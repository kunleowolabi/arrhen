import { useState, useEffect } from 'react'
import { getOrganisations, getActivityRecords } from '../api/client'
import { FlagsSkeleton } from '../components/Skeleton'

const TABS = [
  { value: 'quarantined', label: 'Quarantined' },
  { value: 'duplicate', label: 'Duplicates' },
]

const SCOPE_LABELS = {
  scope_1: 'Scope 1',
  scope_2: 'Scope 2',
  scope_3: 'Scope 3',
}

function SummaryCard({ label, value, sub }) {
  return (
    <div className="card-sm" style={{
      flex: 1,
      minWidth: '140px',
      padding: '20px 24px',
    }}>
      <div style={{
        fontSize: '11px',
        fontWeight: '500',
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        color: 'var(--text-muted)',
        marginBottom: '10px',
      }}>
        {label}
      </div>
      <div style={{
        fontSize: '28px',
        fontWeight: '700',
        color: 'var(--text-primary)',
        lineHeight: 1,
        marginBottom: sub ? '6px' : 0,
      }}>
        {value}
      </div>
      {sub && (
        <div style={{
          fontSize: '11px',
          color: 'var(--text-muted)',
        }}>
          {sub}
        </div>
      )}
    </div>
  )
}

export default function Flags() {
  const [records, setRecords] = useState({ quarantined: [], duplicates: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('quarantined')
  const [expanded, setExpanded] = useState(null)
  const [yearFilter, setYearFilter] = useState('all')

  useEffect(() => {
    getOrganisations()
      .then(() =>
        Promise.all([
          getActivityRecords({ status: 'quarantined', limit: 500 }),
          getActivityRecords({ limit: 500 }),
        ])
      )
      .then(([quarantined, all]) => {
        const duplicates = all.filter((r) => r.is_flagged_duplicate)
        setRecords({ quarantined, duplicates })
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <FlagsSkeleton />
  if (error) return (
    <div style={{ color: 'var(--status-bad)' }}>Error: {error}</div>
  )

  const { quarantined, duplicates } = records
  const total = quarantined.length + duplicates.length
  const activeRecords = activeTab === 'quarantined' ? quarantined : duplicates

  // Unique years for filter
  const allRecords = [...quarantined, ...duplicates]
  const uniqueYears = [...new Set(allRecords.map((r) => r.period_year))]
    .filter(Boolean)
    .sort()

  // Apply year filter
  const filtered = activeRecords.filter((r) => {
    if (yearFilter !== 'all' && r.period_year !== parseInt(yearFilter)) return false
    return true
  })

  return (
    <div>
      {/* ── Header ───────────────────────────────────────── */}
      <div style={{ marginBottom: '32px' }}>
        <h1>Flags & Quarantine</h1>
        <p style={{ color: 'var(--text-muted)', marginTop: '6px' }}>
          Review records that require attention before calculations run
        </p>
      </div>

      {/* ── Summary cards — Total → Quarantined → Duplicates */}
      <div style={{
        display: 'flex',
        gap: '16px',
        marginBottom: '32px',
        flexWrap: 'wrap',
      }}>
        <SummaryCard
          label="Total Flagged"
          value={total}
          sub="Require attention"
        />
        <SummaryCard
          label="Quarantined"
          value={quarantined.length}
          sub="Failed validation"
        />
        <SummaryCard
          label="Duplicates"
          value={duplicates.length}
          sub="Flagged for review"
        />
      </div>

      {/* ── Tabs + filters ───────────────────────────────── */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '16px',
        flexWrap: 'wrap',
        gap: '12px',
      }}>
        {/* Tabs */}
        <div style={{ display: 'flex', gap: '4px' }}>
          {TABS.map((tab) => {
            const count = tab.value === 'quarantined'
              ? quarantined.length
              : duplicates.length
            return (
              <button
                key={tab.value}
                className={`btn ${activeTab === tab.value ? 'btn-primary' : ''}`}
                style={{ fontSize: '13px' }}
                onClick={() => {
                  setActiveTab(tab.value)
                  setExpanded(null)
                }}
              >
                {tab.label}
                <span style={{
                  marginLeft: '6px',
                  padding: '1px 6px',
                  borderRadius: '10px',
                  fontSize: '11px',
                  background: activeTab === tab.value
                    ? 'rgba(255,255,255,0.2)'
                    : 'var(--bg-elevated)',
                  color: activeTab === tab.value
                    ? 'inherit'
                    : 'var(--text-muted)',
                }}>
                  {count}
                </span>
              </button>
            )
          })}
        </div>

        {/* Year filter dropdown */}
        <select
          value={yearFilter}
          onChange={(e) => setYearFilter(e.target.value)}
          style={{ width: 'auto', minWidth: '140px' }}
        >
          <option value="all">All Years</option>
          {uniqueYears.map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      {/* ── Records table ────────────────────────────────── */}
      <div className="card" style={{ padding: 0 }}>
        {filtered.length === 0 ? (
          <div style={{
            padding: '56px',
            textAlign: 'center',
            color: 'var(--text-muted)',
            fontSize: '13px',
          }}>
            {activeTab === 'quarantined'
              ? 'No quarantined records. All uploads passed validation.'
              : 'No duplicate records flagged.'}
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Scope</th>
                  <th>Category</th>
                  <th>Fuel / Material</th>
                  <th>Quantity</th>
                  <th>Unit</th>
                  <th>Period</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((record) => (
                  <>
                    <tr
                      key={record.id}
                      style={{ cursor: 'pointer' }}
                      onClick={() =>
                        setExpanded(
                          expanded === record.id ? null : record.id
                        )
                      }
                    >
                      {/* Status — plain text, no badge box */}
                      <td style={{
                        fontSize: '12px',
                        color: record.is_flagged_duplicate
                          ? 'var(--status-warn)'
                          : 'var(--status-bad)',
                      }}>
                        {record.is_flagged_duplicate
                          ? 'Duplicate'
                          : 'Quarantined'}
                      </td>

                      {/* Scope — plain text */}
                      <td style={{
                        fontSize: '12px',
                        color: 'var(--text-secondary)',
                      }}>
                        {SCOPE_LABELS[record.scope] || record.scope}
                      </td>

                      {/* Category — sentence case, no caps */}
                      <td style={{
                        fontSize: '12px',
                        color: 'var(--text-secondary)',
                      }}>
                        {record.ghg_category.replace(/_/g, ' ')}
                      </td>

                      <td style={{
                        fontWeight: '500',
                        color: 'var(--text-primary)',
                      }}>
                        {record.fuel_or_material}
                      </td>

                      <td style={{
                        color: 'var(--text-secondary)',
                      }}>
                        {record.quantity.toLocaleString()}
                      </td>

                      <td style={{
                        fontSize: '12px',
                        color: 'var(--text-muted)',
                      }}>
                        {record.unit}
                      </td>

                      <td style={{
                        fontSize: '12px',
                        color: 'var(--text-muted)',
                        whiteSpace: 'nowrap',
                      }}>
                        {record.period_month
                          ? `${record.period_month}/${record.period_year}`
                          : record.period_year}
                      </td>

                      <td style={{
                        fontSize: '11px',
                        color: 'var(--text-muted)',
                        whiteSpace: 'nowrap',
                      }}>
                        {new Date(record.created_at).toLocaleDateString(
                          'en-GB', {
                            day: '2-digit',
                            month: 'short',
                            year: 'numeric',
                          }
                        )}
                      </td>
                    </tr>

                    {/* Expanded detail row */}
                    {expanded === record.id && (
                      <tr key={`${record.id}-detail`}>
                        <td colSpan={8} style={{
                          background: 'var(--bg-elevated)',
                          padding: '20px 24px',
                        }}>
                          <div style={{
                            display: 'grid',
                            gridTemplateColumns:
                              'repeat(auto-fit, minmax(200px, 1fr))',
                            gap: '20px',
                          }}>
                            {/* Flag reason — prominent */}
                            {record.flag_reason && (
                              <div style={{ gridColumn: '1 / -1' }}>
                                <div style={{
                                  fontSize: '10px',
                                  textTransform: 'uppercase',
                                  letterSpacing: '0.05em',
                                  color: 'var(--text-muted)',
                                  marginBottom: '6px',
                                }}>
                                  Reason
                                </div>
                                <div style={{
                                  fontSize: '13px',
                                  color: 'var(--text-primary)',
                                  padding: '10px 14px',
                                  background: 'var(--bg-surface)',
                                  borderRadius: '6px',
                                  border: '1px solid var(--border)',
                                  lineHeight: '1.5',
                                }}>
                                  {record.flag_reason}
                                </div>
                              </div>
                            )}

                            {/* Supporting details */}
                            {[
                              { label: 'Record ID', value: record.id },
                              { label: 'Site ID', value: record.site_id },
                              {
                                label: 'Upload batch',
                                value: record.data_lineage_id || '—',
                              },
                              {
                                label: 'Description',
                                value: record.activity_description || '—',
                              },
                              {
                                label: 'Supplier',
                                value: record.supplier_name || '—',
                              },
                              {
                                label: 'Supplier tier',
                                value: record.supplier_tier
                                  ? `Tier ${record.supplier_tier}`
                                  : '—',
                              },
                            ].map((item) => (
                              <div key={item.label}>
                                <div style={{
                                  fontSize: '10px',
                                  textTransform: 'uppercase',
                                  letterSpacing: '0.05em',
                                  color: 'var(--text-muted)',
                                  marginBottom: '4px',
                                }}>
                                  {item.label}
                                </div>
                                <div style={{
                                  fontSize: '12px',
                                  color: 'var(--text-secondary)',
                                  fontFamily: item.label.includes('ID') ||
                                    item.label === 'Upload batch'
                                    ? 'monospace' : 'inherit',
                                  wordBreak: 'break-all',
                                }}>
                                  {item.value}
                                </div>
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}