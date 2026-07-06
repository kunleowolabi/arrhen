import { useState, useEffect } from 'react'
import { ReportsSkeleton } from '../components/Skeleton'
import { getOrganisations, downloadJsonReport } from '../api/client'

const REPORT_TYPES = [
  {
    id: 'json',
    title: 'JSON Inventory Export',
    description:
      'Machine-readable full emission inventory with complete lineage. Suitable for third-party verification, regulatory portals, or parent company consolidation.',
    format: 'JSON',
    badge: 'badge-ok',
  },
  {
    id: 'pdf',
    title: 'PDF Emission Report',
    description:
      'Structured report containing methodology statement, scope summary, site breakdown, materiality analysis, data quality statement, and target progress.',
    format: 'PDF',
    badge: 'badge-solid',
  },
  {
    id: 'audit',
    title: 'Audit Trail Export',
    description:
      'Full lineage report — every emission record with its source activity, emission factor applied, GWP version, fallback flags, and calculation timestamp.',
    format: 'JSON',
    badge: 'badge-ok',
  },
]

const YEARS = [2024, 2023, 2022, 2021, 2020]

function MethodologyNote() {
  return (
    <div style={{
      background: 'var(--bg-elevated)',
      border: '1px solid var(--border)',
      borderRadius: '8px',
      padding: '20px',
    }}>
      <h2 style={{ marginBottom: '12px' }}>Methodology Statement</h2>
      <div style={{
        fontSize: '13px',
        color: 'var(--text-secondary)',
        lineHeight: '1.7',
      }}>
        <p style={{ marginBottom: '8px' }}>
          Emissions calculated in accordance with the{' '}
          <strong style={{ color: 'var(--text-primary)' }}>
            GHG Protocol Corporate Standard
          </strong>.
          Scope 1, 2, and 3 categories reported where data is available.
        </p>
        <p style={{ marginBottom: '8px' }}>
          Emission factors sourced from{' '}
          <strong style={{ color: 'var(--text-primary)' }}>DEFRA 2023</strong> and{' '}
          <strong style={{ color: 'var(--text-primary)' }}>IEA 2022</strong>.
          Global Warming Potential values applied using{' '}
          <strong style={{ color: 'var(--text-primary)' }}>IPCC AR6 GWP100</strong>.
        </p>
        <p style={{ marginBottom: '8px' }}>
          Scope 2 emissions reported on a{' '}
          <strong style={{ color: 'var(--text-primary)' }}>location-based</strong> basis
          unless contractual instruments are specified, in which case both
          location-based and market-based figures are presented.
        </p>
        <p>
          This report has not been subject to third-party verification.
          Data quality flags and fallback factor usage are documented
          in the audit trail export.
        </p>
      </div>
    </div>
  )
}

