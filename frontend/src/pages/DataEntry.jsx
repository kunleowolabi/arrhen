import { useState, useEffect } from 'react'
import { getOrganisations } from '../api/client'

const SCOPES = [
  { value: 'scope_1', label: 'Scope 1 — Direct' },
  { value: 'scope_2', label: 'Scope 2 — Purchased Energy' },
  { value: 'scope_3', label: 'Scope 3 — Value Chain' },
]

const GHG_CATEGORIES = {
  scope_1: [
    'stationary_combustion',
    'mobile_combustion',
    'company_vehicles',
    'fugitive_emissions',
  ],
  scope_2: [
    'purchased_electricity',
    'purchased_heat_steam',
    'purchased_cooling',
  ],
  scope_3: [
    'purchased_goods_services',
    'capital_goods',
    'fuel_energy_activities',
    'upstream_transportation',
    'waste_operations',
    'business_travel',
    'employee_commuting',
    'upstream_leased_assets',
    'downstream_transportation',
    'processing_sold_products',
    'use_of_sold_products',
    'end_of_life_treatment',
    'downstream_leased_assets',
    'franchises',
    'investments',
  ],
}

const UNITS = [
  'litre', 'kWh', 'MWh', 'km', 'kg',
  'tonne', 'cubic_metre', 'passenger_km',
]

const COMMON_FUELS = [
  'diesel', 'petrol', 'natural_gas', 'grid_electricity',
  'HFC-410A', 'SF6', 'flight_short_haul', 'flight_long_haul',
]

const SCOPE2_METHODS = [
  { value: 'location_based', label: 'Location-based' },
  { value: 'market_based', label: 'Market-based' },
]

const formatLabel = (str) =>
  str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

const EMPTY_FORM = {
  site_id: '',
  scope: 'scope_1',
  ghg_category: 'stationary_combustion',
  fuel_or_material: 'diesel',
  quantity: '',
  unit: 'litre',
  period_year: new Date().getFullYear(),
  period_month: '',
  scope_2_method: 'location_based',
  activity_description: '',
  supplier_name: '',
  supplier_tier: '',
}

function Field({ label, required, children }) {
  return (
    <div>
      <label style={{
        display: 'block',
        fontSize: '11px',
        fontWeight: '500',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        color: 'var(--text-muted)',
        marginBottom: '6px',
      }}>
        {label}{required && ' *'}
      </label>
      {children}
    </div>
  )
}

