import { useState, useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import { getOrganisations } from '../../api/client'
import { useAuth } from '../../context/AuthContext'

export default function Layout() {
  const { user, signOut } = useAuth()
  const [orgName, setOrgName] = useState('')

  useEffect(() => {
    getOrganisations()
      .then((orgs) => {
        if (orgs && orgs.length > 0) setOrgName(orgs[0].name)
      })
      .catch(() => {})
  }, [])

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar orgName={orgName} />

      {/* Main content — offset by sidebar width on desktop */}
      <main
        className="flex-1"
        style={{
          marginLeft: '220px',
          padding: '32px',
          minHeight: '100vh',
          // On mobile the sidebar becomes bottom nav
          // so no left margin needed
        }}
      >
        {/* Remove left margin on mobile */}
        <style>{`
          @media (max-width: 768px) {
            main { margin-left: 0 !important; padding-bottom: 80px !important; }
          }
        `}</style>

        <Outlet />
      </main>
    </div>
  )
}