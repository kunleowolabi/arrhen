import { useState, useEffect } from 'react'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import {
  getOrganisations,
  getDashboardOverview,
} from '../api/client'

const SCOPE_COLOURS = ['#0A0A0A', '#525252', '#A3A3A3']

const abbreviate = (str) => {
  const map = {
    'stationary combustion': 'Stat. Comb.',
    'grid electricity': 'Grid Elec.',
    'flight long haul': 'Long Haul',
    'flight short haul': 'Short Haul',
    'company vehicles': 'Vehicles',
    'fugitive emissions': 'Fugitive',
    'business travel': 'Biz Travel',
    'natural gas': 'Nat. Gas',
    'purchased electricity': 'Purch. Elec.',
    'hfc-410a': 'HFC-410A',
    'diesel': 'Diesel',
    'petrol': 'Petrol',
    'sf6': 'SF6',
  }
  const lower = str.toLowerCase()
  return map[lower] || str.charAt(0).toUpperCase() + str.slice(1)
}

function StatCard({ label, value, sub }) {
  return (
    <div style={{
      background: 'var(--bg-elevated)',
      borderRadius: '8px',
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
        fontSize: '26px',
        fontWeight: '700',
        color: 'var(--text-primary)',
        lineHeight: 1,
        marginBottom: sub ? '6px' : 0,
      }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          {sub}
        </div>
      )}
    </div>
  )
}

function TargetProgressBar({ baseline, target, current }) {
  const maxValue = Math.max(baseline, current) * 1.05
  const targetPct = ((baseline - target) / maxValue) * 100
  const currentPct = ((baseline - current) / maxValue) * 100
  const currentClamped = Math.max(0, Math.min(currentPct, 100))
  const isRegressing = current > baseline
  const exceededTarget = current <= target

  return (
    <div style={{ marginTop: '28px' }}>
      {/* Track */}
      <div style={{
        position: 'relative',
        height: '6px',
        background: 'var(--bg-elevated)',
        borderRadius: '3px',
        marginBottom: '10px',
      }}>
        {/* Fill */}
        <div style={{
          position: 'absolute',
          left: 0,
          width: `${currentClamped}%`,
          height: '100%',
          background: isRegressing
            ? 'var(--text-muted)'
            : 'var(--text-primary)',
          borderRadius: '3px',
          transition: 'width 0.6s ease',
        }} />

        {/* Target tick */}
        <div style={{
          position: 'absolute',
          left: `${targetPct}%`,
          top: '-5px',
          width: '2px',
          height: '16px',
          background: 'var(--accent)',
          transform: 'translateX(-50%)',
        }} />

        {/* Current marker */}
        <div style={{
          position: 'absolute',
          left: `${currentClamped}%`,
          top: '50%',
          width: '12px',
          height: '12px',
          background: isRegressing
            ? 'var(--text-muted)'
            : 'var(--text-primary)',
          borderRadius: '50%',
          border: '2px solid var(--bg-surface)',
          transform: 'translate(-50%, -50%)',
          transition: 'left 0.6s ease',
        }} />
      </div>

      {/* Track labels */}
      <div style={{
        position: 'relative',
        fontSize: '10px',
        color: 'var(--text-muted)',
        height: '16px',
      }}>
        <span style={{ position: 'absolute', left: 0 }}>0%</span>
        <span style={{
          position: 'absolute',
          left: `${targetPct}%`,
          transform: 'translateX(-50%)',
          color: 'var(--text-secondary)',
          whiteSpace: 'nowrap',
        }}>
          Target
        </span>
        <span style={{ position: 'absolute', right: 0 }}>100%</span>
      </div>
    </div>
  )
}

