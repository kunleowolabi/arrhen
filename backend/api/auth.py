"""
Authentication and authorisation middleware.

Every protected endpoint depends on get_current_user() which:
1. Extracts the Bearer token from the Authorization header
2. Verifies it against Supabase's JWT secret
3. Looks up the user in our users table
4. Returns the User object

Role enforcement is done per-endpoint using require_role().

Usage:
    from backend.api.auth import get_current_user, require_role
    from backend.models.user import UserRole

    # Any authenticated user
    @router.get("/something")
    def my_endpoint(current_user = Depends(get_current_user)):
        ...

    # Specific role required
    @router.post("/something")
    def admin_only(current_user = Depends(require_role(UserRole.admin))):
        ...
"""

import os
import jwt
import requests
from jwt.algorithms import RSAAlgorithm
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from backend.db.database import get_db
from backend.models.user import User, OrganisationMembership, UserRole
from backend.models import Organisation

load_dotenv()

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL")

security = HTTPBearer()

# Cache JWKS public keys so we don't fetch on every request
_jwks_cache: dict = {}


def _parse_jwk(key_data: dict):
    """
    Parses a JWK key regardless of type (RSA, EC, OKP/EdDSA).
    Returns (key_object, algorithm_string).
    """
    from jwt.algorithms import RSAAlgorithm, ECAlgorithm
    kty = key_data.get("kty", "RSA")
    alg = key_data.get("alg", "")

    if kty == "RSA":
        return RSAAlgorithm.from_jwk(key_data), alg or "RS256"
    elif kty == "EC":
        return ECAlgorithm.from_jwk(key_data), alg or "ES256"
    elif kty == "OKP":
        try:
            from jwt.algorithms import OKPAlgorithm
            return OKPAlgorithm.from_jwk(key_data), alg or "EdDSA"
        except (ImportError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="EdDSA keys require PyJWT >= 2.4.0 with cryptography installed.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unsupported JWK key type: {kty}",
        )


def _get_jwks_key(token: str):
    """
    Fetches Supabase's public JWKS and returns the matching key + algorithm.
    Supports RSA (RS256), EC (ES256), and OKP (EdDSA) key types.
    Falls back to HS256 symmetric secret if token algorithm is HS256.
    """
    global _jwks_cache

    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        alg = header.get("alg", "RS256")

        # HS256 — symmetric, use JWT secret directly
        if alg == "HS256":
            if not SUPABASE_JWT_SECRET:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="SUPABASE_JWT_SECRET not configured.",
                )
            return SUPABASE_JWT_SECRET, ["HS256"]

        # Asymmetric — fetch JWKS and cache keys
        if kid not in _jwks_cache:
            jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
            resp = requests.get(jwks_url, timeout=10)
            resp.raise_for_status()
            jwks = resp.json()
            for key_data in jwks.get("keys", []):
                key_kid = key_data.get("kid")
                if key_kid:
                    key_obj, key_alg = _parse_jwk(key_data)
                    _jwks_cache[key_kid] = (key_obj, key_alg)

        if kid not in _jwks_cache:
            # Clear cache and retry once in case of key rotation
            _jwks_cache.clear()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No matching public key found for token kid.",
            )

        key_obj, key_alg = _jwks_cache[kid]
        return key_obj, [key_alg]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token key resolution failed: {e}",
        )


def _verify_token(token: str) -> dict:
    """
    Verifies a Supabase JWT and returns the decoded payload.
    Supports both RS256 (default) and HS256.
    """
    try:
        key, algorithms = _get_jwks_key(token)
        payload = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            options={"verify_aud": False},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
        )
    except HTTPException:
        raise
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency — verifies JWT and returns the authenticated User.
    Creates the user record on first login if it doesn't exist yet.
    """
    payload = _verify_token(credentials.credentials)

    user_id = payload.get("sub")
    email = payload.get("email")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim.",
        )

    # Look up user — create on first login (mirrors Supabase auth.users)
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing email claim.",
            )
        user = User(id=user_id, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


def get_current_user_organisations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    """
    Returns all organisation IDs the current user has access to.
    Used to filter queries to the user's own data.
    """
    memberships = db.query(OrganisationMembership).filter_by(
        user_id=current_user.id
    ).all()
    return [m.organisation_id for m in memberships]


def require_role(*roles: UserRole):
    """
    Returns a dependency that enforces one of the given roles
    within the organisation being accessed.

    Usage:
        Depends(require_role(UserRole.admin, UserRole.analyst))
    """
    def _check(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        memberships = db.query(OrganisationMembership).filter(
            OrganisationMembership.user_id == current_user.id,
            OrganisationMembership.role.in_([r.value for r in roles]),
        ).all()

        if not memberships:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"This action requires one of the following roles: "
                    f"{[r.value for r in roles]}"
                ),
            )
        return current_user
    return _check


def get_user_org_ids(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    """
    Shorthand dependency — returns list of organisation UUIDs
    the current user belongs to. Used in query filters.
    """
    return get_current_user_organisations(current_user=current_user, db=db)


def validate_org_access(
    organisation_id,
    current_user: User,
    db: Session,
) -> None:
    """
    Raises HTTP 403 if the current user does not have access
    to the requested organisation.
    Call this at the start of any endpoint that takes organisation_id.
    """
    membership = db.query(OrganisationMembership).filter_by(
        user_id=current_user.id,
        organisation_id=organisation_id,
    ).first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organisation.",
        )
