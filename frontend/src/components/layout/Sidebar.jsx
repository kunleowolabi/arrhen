import { NavLink } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const navItems = [
  { path: '/',        label: 'Overview' },
  { path: '/trends',  label: 'Trends' },
  { path: '/sites',   label: 'Sites' },
  { path: '/factors', label: 'Emission Factors' },
  { path: '/data',    label: 'Data Management' },
  { path: '/flags',   label: 'Flags & Quarantine' },
  { path: '/reports', label: 'Reports' },
]

export default function Sidebar({ orgName }) {
  const { user, signOut } = useAuth()

  return (
    <>
      {/* ── Desktop sidebar ─────────────────────────── */}
      <aside
        className="hidden md:flex flex-col"
        style={{
          width: '220px',
          minHeight: '100vh',
          background: 'var(--bg-sidebar)',
          borderRight: '1px solid var(--border)',
          padding: '28px 0',
          position: 'fixed',
          top: 0,
          left: 0,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Logo + org name */}
        <div style={{ padding: '0 24px 24px' }}>
          <img
            src="/src/assets/logo-icon.svg"
            alt="Arrhen"
            style={{
              width: '52px',
              height: 'auto',
              display: 'block',
              marginBottom: '14px',
            }}
          />
          <div style={{
            fontSize: '11px',
            color: 'var(--text-muted)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            fontWeight: '400',
          }}>
            {orgName || 'Loading...'}
          </div>
        </div>

        <hr className="divider" style={{ marginBottom: '12px' }} />

        {/* Nav */}
        <nav style={{ flex: 1 }}>
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              style={({ isActive }) => ({
                display: 'block',
                padding: '9px 24px',
                fontSize: '13px',
                fontWeight: isActive ? '600' : '400',
                color: isActive
                  ? 'var(--text-primary)'
                  : 'var(--text-muted)',
                textDecoration: 'none',
                borderLeft: isActive
                  ? '2px solid var(--black)'
                  : '2px solid transparent',
                transition: 'all 0.12s ease',
                letterSpacing: '0.01em',
              })}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div style={{ padding: '16px 24px' }}>
          <div style={{
            fontSize: '11px',
            color: 'var(--text-muted)',
            marginBottom: '10px',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}>
            {user?.email}
          </div>
          <button
            className="btn"
            style={{
              width: '100%',
              justifyContent: 'center',
              fontSize: '12px',
              background: 'transparent',
              border: '1px solid var(--border)',
            }}
            onClick={signOut}
          >
            Sign out
          </button>
          <div style={{
            fontSize: '10px',
            color: 'var(--text-muted)',
            marginTop: '10px',
            letterSpacing: '0.03em',
          }}>
            v0.1.0 · BUSL-1.1
          </div>
        </div>
      </aside>

      {/* ── Mobile bottom tab bar ────────────────────── */}
      <nav
        style={{
          display: 'none',
          position: 'fixed',
          bottom: 0, left: 0, right: 0,
          background: 'var(--bg-sidebar)',
          borderTop: '1px solid var(--border)',
          zIndex: 100,
          padding: '8px 0',
          justifyContent: 'space-around',
        }}
        className="mobile-nav"
      >
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            style={({ isActive }) => ({
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              padding: '4px 8px',
              fontSize: '10px',
              fontWeight: isActive ? '600' : '400',
              color: isActive
                ? 'var(--text-primary)'
                : 'var(--text-muted)',
              textDecoration: 'none',
              minWidth: '44px',
            })}
          >
            {item.label.split(' ')[0]}
          </NavLink>
        ))}
      </nav>
    </>
  )
}
