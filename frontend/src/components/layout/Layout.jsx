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
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg-page)',
      display: 'flex',
    }}>
      {/* Sidebar — on grey background, outside the card */}
      <Sidebar orgName={orgName} />

      {/* Content area — white card, right of sidebar */}
      <div style={{
        flex: 1,
        marginLeft: '220px',
        padding: '16px 16px 16px 0',
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
      }}>
        <div style={{
          flex: 1,
          background: 'var(--bg-surface)',
          borderRadius: 'var(--radius-lg)',
          padding: '36px 40px',
          minHeight: 'calc(100vh - 32px)',
        }}>
          <Outlet />
        </div>
      </div>
    </div>
  )
}