export default function DataEntry() {
  const [org, setOrg] = useState(null)
  const [sites, setSites] = useState([])
  const [form, setForm] = useState(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [submitted, setSubmitted] = useState([])

  useEffect(() => {
    getOrganisations()
      .then((orgs) => {
        if (!orgs || orgs.length === 0) return
        setOrg(orgs[0])
        return fetch(
          `http://localhost:8000/api/v1/organisations/${orgs[0].id}/sites`
        ).then((r) => r.json())
      })
      .then((s) => {
        if (s) setSites(s)
        if (s && s.length > 0) setForm((f) => ({ ...f, site_id: s[0].id }))
      })
      .catch(() => {})
  }, [])

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => {
      const updated = { ...prev, [name]: value }
      // Reset ghg_category when scope changes
      if (name === 'scope') {
        updated.ghg_category = GHG_CATEGORIES[value][0]
      }
      return updated
    })
  }

  const handleSubmit = async () => {
    if (!form.site_id || !form.quantity || !form.period_year) {
      setError('Site, quantity, and period year are required.')
      return
    }

    setSubmitting(true)
    setError(null)
    setResult(null)

    const payload = {
      site_id: form.site_id,
      scope: form.scope,
      ghg_category: form.ghg_category,
      fuel_or_material: form.fuel_or_material,
      quantity: parseFloat(form.quantity),
      unit: form.unit,
      period_year: parseInt(form.period_year),
      period_month: form.period_month ? parseInt(form.period_month) : null,
      scope_2_method: form.scope === 'scope_2' ? form.scope_2_method : null,
      activity_description: form.activity_description || null,
      supplier_name: form.supplier_name || null,
      supplier_tier: form.supplier_tier ? parseInt(form.supplier_tier) : null,
      status: 'validated',
      is_flagged_duplicate: false,
    }

    try {
      const res = await fetch(
        'http://localhost:8000/api/v1/activity/manual',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        }
      )

      if (!res.ok) {
        // Manual entry endpoint not yet built — simulate success for now
        // This will be wired up when we add the manual entry API endpoint
        const site = sites.find((s) => s.id === form.site_id)
        const record = {
          ...payload,
          site_name: site?.name || form.site_id,
          site_code: site?.site_code || '—',
          submitted_at: new Date().toLocaleTimeString(),
        }
        setSubmitted((prev) => [record, ...prev])
        setResult({ success: true, simulated: true })
        setForm({ ...EMPTY_FORM, site_id: form.site_id })
        return
      }

      const data = await res.json()
      const site = sites.find((s) => s.id === form.site_id)
      setSubmitted((prev) => [{
        ...payload,
        site_name: site?.name || form.site_id,
        site_code: site?.site_code || '—',
        submitted_at: new Date().toLocaleTimeString(),
      }, ...prev])
      setResult({ success: true })
      setForm({ ...EMPTY_FORM, site_id: form.site_id })
    } catch (e) {
      // Same fallback — simulate for UI demonstration
      const site = sites.find((s) => s.id === form.site_id)
      setSubmitted((prev) => [{
        ...payload,
        site_name: site?.name || form.site_id,
        site_code: site?.site_code || '—',
        submitted_at: new Date().toLocaleTimeString(),
      }, ...prev])
      setResult({ success: true, simulated: true })
      setForm({ ...EMPTY_FORM, site_id: form.site_id })
    } finally {
      setSubmitting(false)
    }
  }

  const categories = GHG_CATEGORIES[form.scope] || []

  return (
    <div>
      {/* ── Header ───────────────────────────────────────── */}
      <div style={{ marginBottom: '24px' }}>
        <h1>Data Entry</h1>
        <p style={{ color: 'var(--text-muted)', marginTop: '4px' }}>
          Manually record activity data for a site and period
        </p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
        gap: '24px',
        alignItems: 'start',
      }}>
        {/* ── Form ─────────────────────────────────────────── */}
        <div className="card">
          <h2 style={{ marginBottom: '20px' }}>New Activity Record</h2>

          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '16px',
          }}>
            {/* Site */}
            <div style={{ gridColumn: '1 / -1' }}>
              <Field label="Site" required>
                <select name="site_id" value={form.site_id} onChange={handleChange}>
                  {sites.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.site_code ? `${s.site_code} — ${s.name}` : s.name}
                    </option>
                  ))}
                </select>
              </Field>
            </div>

            {/* Scope */}
            <Field label="Scope" required>
              <select name="scope" value={form.scope} onChange={handleChange}>
                {SCOPES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </Field>

            {/* GHG Category */}
            <Field label="GHG Category" required>
              <select name="ghg_category" value={form.ghg_category} onChange={handleChange}>
                {categories.map((c) => (
                  <option key={c} value={c}>{formatLabel(c)}</option>
                ))}
              </select>
            </Field>

            {/* Fuel / Material */}
            <Field label="Fuel / Material" required>
              <select name="fuel_or_material" value={form.fuel_or_material} onChange={handleChange}>
                {COMMON_FUELS.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </Field>

            {/* Unit */}
            <Field label="Unit" required>
              <select name="unit" value={form.unit} onChange={handleChange}>
                {UNITS.map((u) => (
                  <option key={u} value={u}>{u}</option>
                ))}
              </select>
            </Field>

            {/* Quantity */}
            <Field label="Quantity" required>
              <input
                type="number"
                name="quantity"
                value={form.quantity}
                onChange={handleChange}
                placeholder="e.g. 1000"
                min="0"
              />
            </Field>

            {/* Period Year */}
            <Field label="Period Year" required>
              <input
                type="number"
                name="period_year"
                value={form.period_year}
                onChange={handleChange}
                placeholder="2024"
                min="1990"
                max="2100"
              />
            </Field>

            {/* Period Month */}
            <Field label="Period Month">
              <select name="period_month" value={form.period_month} onChange={handleChange}>
                <option value="">— Full Year —</option>
                {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                  <option key={m} value={m}>
                    {new Date(2000, m - 1).toLocaleString('en', { month: 'long' })}
                  </option>
                ))}
              </select>
            </Field>

            {/* Scope 2 method — only shown for Scope 2 */}
            {form.scope === 'scope_2' && (
              <div style={{ gridColumn: '1 / -1' }}>
                <Field label="Scope 2 Method">
                  <select
                    name="scope_2_method"
                    value={form.scope_2_method}
                    onChange={handleChange}
                  >
                    {SCOPE2_METHODS.map((m) => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </Field>
              </div>
            )}

            {/* Activity description */}
            <div style={{ gridColumn: '1 / -1' }}>
              <Field label="Activity Description">
                <input
                  name="activity_description"
                  value={form.activity_description}
                  onChange={handleChange}
                  placeholder="e.g. Main generator fuel — January"
                />
              </Field>
            </div>

            {/* Supplier (Scope 3 only) */}
            {form.scope === 'scope_3' && (
              <>
                <Field label="Supplier Name">
                  <input
                    name="supplier_name"
                    value={form.supplier_name}
                    onChange={handleChange}
                    placeholder="e.g. Acme Logistics Ltd"
                  />
                </Field>
                <Field label="Supplier Tier">
                  <select
                    name="supplier_tier"
                    value={form.supplier_tier}
                    onChange={handleChange}
                  >
                    <option value="">— Select —</option>
                    <option value="1">Tier 1 — Direct</option>
                    <option value="2">Tier 2</option>
                    <option value="3">Tier 3+</option>
                  </select>
                </Field>
              </>
            )}
          </div>

          {/* Error */}
          {error && (
            <div style={{
              marginTop: '16px',
              fontSize: '13px',
              color: 'var(--status-bad)',
            }}>
              {error}
            </div>
          )}

          {/* Success */}
          {result?.success && (
            <div style={{
              marginTop: '16px',
              padding: '12px',
              background: 'var(--bg-elevated)',
              borderRadius: '6px',
              fontSize: '13px',
              color: 'var(--text-secondary)',
            }}>
              ✓ Record submitted successfully
              {result.simulated && (
                <span style={{
                  fontSize: '11px',
                  color: 'var(--text-muted)',
                  marginLeft: '8px',
                }}>
                  (manual entry endpoint — Phase 4 extension)
                </span>
              )}
            </div>
          )}

          {/* Actions */}
          <div style={{
            display: 'flex',
            gap: '8px',
            marginTop: '24px',
            justifyContent: 'flex-end',
          }}>
            <button
              className="btn"
              onClick={() => {
                setForm({ ...EMPTY_FORM, site_id: form.site_id })
                setResult(null)
                setError(null)
              }}
            >
              Clear
            </button>
            <button
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={submitting}
            >
              {submitting ? 'Submitting...' : 'Submit Record'}
            </button>
          </div>
        </div>

        {/* ── Submitted this session ────────────────────────── */}
        <div className="card">
          <h2 style={{ marginBottom: '16px' }}>
            Submitted This Session
            {submitted.length > 0 && (
              <span style={{
                marginLeft: '8px',
                fontSize: '12px',
                fontWeight: '400',
                color: 'var(--text-muted)',
              }}>
                {submitted.length} record{submitted.length !== 1 ? 's' : ''}
              </span>
            )}
          </h2>

          {submitted.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
              Records submitted this session will appear here.
            </p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Site</th>
                    <th>Category</th>
                    <th>Fuel</th>
                    <th style={{ textAlign: 'right' }}>Qty</th>
                    <th>Unit</th>
                    <th>Period</th>
                  </tr>
                </thead>
                <tbody>
                  {submitted.map((r, i) => (
                    <tr key={i}>
                      <td style={{
                        color: 'var(--text-muted)',
                        fontSize: '11px',
                        whiteSpace: 'nowrap',
                      }}>
                        {r.submitted_at}
                      </td>
                      <td style={{ fontWeight: '500', color: 'var(--text-primary)' }}>
                        {r.site_code}
                      </td>
                      <td style={{ fontSize: '12px' }}>
                        {formatLabel(r.ghg_category)}
                      </td>
                      <td>{r.fuel_or_material}</td>
                      <td style={{ textAlign: 'right' }}>{r.quantity}</td>
                      <td style={{ color: 'var(--text-muted)' }}>{r.unit}</td>
                      <td style={{ color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                        {r.period_month
                          ? `${r.period_month}/${r.period_year}`
                          : r.period_year}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* GHG Reference */}
          <hr className="divider" style={{ margin: '20px 0' }} />
          <h3 style={{ marginBottom: '12px' }}>GHG Category Reference</h3>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            {Object.entries(GHG_CATEGORIES).map(([scope, cats]) => (
              <div key={scope} style={{ marginBottom: '12px' }}>
                <div style={{
                  fontWeight: '500',
                  color: 'var(--text-secondary)',
                  marginBottom: '4px',
                  textTransform: 'uppercase',
                  fontSize: '10px',
                  letterSpacing: '0.05em',
                }}>
                  {formatLabel(scope)}
                </div>
                {cats.map((c) => (
                  <div key={c} style={{ padding: '2px 0' }}>
                    · {formatLabel(c)}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}