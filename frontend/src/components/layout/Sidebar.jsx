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
      {/* ── Desktop sidebar — on grey background ──── */}
      <aside style={{
        width: '220px',
        minHeight: '100vh',
        position: 'fixed',
        top: 0,
        left: 0,
        bottom: 0,
        padding: '28px 0',
        display: 'flex',
        flexDirection: 'column',
        background: 'transparent',
      }}>
        {/* Logo + org */}
        <div style={{ padding: '0 24px 24px' }}>
          <img
            src="/logo1.svg"
            alt="Arrhen"
            style={{
              width: '100px',
              height: 'auto',
              display: 'block',
              marginBottom: '14px',
            }}
          />
          <div style={{
            fontSize: '11px',
            color: '#9CA3AF',
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
                fontSize: '13.5px',
                fontWeight: isActive ? '700' : '500',
                color: isActive
                  ? '#111111'
                  : '#6B7280',
                textDecoration: 'none',
                borderLeft: isActive
                  ? '2px solid #111111'
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
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '8px',
          }}>
            <div style={{
              fontSize: '12px',
              fontWeight: '500',
              color: '#4B5563',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              {user?.user_metadata?.full_name ||
               user?.email?.split('@')[0] ||
               'Account'}
            </div>
            <button
              onClick={signOut}
              title="Sign out"
              style={{
                background: 'none',
                border: '1px solid #E5E7EB',
                borderRadius: '6px',
                padding: '5px 7px',
                cursor: 'pointer',
                color: '#9CA3AF',
                display: 'flex',
                alignItems: 'center',
                flexShrink: 0,
                transition: 'all 0.12s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = '#374151'
                e.currentTarget.style.borderColor = '#9CA3AF'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = '#9CA3AF'
                e.currentTarget.style.borderColor = '#E5E7EB'
              }}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
            </button>
          </div>
          <div style={{
            fontSize: '10px',
            color: '#9CA3AF',
            marginTop: '10px',
            letterSpacing: '0.03em',
          }}>
            v0.1.0 · BUSL-1.1
          </div>
        </div>
      </aside>

      {/* ── Mobile bottom tab bar ────────────────────── */}
      <nav style={{
        position: 'fixed',
        bottom: 0, left: 0, right: 0,
        background: 'var(--bg-surface)',
        borderTop: '1px solid var(--border)',
        zIndex: 100,
        padding: '8px 0',
        justifyContent: 'space-around',
        display: 'none',
      }}>
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
