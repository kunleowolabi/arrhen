import { useState, useEffect, useRef } from 'react'
import Map, { Marker, Popup, NavigationControl } from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import {
  getOrganisations,
  getSiteBreakdown,
  getEmissionIntensity,
} from '../api/client'

// CartoDB Dark Matter GL style — free, no API key
// Dark Matter No Labels — clean dark basemap, no text clutter at any zoom level
const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json'

const INTENSITY_COLOUR = (score) => {
  if (score >= 0.66) return '#FFFFFF'
  if (score >= 0.33) return '#BBBBBB'
  return '#888888'
}

function AddSiteModal({ orgId, onClose, onSaved }) {
  const [form, setForm] = useState({
    name: '', site_code: '', region: '',
    country: 'Nigeria', address: '',
    latitude: '', longitude: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const handleSubmit = async () => {
    if (!form.name || !form.country) { setError('Name and country are required.'); return }
    setSaving(true)
    setError(null)
    try {
      const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const res = await fetch(`${API_BASE}/api/v1/organisations/${orgId}/sites`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...form,
          latitude: form.latitude ? parseFloat(form.latitude) : null,
          longitude: form.longitude ? parseFloat(form.longitude) : null,
        }),
      })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed') }
      onSaved(); onClose()
    } catch (e) { setError(e.message) } finally { setSaving(false) }
  }

  const fields = [
    { name: 'name', label: 'Site Name', required: true },
    { name: 'site_code', label: 'Site Code (e.g. LAGOS-01)' },
    { name: 'region', label: 'Region' },
    { name: 'country', label: 'Country', required: true },
    { name: 'address', label: 'Address' },
    { name: 'latitude', label: 'Latitude' },
    { name: 'longitude', label: 'Longitude' },
  ]

  return (
    <div style={{
      position: 'fixed', inset: 0,
      background: 'rgba(0,0,0,0.4)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000,
    }}>
      <div className="card" style={{
        width: '100%', maxWidth: '480px',
        maxHeight: '90vh', overflowY: 'auto',
        padding: '32px', background: 'var(--bg-surface)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '28px' }}>
          <h2>Add Site</h2>
          <button className="btn" style={{ padding: '4px 12px' }} onClick={onClose}>✕</button>
        </div>
        {fields.map((f) => (
          <div key={f.name} style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: '6px' }}>
              {f.label}{f.required && ' *'}
            </label>
            <input name={f.name} value={form[f.name]} onChange={handleChange} placeholder={f.label} />
          </div>
        ))}
        {error && <div style={{ fontSize: '12px', color: 'var(--status-bad)', marginBottom: '16px' }}>{error}</div>}
        <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '8px' }}>
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={saving}>
            {saving ? 'Saving...' : 'Add Site'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Sites() {
  const [org, setOrg] = useState(null)
  const [sites, setSites] = useState([])
  const [geoData, setGeoData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedSite, setSelectedSite] = useState(null)
  const [popupInfo, setPopupInfo] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [viewState, setViewState] = useState({
    longitude: 8.6753,
    latitude: 9.0820,
    zoom: 5.5,
  })
  const YEAR = 2024

  const loadData = (orgId) =>
    Promise.all([
      getSiteBreakdown(orgId, YEAR),
      getEmissionIntensity(orgId, YEAR),
    ]).then(([siteData, geoJSON]) => {
      setSites(siteData)
      setGeoData(geoJSON.features || [])
    })

  useEffect(() => {
    getOrganisations()
      .then((orgs) => {
        if (!orgs || orgs.length === 0) throw new Error('No organisations found')
        setOrg(orgs[0])
        return loadData(orgs[0].id)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div style={{ color: 'var(--text-muted)' }}>Loading...</div>
  if (error) return <div style={{ color: 'var(--status-bad)' }}>Error: {error}</div>

  const avg = sites.length > 0
    ? sites.reduce((sum, s) => sum + s.total_co2e_tonnes, 0) / sites.length
    : 0

  const siteChartData = sites.map((s) => ({
    name: s.site_code,
    value: s.total_co2e_tonnes,
  }))

  const regionMap = {}
  sites.forEach((s) => {
    const region = s.region || 'Unknown'
    if (!regionMap[region]) regionMap[region] = 0
    regionMap[region] += s.total_co2e_tonnes
  })
  const regionChartData = Object.entries(regionMap)
    .map(([name, value]) => ({ name, value: parseFloat(value.toFixed(3)) }))
    .sort((a, b) => b.value - a.value)

  const regionAvg = regionChartData.length > 0
    ? regionChartData.reduce((sum, r) => sum + r.value, 0) / regionChartData.length
    : 0

  const tooltipStyle = {
    background: 'var(--bg-surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-sm)',
    fontSize: '12px',
    fontFamily: "'Raleway', sans-serif",
  }

  return (
    <div>
      {/* ── Header ─────────────────────────────────── */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '28px',
        flexWrap: 'wrap',
        gap: '16px',
      }}>
        <div>
          <h1>Sites & Branches</h1>
          <p style={{ color: 'var(--text-muted)', marginTop: '4px' }}>
            {sites.length} active sites · {YEAR} emissions
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          + Add Site
        </button>
      </div>

      {/* ── Map — MapLibre GL + CartoDB Dark Matter ─── */}
      <div style={{
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
        border: '1px solid var(--border)',
        marginBottom: '20px',
      }}>
        <div style={{ height: '500px' }}>
          <Map
            {...viewState}
            onMove={(evt) => setViewState(evt.viewState)}
            mapStyle={MAP_STYLE}
            style={{ width: '100%', height: '100%' }}
          >
            <NavigationControl position="top-right" />

            {geoData.map((feature) => {
              const [lng, lat] = feature.geometry.coordinates
              const props = feature.properties
              const isSelected = selectedSite === props.site_code
              const colour = INTENSITY_COLOUR(props.intensity_score)

              return (
                <Marker
                  key={props.id}
                  longitude={lng}
                  latitude={lat}
                  anchor="center"
                  onClick={() => {
                    setSelectedSite(isSelected ? null : props.site_code)
                    setPopupInfo(isSelected ? null : { lng, lat, props })
                  }}
                >
                  <div style={{
                    width: isSelected ? 18 : 12,
                    height: isSelected ? 18 : 12,
                    borderRadius: '50%',
                    background: colour,
                    border: `2px solid rgba(255,255,255,${isSelected ? 0.9 : 0.4})`,
                    boxShadow: isSelected
                      ? `0 0 0 4px rgba(255,255,255,0.15)`
                      : '0 1px 4px rgba(0,0,0,0.5)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }} />
                </Marker>
              )
            })}

            {popupInfo && (
              <Popup
                longitude={popupInfo.lng}
                latitude={popupInfo.lat}
                anchor="bottom"
                onClose={() => { setPopupInfo(null); setSelectedSite(null) }}
                closeButton={false}
                offset={12}
              >
                <div style={{
                  fontSize: '13px',
                  minWidth: '160px',
                  fontFamily: "'Raleway', sans-serif",
                  padding: '4px',
                }}>
                  <div style={{ fontWeight: '700', marginBottom: '3px' }}>
                    {popupInfo.props.name}
                  </div>
                  <div style={{ color: '#888', fontSize: '11px', marginBottom: '8px' }}>
                    {popupInfo.props.site_code} · {popupInfo.props.region}
                  </div>
                  <div style={{ fontWeight: '700', fontSize: '15px' }}>
                    {popupInfo.props.total_co2e_tonnes} tCO₂e
                  </div>
                  <div style={{ color: '#888', fontSize: '11px', marginTop: '2px' }}>
                    {popupInfo.props.record_count} activity records
                  </div>
                </div>
              </Popup>
            )}
          </Map>
        </div>

        {/* Legend */}
        <div style={{
          padding: '10px 20px',
          background: 'var(--bg-surface)',
          borderTop: '1px solid var(--border)',
          display: 'flex',
          gap: '20px',
          alignItems: 'center',
          flexWrap: 'wrap',
        }}>
          <span style={{
            fontSize: '10px',
            color: 'var(--text-muted)',
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
          }}>
            Emission intensity
          </span>
          {[
            { label: 'High', colour: '#FFFFFF' },
            { label: 'Medium', colour: '#BBBBBB' },
            { label: 'Low', colour: '#888888' },
          ].map((item) => (
            <div key={item.label} style={{
              display: 'flex', alignItems: 'center',
              gap: '6px', fontSize: '12px',
              color: 'var(--text-secondary)',
            }}>
              <div style={{
                width: '10px', height: '10px',
                borderRadius: '50%',
                background: item.colour,
                border: '1px solid var(--border)',
              }} />
              {item.label}
            </div>
          ))}
          <span style={{ marginLeft: 'auto', fontSize: '10px', color: 'var(--text-muted)' }}>
            Scroll to zoom · Click marker for details
          </span>
        </div>
      </div>

      {/* ── Charts ─────────────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '20px',
        marginBottom: '20px',
      }}>
        <div className="card">
          <div style={{ marginBottom: '16px' }}>
            <h2>Emissions by Site</h2>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
              Portfolio average {avg.toFixed(1)} tCO₂e
            </p>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={siteChartData} margin={{ left: 0, right: 8, top: 4, bottom: 4 }} barSize={16}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-muted)', fontFamily: 'Raleway' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)', fontFamily: 'Raleway' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}t`} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v.toFixed(2)} tCO₂e`, 'Emissions']} />
              <ReferenceLine y={avg} stroke="var(--text-muted)" strokeDasharray="4 4" label={{ value: 'Avg', position: 'insideTopRight', fontSize: 9, fill: 'var(--text-muted)' }} />
              <Bar dataKey="value" fill="var(--black)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div style={{ marginBottom: '16px' }}>
            <h2>Emissions by Region</h2>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
              Regional average {regionAvg.toFixed(1)} tCO₂e
            </p>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={regionChartData} layout="vertical" margin={{ left: 0, right: 8, top: 4, bottom: 4 }} barSize={14}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border)" />
              <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-muted)', fontFamily: 'Raleway' }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-muted)', fontFamily: 'Raleway' }} axisLine={false} tickLine={false} width={80} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v.toFixed(2)} tCO₂e`, 'Emissions']} />
              <ReferenceLine x={regionAvg} stroke="var(--text-muted)" strokeDasharray="4 4" />
              <Bar dataKey="value" fill="var(--black)" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Sites table ────────────────────────────── */}
      <div className="card" style={{ padding: '24px' }}>
        <h2 style={{ marginBottom: '18px' }}>All Sites</h2>
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>Rank</th><th>Site Code</th><th>Name</th>
                <th>Region</th>
                <th style={{ textAlign: 'right' }}>tCO₂e</th>
                <th style={{ textAlign: 'right' }}>Records</th>
              </tr>
            </thead>
            <tbody>
              {sites.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px' }}>
                    No emission data for this period.
                  </td>
                </tr>
              ) : (
                sites.map((site) => (
                  <tr
                    key={site.site_code}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setSelectedSite(
                      selectedSite === site.site_code ? null : site.site_code
                    )}
                  >
                    <td style={{ color: 'var(--text-muted)' }}>{site.rank}</td>
                    <td><span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>{site.site_code}</span></td>
                    <td style={{ color: 'var(--text-secondary)' }}>{site.site_name}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{site.region || '—'}</td>
                    <td style={{ textAlign: 'right', fontWeight: '600', color: 'var(--text-primary)' }}>
                      {site.total_co2e_tonnes.toLocaleString()}
                    </td>
                    <td style={{ textAlign: 'right', color: 'var(--text-muted)' }}>{site.record_count}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && org && (
        <AddSiteModal
          orgId={org.id}
          onClose={() => setShowModal(false)}
          onSaved={() => loadData(org.id)}
        />
      )}
    </div>
  )
}
