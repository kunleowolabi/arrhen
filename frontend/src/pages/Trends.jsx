import { useState, useEffect } from 'react'
import {
  LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'
import { getOrganisations, getTrends } from '../api/client'

const MONTH_NAMES = [
  '', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

const SCOPE_COLOURS = {
  scope_1: '#0A0A0A',
  scope_2: '#525252',
  scope_3: '#A3A3A3',
}

function FilterBar({ scopeFilter, setScopeFilter }) {
  const options = [
    { value: 'all', label: 'All Scopes' },
    { value: 'scope_1', label: 'Scope 1' },
    { value: 'scope_2', label: 'Scope 2' },
    { value: 'scope_3', label: 'Scope 3' },
  ]

  return (
    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
      {options.map((opt) => (
        <button
          key={opt.value}
          className={`btn ${scopeFilter === opt.value ? 'btn-primary' : ''}`}
          style={{ fontSize: '12px', padding: '6px 12px' }}
          onClick={() => setScopeFilter(opt.value)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}

export default function Trends() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [scopeFilter, setScopeFilter] = useState('all')

  useEffect(() => {
    getOrganisations()
      .then((orgs) => {
        if (!orgs || orgs.length === 0) throw new Error('No organisations found')
        return getTrends(orgs[0].id)
      })
      .then((res) => setData(res.data_points || []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{ color: 'var(--text-muted)' }}>Loading...</div>
  )
  if (error) return (
    <div style={{ color: 'var(--status-bad)' }}>Error: {error}</div>
  )
  if (data.length === 0) return (
    <div>
      <h1 style={{ marginBottom: '8px' }}>Trends</h1>
      <p style={{ color: 'var(--text-muted)' }}>
        No trend data available. Run calculations first.
      </p>
    </div>
  )

  // Format data points for charts
  const chartData = data.map((d) => ({
    ...d,
    label: d.period_month
      ? `${MONTH_NAMES[d.period_month]} ${d.period_year}`
      : `${d.period_year}`,
  }))

  // Visible lines based on filter
  const showScope1 = scopeFilter === 'all' || scopeFilter === 'scope_1'
  const showScope2 = scopeFilter === 'all' || scopeFilter === 'scope_2'
  const showScope3 = scopeFilter === 'all' || scopeFilter === 'scope_3'

  // Summary stats
  const totalEmissions = data.reduce((sum, d) => sum + d.total_tco2e, 0)
  const avgPerPeriod = totalEmissions / data.length
  const maxPeriod = data.reduce((max, d) =>
    d.total_tco2e > max.total_tco2e ? d : max, data[0]
  )

  const tooltipStyle = {
    background: 'var(--bg-surface)',
    border: '1px solid var(--border)',
    borderRadius: '6px',
    fontSize: '12px',
  }

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
          <h1>Trends</h1>
          <p style={{ color: 'var(--text-muted)', marginTop: '4px' }}>
            Emission trends across all reporting periods
          </p>
        </div>
        <FilterBar
          scopeFilter={scopeFilter}
          setScopeFilter={setScopeFilter}
        />
      </div>

      {/* ── Summary KPIs ─────────────────────────────────── */}
      <div style={{
        display: 'flex',
        gap: '16px',
        marginBottom: '24px',
        flexWrap: 'wrap',
      }}>
        {[
          {
            label: 'Total Reported',
            value: `${totalEmissions.toFixed(2)} t`,
            sub: 'tCO₂e across all periods',
          },
          {
            label: 'Avg per Period',
            value: `${avgPerPeriod.toFixed(2)} t`,
            sub: 'tCO₂e average',
          },
          {
            label: 'Peak Period',
            value: maxPeriod.label ||
              `${MONTH_NAMES[maxPeriod.period_month] || ''} ${maxPeriod.period_year}`,
            sub: `${maxPeriod.total_tco2e.toFixed(2)} tCO₂e`,
          },
        ].map((kpi) => (
          <div key={kpi.label} className="card" style={{ flex: 1, minWidth: '180px' }}>
            <div style={{
              fontSize: '11px',
              fontWeight: '500',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: 'var(--text-muted)',
              marginBottom: '8px',
            }}>
              {kpi.label}
            </div>
            <div style={{
              fontSize: '24px',
              fontWeight: '700',
              color: 'var(--text-primary)',
              lineHeight: 1,
              marginBottom: '4px',
            }}>
              {kpi.value}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              {kpi.sub}
            </div>
          </div>
        ))}
      </div>

      {/* ── Total emissions line chart ────────────────────── */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h2 style={{ marginBottom: '20px' }}>Total CO₂e by Period</h2>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={chartData} margin={{ right: 16 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              vertical={false}
              stroke="var(--border)"
            />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${v}t`}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(v) => [`${v.toFixed(2)} tCO₂e`, 'Total']}
            />
            <Line
              type="monotone"
              dataKey="total_tco2e"
              stroke="var(--text-primary)"
              strokeWidth={2}
              dot={{ r: 4, fill: 'var(--text-primary)' }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* ── Scope stacked area chart ──────────────────────── */}
      <div className="card">
        <h2 style={{ marginBottom: '20px' }}>Scope Breakdown over Time</h2>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={chartData} margin={{ right: 16 }}>
            <defs>
              <linearGradient id="s1" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0A0A0A" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#0A0A0A" stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id="s2" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#525252" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#525252" stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id="s3" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#A3A3A3" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#A3A3A3" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              vertical={false}
              stroke="var(--border)"
            />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${v}t`}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(v, name) => [
                `${v.toFixed(2)} tCO₂e`,
                name.replace('_tco2e', '').replace('_', ' ').replace('scope', 'Scope'),
              ]}
            />
            <Legend
              formatter={(value) =>
                value.replace('_tco2e', '').replace('_', ' ').replace('scope', 'Scope ')
              }
              wrapperStyle={{ fontSize: '12px', color: 'var(--text-secondary)' }}
            />
            {showScope1 && (
              <Area
                type="monotone"
                dataKey="scope_1_tco2e"
                stroke={SCOPE_COLOURS.scope_1}
                strokeWidth={2}
                fill="url(#s1)"
              />
            )}
            {showScope2 && (
              <Area
                type="monotone"
                dataKey="scope_2_tco2e"
                stroke={SCOPE_COLOURS.scope_2}
                strokeWidth={2}
                fill="url(#s2)"
              />
            )}
            {showScope3 && (
              <Area
                type="monotone"
                dataKey="scope_3_tco2e"
                stroke={SCOPE_COLOURS.scope_3}
                strokeWidth={2}
                fill="url(#s3)"
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}