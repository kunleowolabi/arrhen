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
          background: 'var(--bg-surface)',
          borderRight: '1px solid var(--border)',
          padding: '32px 0',
          position: 'fixed',
          top: 0,
          left: 0,
        }}
      >
        {/* Logo block */}
        <div style={{ padding: '0 24px 28px' }}>
          <img
            src="/src/assets/logo.svg"
            alt="Arrhen"
            style={{
              width: '72px',
              height: 'auto',
              display: 'block',
              marginBottom: '12px',
            }}
          />
          <div style={{
            fontSize: '12px',
            color: 'var(--text-muted)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}>
            {orgName || 'Loading...'}
          </div>
        </div>

        <hr className="divider" style={{ marginBottom: '16px' }} />

        <nav style={{ flex: 1 }}>
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              style={({ isActive }) => ({
                display: 'block',
                padding: '10px 24px',
                fontSize: '13px',
                fontWeight: isActive ? '500' : '400',
                color: isActive
                  ? 'var(--text-primary)'
                  : 'var(--text-secondary)',
                textDecoration: 'none',
                borderLeft: isActive
                  ? '2px solid var(--black)'
                  : '2px solid transparent',
                transition: 'all 0.15s',
              })}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div style={{ padding: '16px 24px' }}>
          <div style={{
            fontSize: '11px',
            color: 'var(--text-muted)',
            marginBottom: '8px',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}>
            {user?.email}
          </div>
          <button
            className="btn"
            style={{ width: '100%', fontSize: '12px', justifyContent: 'center' }}
            onClick={signOut}
          >
            Sign out
          </button>
          <div style={{
            fontSize: '10px',
            color: 'var(--text-muted)',
            marginTop: '8px',
          }}>
            v0.1.0 · BUSL-1.1
          </div>
        </div>
      </aside>

      {/* ── Mobile bottom tab bar ────────────────────── */}
      <nav
        className="flex md:hidden"
        style={{
          position: 'fixed',
          bottom: 0, left: 0, right: 0,
          background: 'var(--bg-surface)',
          borderTop: '1px solid var(--border)',
          zIndex: 100,
          padding: '8px 0',
          justifyContent: 'space-around',
        }}
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
              fontWeight: isActive ? '500' : '400',
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