export default function Reports() {
  const [org, setOrg] = useState(null)
  const [selectedYear, setSelectedYear] = useState(2024)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getOrganisations()
      .then((orgs) => {
        if (orgs && orgs.length > 0) setOrg(orgs[0])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleGenerate = async (reportType) => {
    if (!org) return
    setGenerating(reportType)
    setResult(null)
    setError(null)

    try {
      if (reportType === 'json') {
        const data = await downloadJsonReport(org.id, selectedYear)
        _downloadBlob(
          JSON.stringify(data, null, 2),
          'application/json',
          `${org.name.replace(/\s+/g, '_')}_${selectedYear}_inventory.json`,
        )
        setResult({ type: 'json', success: true })

      } else if (reportType === 'audit') {
        const res = await fetch(
          `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/v1/reports/audit-trail?organisation_id=${org.id}&period_year=${selectedYear}`
        )
        const data = await res.json()
        _downloadBlob(
          JSON.stringify(data, null, 2),
          'application/json',
          `${org.name.replace(/\s+/g, '_')}_${selectedYear}_audit_trail.json`,
        )
        setResult({ type: 'audit', success: true })

      } else if (reportType === 'pdf') {
        const res = await fetch(
          `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/v1/reports/pdf?organisation_id=${org.id}&period_year=${selectedYear}`
        )
        if (!res.ok) throw new Error('PDF generation failed')
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${org.name.replace(/\s+/g, '_')}_${selectedYear}_report.pdf`
        a.click()
        URL.revokeObjectURL(url)
        setResult({ type: 'pdf', success: true })
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setGenerating(null)
    }
  }

  const _downloadBlob = (content, type, filename) => {
    const blob = new Blob([content], { type })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) return <ReportsSkeleton />

  return (
    <div>
      {/* ── Header ───────────────────────────────────────── */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '24px',
        flexWrap: 'wrap',
        gap: '16px',
      }}>
        <div>
          <h1>Reports</h1>
          <p style={{ color: 'var(--text-muted)', marginTop: '4px' }}>
            Generate and download emission inventory reports
          </p>
        </div>

        {/* Year selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <label style={{
            fontSize: '12px',
            color: 'var(--text-muted)',
            fontWeight: '500',
          }}>
            Reporting Year
          </label>
          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(parseInt(e.target.value))}
            style={{ width: 'auto', minWidth: '100px' }}
          >
            {YEARS.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
      </div>

      {/* ── Organisation context ──────────────────────────── */}
      {org && (
        <div className="card-sm" style={{
          marginBottom: '24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}>
          <div>
            <div style={{
              fontSize: '11px',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: 'var(--text-muted)',
              marginBottom: '2px',
            }}>
              Reporting Entity
            </div>
            <div style={{
              fontSize: '15px',
              fontWeight: '600',
              color: 'var(--text-primary)',
            }}>
              {org.name}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              {org.industry.replace(/_/g, ' ')} · {org.country} ·{' '}
              GWP: {org.default_gwp_version}
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <span className="badge badge-ok">
              {selectedYear} Inventory
            </span>
            <span className="badge badge-solid">
              GHG Protocol
            </span>
          </div>
        </div>
      )}

      {/* ── Error / success ───────────────────────────────── */}
      {error && (
        <div style={{
          padding: '12px 16px',
          background: 'var(--bg-elevated)',
          borderRadius: '6px',
          fontSize: '13px',
          color: 'var(--text-secondary)',
          marginBottom: '16px',
        }}>
          {error}
        </div>
      )}

      {result?.success && (
        <div style={{
          padding: '12px 16px',
          background: 'var(--bg-elevated)',
          borderRadius: '6px',
          fontSize: '13px',
          color: 'var(--text-secondary)',
          marginBottom: '16px',
        }}>
          ✓ {result.type.toUpperCase()} report downloaded successfully
        </div>
      )}

      {/* ── Report cards ─────────────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '16px',
        marginBottom: '24px',
      }}>
        {REPORT_TYPES.map((report) => (
          <div key={report.id} className="card" style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            opacity: report.comingSoon ? 0.6 : 1,
          }}>
            <div>
              {/* Header */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: '12px',
              }}>
                <h2>{report.title}</h2>
                <span className={`badge ${report.badge}`}>
                  {report.format}
                </span>
              </div>

              {/* Description */}
              <p style={{
                fontSize: '13px',
                color: 'var(--text-secondary)',
                lineHeight: '1.6',
                marginBottom: '20px',
              }}>
                {report.description}
              </p>
            </div>

            {/* Action */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              {report.comingSoon ? (
                <span style={{
                  fontSize: '12px',
                  color: 'var(--text-muted)',
                }}>
                  Coming in Phase 7
                </span>
              ) : (
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  {selectedYear} · {org?.name || '—'}
                </span>
              )}

              <button
                className={`btn ${!report.comingSoon ? 'btn-primary' : ''}`}
                onClick={() => handleGenerate(report.id)}
                disabled={!!generating || report.comingSoon || !org}
              >
                {generating === report.id
                  ? 'Generating...'
                  : `↓ ${report.format}`}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* ── Methodology statement ─────────────────────────── */}
      <MethodologyNote />
    </div>
  )
}