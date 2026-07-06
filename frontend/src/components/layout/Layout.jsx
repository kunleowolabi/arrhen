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
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-page)' }}>
      <Sidebar orgName={orgName} />
      <main className="main-content">
        <div className="content-sheet">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