function TargetBanner({ targets, total }) {
  const [showDetail, setShowDetail] = useState(false)

  if (!targets || targets.length === 0) return null
  const target = targets[0]

  const baseline = target.baseline_emissions_tco2e
  const targetCeiling = target.target_emissions_tco2e
  const current = total

  const reductionPct = baseline > 0
    ? ((baseline - current) / baseline * 100)
    : 0

  const isRegressing = current > baseline

  const signedPct = isRegressing
    ? `+${Math.abs(reductionPct).toFixed(1)}%`
    : `−${Math.abs(reductionPct).toFixed(1)}%`

  return (
    <div style={{
      border: '1px solid var(--border)',
      borderRadius: '10px',
      padding: '28px 32px',
      marginBottom: '32px',
      background: 'var(--bg-surface)',
    }}>
      {/* ── Header ─────────────────────────────────── */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '24px',
        flexWrap: 'wrap',
        gap: '12px',
      }}>
        <div>
          <div style={{
            fontSize: '11px',
            fontWeight: '500',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: 'var(--text-muted)',
            marginBottom: '6px',
          }}>
            Reduction Target
          </div>
          <div style={{
            fontSize: '14px',
            color: 'var(--text-secondary)',
          }}>
            Tracking progress toward your organisation's
            emission reduction commitment
          </div>
        </div>

        <button
          className="btn"
          style={{ fontSize: '12px', padding: '6px 16px' }}
          onClick={() => setShowDetail(!showDetail)}
        >
          Target {showDetail ? '↑' : '↓'}
        </button>
      </div>

      {/* ── Target detail panel ─────────────────────── */}
      {showDetail && (
        <div style={{
          background: 'var(--bg-elevated)',
          borderRadius: '8px',
          padding: '16px 20px',
          marginBottom: '24px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '16px',
        }}>
          {[
            { label: 'Target Name', value: target.target_name },
            {
              label: 'Commitment Period',
              value: `${target.baseline_year} → ${target.target_year}`,
            },
            {
              label: 'Reduction Goal',
              value: `${target.target_reduction_pct}%`,
            },
            {
              label: 'Framework',
              value: target.aligned_to || 'Internal',
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
                color: 'var(--text-primary)',
                fontWeight: '500',
              }}>
                {item.value}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Four stat cards ─────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
        gap: '12px',
      }}>
        <StatCard
          label="Baseline"
          value={`${baseline.toLocaleString()} t`}
          sub={`${target.baseline_year} reference year`}
        />
        <StatCard
          label="2030 Target"
          value={`${targetCeiling.toLocaleString()} t`}
          sub={`${target.target_reduction_pct}% reduction goal`}
        />
        <StatCard
          label="Current"
          value={`${current.toFixed(1)} t`}
          sub={`${new Date().getFullYear()} reporting year`}
        />
        <StatCard
          label="Status"
          value={`${Math.abs(reductionPct).toFixed(1)}%`}
          sub={
            isRegressing
              ? 'Increase from baseline'
              : 'Reduction from baseline'
          }
        />
      </div>

      {/* ── Progress bar ────────────────────────────── */}
      <TargetProgressBar
        baseline={baseline}
        target={targetCeiling}
        current={current}
      />
    </div>
  )
}

function KPICard({ label, value, sub }) {
  return (
    <div className="card" style={{ padding: '24px 28px' }}>
      <div style={{
        fontSize: '11px',
        fontWeight: '500',
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        color: 'var(--text-muted)',
        marginBottom: '12px',
      }}>
        {label}
      </div>
      <div style={{
        fontSize: '30px',
        fontWeight: '700',
        color: 'var(--text-primary)',
        lineHeight: 1,
        marginBottom: sub ? '8px' : 0,
      }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          {sub}
        </div>
      )}
    </div>
  )
}

