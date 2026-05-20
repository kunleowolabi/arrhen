import { useState, useEffect } from 'react'
import { getFactors } from '../api/client'

const ACTIVITY_TYPES = [
  'All',
  'stationary_combustion',
  'company_vehicles',
  'mobile_combustion',
  'purchased_electricity',
  'fugitive_emissions',
  'business_travel',
]

const formatActivityType = (str) =>
  str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

export default function Factors() {
  const [factors, setFactors] = useState([])
  const [filtered, setFiltered] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activityFilter, setActivityFilter] = useState('All')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    getFactors()
      .then((data) => {
        setFactors(data)
        setFiltered(data)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    let result = factors

    if (activityFilter !== 'All') {
      result = result.filter((f) => f.activity_type === activityFilter)
    }

    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(
        (f) =>
          f.fuel_or_material.toLowerCase().includes(q) ||
          f.activity_type.toLowerCase().includes(q) ||
          f.source.toLowerCase().includes(q) ||
          (f.region && f.region.toLowerCase().includes(q))
      )
    }

    setFiltered(result)
  }, [activityFilter, search, factors])

  if (loading) return (
    <div style={{ color: 'var(--text-muted)' }}>Loading...</div>
  )
  if (error) return (
    <div style={{ color: 'var(--status-bad)' }}>Error: {error}</div>
  )

  return (
    <div>
      {/* ── Header ───────────────────────────────────────── */}
      <div style={{ marginBottom: '32px' }}>
        <h1>Emission Factors</h1>
        <p style={{ color: 'var(--text-muted)', marginTop: '6px' }}>
          {factors.length} factors · DEFRA 2023 · IEA 2022 · IPCC AR6
        </p>
      </div>

      {/* ── Summary stats ────────────────────────────────── */}
      <div style={{
        display: 'flex',
        gap: '16px',
        marginBottom: '24px',
        flexWrap: 'wrap',
      }}>
        {[
          { label: 'Total Factors', value: factors.length },
          {
            label: 'Regional',
            value: factors.filter((f) => f.region).length,
          },
          {
            label: 'Global Default',
            value: factors.filter((f) => !f.region).length,
          },
          { label: 'Showing', value: filtered.length },
        ].map((stat) => (
          <div key={stat.label} className="card-sm" style={{
            flex: 1,
            minWidth: '120px',
            textAlign: 'center',
            padding: '16px',
          }}>
            <div style={{
              fontSize: '24px',
              fontWeight: '700',
              color: 'var(--text-primary)',
            }}>
              {stat.value}
            </div>
            <div style={{
              fontSize: '11px',
              color: 'var(--text-muted)',
              marginTop: '4px',
            }}>
              {stat.label}
            </div>
          </div>
        ))}
      </div>

      {/* ── Filters ──────────────────────────────────────── */}
      <div style={{
        display: 'flex',
        gap: '12px',
        marginBottom: '20px',
        flexWrap: 'wrap',
        alignItems: 'center',
      }}>
        <input
          placeholder="Search fuel, source, region..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ maxWidth: '260px' }}
        />
        <select
          value={activityFilter}
          onChange={(e) => setActivityFilter(e.target.value)}
          style={{ width: 'auto', minWidth: '180px' }}
        >
          {ACTIVITY_TYPES.map((type) => (
            <option key={type} value={type}>
              {type === 'All' ? 'All Activity Types' : formatActivityType(type)}
            </option>
          ))}
        </select>
      </div>

      {/* ── Table ────────────────────────────────────────── */}
      <div className="card" style={{ padding: 0 }}>
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>Activity Type</th>
                <th>Fuel / Material</th>
                <th>Region</th>
                <th style={{ textAlign: 'right' }}>CO₂</th>
                <th style={{ textAlign: 'right' }}>CH₄</th>
                <th style={{ textAlign: 'right' }}>N₂O</th>
                <th>Unit</th>
                <th>Source</th>
                <th>Version</th>
                <th>Valid From</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={10} style={{
                    textAlign: 'center',
                    color: 'var(--text-muted)',
                    padding: '40px',
                  }}>
                    No factors match your filters.
                  </td>
                </tr>
              ) : (
                filtered.map((factor) => (
                  <>
                    <tr
                      key={factor.id}
                      style={{ cursor: 'pointer' }}
                      onClick={() =>
                        setSelected(
                          selected?.id === factor.id ? null : factor
                        )
                      }
                    >
                      <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                        {formatActivityType(factor.activity_type)}
                      </td>
                      <td style={{
                        fontWeight: '500',
                        color: 'var(--text-primary)',
                      }}>
                        {factor.fuel_or_material}
                      </td>
                      <td style={{
                        fontSize: '12px',
                        color: 'var(--text-secondary)',
                      }}>
                        {factor.region || 'Global'}
                      </td>
                      <td style={{
                        textAlign: 'right',
                        fontFamily: 'monospace',
                        fontSize: '12px',
                      }}>
                        {factor.co2_factor.toFixed(5)}
                      </td>
                      <td style={{
                        textAlign: 'right',
                        fontFamily: 'monospace',
                        fontSize: '12px',
                      }}>
                        {factor.ch4_factor.toFixed(5)}
                      </td>
                      <td style={{
                        textAlign: 'right',
                        fontFamily: 'monospace',
                        fontSize: '12px',
                      }}>
                        {factor.n2o_factor.toFixed(5)}
                      </td>
                      <td style={{
                        color: 'var(--text-muted)',
                        fontSize: '12px',
                      }}>
                        {factor.unit}
                      </td>
                      <td style={{
                        color: 'var(--text-secondary)',
                        fontSize: '12px',
                      }}>
                        {factor.source}
                      </td>
                      <td style={{
                        color: 'var(--text-secondary)',
                        fontSize: '12px',
                      }}>
                        {factor.version}
                      </td>
                      <td style={{
                        color: 'var(--text-muted)',
                        fontSize: '12px',
                      }}>
                        {factor.valid_from}
                      </td>
                    </tr>

                    {/* Expanded detail row */}
                    {selected?.id === factor.id && (
                      <tr key={`${factor.id}-detail`}>
                        <td colSpan={10} style={{
                          background: 'var(--bg-elevated)',
                          padding: '20px 24px',
                        }}>
                          <div style={{
                            display: 'grid',
                            gridTemplateColumns:
                              'repeat(auto-fit, minmax(160px, 1fr))',
                            gap: '20px',
                          }}>
                            {[
                              {
                                label: 'HFC Factor',
                                value: factor.hfc_factor.toFixed(5),
                              },
                              {
                                label: 'PFC Factor',
                                value: factor.pfc_factor.toFixed(5),
                              },
                              {
                                label: 'SF₆ Factor',
                                value: factor.sf6_factor.toFixed(5),
                              },
                              {
                                label: 'NF₃ Factor',
                                value: factor.nf3_factor.toFixed(5),
                              },
                              {
                                label: 'Valid To',
                                value: factor.valid_to || 'Currently Active',
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
                                  fontSize: '13px',
                                  fontFamily: 'monospace',
                                  color: 'var(--text-primary)',
                                }}>
                                  {item.value}
                                </div>
                              </div>
                            ))}
                            {factor.notes && (
                              <div style={{ gridColumn: '1 / -1' }}>
                                <div style={{
                                  fontSize: '10px',
                                  textTransform: 'uppercase',
                                  letterSpacing: '0.05em',
                                  color: 'var(--text-muted)',
                                  marginBottom: '4px',
                                }}>
                                  Notes
                                </div>
                                <div style={{
                                  fontSize: '13px',
                                  color: 'var(--text-secondary)',
                                  lineHeight: '1.6',
                                }}>
                                  {factor.notes}
                                </div>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}