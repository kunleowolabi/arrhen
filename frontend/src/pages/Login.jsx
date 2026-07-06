import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const { signIn, signUp } = useAuth()
  const navigate = useNavigate()

  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [message, setMessage] = useState(null)

  const handleSubmit = async () => {
    setLoading(true)
    setError(null)
    setMessage(null)

    if (mode === 'login') {
      const { error } = await signIn(email, password)
      if (error) setError(error.message)
      else navigate('/')
    } else {
      const { error } = await signUp(email, password, fullName)
      if (error) {
        setError(error.message)
      } else {
        setMessage('Account created. Check your email to confirm, then sign in.')
        setMode('login')
      }
    }

    setLoading(false)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSubmit()
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      fontFamily: "'Raleway', system-ui, sans-serif",
    }}>
      {/* ── Left panel ──────────────────────────────── */}
      <div style={{
        flex: '0 0 48%',
        background: '#0A0A0A',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '48px',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Subtle texture gradient */}
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(ellipse at 20% 80%, #1a1a1a 0%, #0A0A0A 60%)',
          pointerEvents: 'none',
        }} />

        {/* Logo */}
        <div style={{ position: 'relative', zIndex: 1 }}>
          <img
            src="/src/assets/logo-full.svg"
            alt="Arrhen"
            style={{
              width: '140px',
              height: 'auto',
              display: 'block',
              filter: 'invert(1)',
            }}
          />
        </div>

        {/* Copy */}
        <div style={{ position: 'relative', zIndex: 1, maxWidth: '400px' }}>
          <p style={{
            fontSize: '11px',
            fontWeight: '500',
            textTransform: 'uppercase',
            letterSpacing: '0.12em',
            color: '#666666',
            marginBottom: '20px',
          }}>
            Carbon Emission Tracking
          </p>
          <h2 style={{
            fontSize: '28px',
            fontWeight: '600',
            lineHeight: '1.25',
            color: '#FFFFFF',
            letterSpacing: '-0.02em',
            marginBottom: '24px',
          }}>
            Your emissions data.{' '}
            Your methodology.{' '}
            Your audit trail.
          </h2>
          <p style={{
            fontSize: '14px',
            fontWeight: '400',
            lineHeight: '1.8',
            color: '#888888',
          }}>
            Africa's carbon accountability landscape is changing faster than
            most organisations are prepared for. The companies that will
            participate in emerging carbon markets are the ones who own their
            data today. Arrhen puts that infrastructure in-house — a full GHG
            Protocol-aligned calculation engine, field data collection via ODK,
            and a complete audit trail that belongs to you, not your consultant.
          </p>
        </div>

        {/* Bottom label */}
        <div style={{ position: 'relative', zIndex: 1 }}>
          <p style={{
            fontSize: '10px',
            color: '#444444',
            letterSpacing: '0.05em',
          }}>
            GHG Protocol · IPCC AR6 · DEFRA 2023 · IEA 2022
          </p>
        </div>
      </div>

      {/* ── Right panel ─────────────────────────────── */}
      <div style={{
        flex: 1,
        background: '#FAFAFA',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px',
      }}>
        <div style={{ width: '100%', maxWidth: '360px' }}>
          <h2 style={{
            fontSize: '20px',
            fontWeight: '600',
            marginBottom: '8px',
            letterSpacing: '-0.01em',
          }}>
            {mode === 'login' ? 'Sign in' : 'Create account'}
          </h2>
          <p style={{
            fontSize: '13px',
            color: 'var(--text-muted)',
            marginBottom: '32px',
          }}>
            {mode === 'login'
              ? 'Enter your credentials to continue'
              : 'Set up your account to get started'}
          </p>

          {/* Full name — signup only */}
          {mode === 'signup' && (
            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block',
                fontSize: '11px',
                fontWeight: '600',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                color: 'var(--text-muted)',
                marginBottom: '6px',
              }}>
                Full Name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Your full name"
                style={{ background: '#FFFFFF' }}
              />
            </div>
          )}

          {/* Email */}
          <div style={{ marginBottom: '16px' }}>
            <label style={{
              display: 'block',
              fontSize: '11px',
              fontWeight: '600',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: 'var(--text-muted)',
              marginBottom: '6px',
            }}>
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="you@organisation.com"
              style={{ background: '#FFFFFF' }}
            />
          </div>

          {/* Password */}
          <div style={{ marginBottom: '28px' }}>
            <label style={{
              display: 'block',
              fontSize: '11px',
              fontWeight: '600',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: 'var(--text-muted)',
              marginBottom: '6px',
            }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="••••••••"
              style={{ background: '#FFFFFF' }}
            />
          </div>

          {/* Error / success */}
          {error && (
            <div style={{
              fontSize: '12px',
              color: 'var(--status-bad)',
              marginBottom: '16px',
              padding: '10px 14px',
              background: '#FEF2F2',
              borderRadius: 'var(--radius-sm)',
            }}>
              {error}
            </div>
          )}
          {message && (
            <div style={{
              fontSize: '12px',
              color: 'var(--text-secondary)',
              marginBottom: '16px',
              padding: '10px 14px',
              background: 'var(--bg-elevated)',
              borderRadius: 'var(--radius-sm)',
            }}>
              {message}
            </div>
          )}

          {/* Submit */}
          <button
            className="btn btn-primary"
            style={{
              width: '100%',
              justifyContent: 'center',
              padding: '11px 16px',
              fontSize: '13px',
              letterSpacing: '0.02em',
            }}
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading
              ? 'Please wait...'
              : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>

          {/* Toggle */}
          <div style={{
            marginTop: '24px',
            textAlign: 'center',
            fontSize: '13px',
            color: 'var(--text-muted)',
          }}>
            {mode === 'login' ? (
              <>
                No account?{' '}
                <button
                  onClick={() => { setMode('signup'); setError(null) }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    fontWeight: '600',
                    fontSize: '13px',
                    fontFamily: 'inherit',
                    padding: 0,
                  }}
                >
                  Sign up
                </button>
              </>
            ) : (
              <>
                Have an account?{' '}
                <button
                  onClick={() => { setMode('login'); setError(null) }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    fontWeight: '600',
                    fontSize: '13px',
                    fontFamily: 'inherit',
                    padding: 0,
                  }}
                >
                  Sign in
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