export default function Overview() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const YEAR = 2024

  useEffect(() => {
    getOrganisations()
      .then((orgs) => {
        if (!orgs || orgs.length === 0) throw new Error('No organisations found')
        return getDashboardOverview(orgs[0].id, YEAR)
      })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{ color: 'var(--text-muted)', padding: '16px' }}>
      Loading...
    </div>
  )
  if (error) return (
    <div style={{ color: 'var(--status-bad)', padding: '16px' }}>
      Error: {error}
    </div>
  )

  const total = data.scope_breakdown.total_tco2e

  const scopeData = [
    { name: 'Scope 1', value: data.scope_breakdown.scope_1_tco2e },
    { name: 'Scope 2', value: data.scope_breakdown.scope_2_tco2e },
    { name: 'Scope 3', value: data.scope_breakdown.scope_3_tco2e },
  ]

  const sourceData = data.top_sources.map((s) => ({
    name: abbreviate(s.fuel_or_material.replace(/_/g, ' ')),
    value: s.total_co2e_tonnes,
  }))

  const tooltipStyle = {
    background: 'var(--bg-surface)',
    border: '1px solid var(--border)',
    borderRadius: '6px',
    fontSize: '12px',
  }

  return (
    <div>
      {/* ── Page header ───────────────────────────────── */}
      <div style={{ marginBottom: '32px' }}>
        <h1>{data.organisation_name}</h1>
        <p style={{ color: 'var(--text-muted)', marginTop: '6px' }}>
          {YEAR} Emission Summary
        </p>
      </div>

      {/* ── Target banner ─────────────────────────────── */}
      <TargetBanner
        targets={data.target_progress}
        total={total}
      />

      {/* ── Middle: donut + KPI 2×2 ───────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '24px',
        marginBottom: '24px',
      }}>
        {/* Scope donut */}
        <div className="card" style={{ padding: '28px' }}>
          <h2 style={{ marginBottom: '20px' }}>Scope Breakdown</h2>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={scopeData}
                cx="50%"
                cy="50%"
                innerRadius={40}
                outerRadius={88}
                paddingAngle={3}
                dataKey="value"
              >
                {scopeData.map((_, i) => (
                  <Cell key={i} fill={SCOPE_COLOURS[i]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v) => [`${v.toFixed(2)} tCO₂e`]}
                contentStyle={tooltipStyle}
              />
            </PieChart>
          </ResponsiveContainer>
          <div style={{
            display: 'flex',
            gap: '20px',
            justifyContent: 'center',
            marginTop: '12px',
          }}>
            {scopeData.map((s, i) => (
              <div key={i} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '7px',
                fontSize: '12px',
                color: 'var(--text-secondary)',
              }}>
                <div style={{
                  width: '8px', height: '8px',
                  borderRadius: '50%',
                  background: SCOPE_COLOURS[i],
                  flexShrink: 0,
                }} />
                {s.name}
              </div>
            ))}
          </div>
        </div>

        {/* KPI 2×2 grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gridTemplateRows: '1fr 1fr',
          gap: '16px',
        }}>
          <KPICard
            label="Total CO₂e"
            value={`${total.toLocaleString()} t`}
            sub="All scopes combined"
          />
          <KPICard
            label="Scope 1"
            value={`${data.scope_breakdown.scope_1_tco2e.toLocaleString()} t`}
            sub="Direct emissions"
          />
          <KPICard
            label="Scope 2"
            value={`${data.scope_breakdown.scope_2_tco2e.toLocaleString()} t`}
            sub="Purchased energy"
          />
          <KPICard
            label="Scope 3"
            value={`${data.scope_breakdown.scope_3_tco2e.toLocaleString()} t`}
            sub="Value chain"
          />
        </div>
      </div>

      {/* ── Bottom: top sites + top sources ───────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '24px',
      }}>
        {/* Top emitting sites */}
        <div className="card" style={{ padding: '28px' }}>
          <h2 style={{ marginBottom: '20px' }}>Top Emitting Sites</h2>
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Site</th>
                <th>Region</th>
                <th style={{ textAlign: 'right' }}>tCO₂e</th>
              </tr>
            </thead>
            <tbody>
              {data.top_sites.map((site) => (
                <tr key={site.site_code}>
                  <td style={{ color: 'var(--text-muted)' }}>
                    {site.rank}
                  </td>
                  <td style={{
                    color: 'var(--text-primary)',
                    fontWeight: '500',
                  }}>
                    {site.site_code}
                  </td>
                  <td>{site.region}</td>
                  <td style={{
                    textAlign: 'right',
                    fontWeight: '500',
                    color: 'var(--text-primary)',
                  }}>
                    {site.total_co2e_tonnes.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Top emission sources */}
        <div className="card" style={{ padding: '28px' }}>
          <h2 style={{ marginBottom: '20px' }}>Top Emission Sources</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={sourceData}
              layout="vertical"
              margin={{ left: 0, right: 16, top: 4, bottom: 4 }}
              barSize={10}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                horizontal={false}
                stroke="var(--border)"
              />
              <XAxis
                type="number"
                tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
                axisLine={false}
                tickLine={false}
                width={80}
              />
              <Tooltip
                formatter={(v) => [`${v.toFixed(2)} tCO₂e`]}
                contentStyle={tooltipStyle}
              />
              <Bar
                dataKey="value"
                fill="var(--text-primary)"
                radius={[0, 3, 3, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}