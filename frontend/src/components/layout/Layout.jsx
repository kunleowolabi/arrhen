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
      <main
        style={{
          flex: 1,
          marginLeft: '220px',
          padding: '32px',
          minHeight: '100vh',
        }}
        className="main-content"
      >
        <Outlet />
      </main>
    </div>
  )
}
