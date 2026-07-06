import { useState, useEffect } from 'react'
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
import { SitesSkeleton } from '../components/Skeleton'

// OpenFreeMap dark — free, no API key, rich geographic texture
const MAP_STYLE = 'https://tiles.openfreemap.org/styles/dark'

function SiteMarker({ feature, isSelected, onSelect, onPopup }) {
  const [hovered, setHovered] = useState(false)
  const props = feature.properties
  const co2e = props.total_co2e_tonnes
    ? parseFloat(props.total_co2e_tonnes).toFixed(1)
    : '—'

  return (
    <div
      onClick={() => onSelect()}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        position: 'relative',
        width: 12,
        height: 12,
        cursor: 'pointer',
      }}
    >
      {/* Pulsing ring */}
      <div style={{
        position: 'absolute',
        width: 32,
        height: 32,
        borderRadius: '50%',
        background: 'rgba(255,255,255,0.18)',
        top: '50%',
        left: '50%',
        animation: 'pulse-ring 2.4s ease-out infinite',
        pointerEvents: 'none',
      }} />

      {/* Centre dot */}
      <div style={{
        width: 12,
        height: 12,
        borderRadius: '50%',
        background: isSelected ? '#FFFFFF' : 'rgba(255,255,255,0.9)',
        border: `2px solid rgba(255,255,255,${isSelected ? 0.9 : 0.4})`,
        boxShadow: isSelected
          ? '0 0 0 4px rgba(255,255,255,0.15), 0 2px 8px rgba(0,0,0,0.6)'
          : '0 1px 4px rgba(0,0,0,0.5)',
        position: 'relative',
        zIndex: 2,
        transition: 'all 0.15s ease',
      }} />

      {/* Hover label */}
      {hovered && !isSelected && (
        <div style={{
          position: 'absolute',
          bottom: '22px',
          left: '50%',
          transform: 'translateX(-50%)',
          background: 'rgba(8,8,8,0.88)',
          backdropFilter: 'blur(6px)',
          border: '1px solid rgba(255,255,255,0.12)',
          borderRadius: '7px',
          padding: '6px 10px',
          zIndex: 100,
          pointerEvents: 'none',
          whiteSpace: 'nowrap',
          fontFamily: "'Raleway', sans-serif",
        }}>
          <div style={{
            fontSize: '9px',
            fontWeight: '600',
            color: 'rgba(255,255,255,0.5)',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            marginBottom: '2px',
          }}>
            {props.site_code}
          </div>
          <div style={{
            fontSize: '12px',
            fontWeight: '700',
            color: '#FFFFFF',
          }}>
            {co2e} tCO₂e
          </div>
        </div>
      )}
    </div>
  )
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
    setSaving(true); setError(null)
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
    zoom: 5.2,
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

  if (loading) return <SitesSkeleton />
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
      {/* ── Header ───────────────────────────────────── */}
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

      {/* ── Map ──────────────────────────────────────── */}
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
            <NavigationControl
              position="top-right"
              style={{
                marginTop: '12px',
                marginRight: '12px',
              }}
            />

            {geoData.map((feature) => {
              const [lng, lat] = feature.geometry.coordinates
              const props = feature.properties
              const isSelected = selectedSite === props.site_code

              return (
                <Marker
                  key={props.id}
                  longitude={lng}
                  latitude={lat}
                  anchor="center"
                >
                  <SiteMarker
                    feature={feature}
                    isSelected={isSelected}
                    onSelect={() => {
                      const next = isSelected ? null : props.site_code
                      setSelectedSite(next)
                      setPopupInfo(next ? { lng, lat, props } : null)
                    }}
                  />
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
                offset={20}
              >
                <div style={{
                  fontSize: '13px',
                  minWidth: '160px',
                  fontFamily: "'Raleway', sans-serif",
                  padding: '4px 2px',
                }}>
                  <div style={{ fontWeight: '700', marginBottom: '2px' }}>
                    {popupInfo.props.name}
                  </div>
                  <div style={{ color: '#888', fontSize: '11px', marginBottom: '10px' }}>
                    {popupInfo.props.site_code} · {popupInfo.props.region}
                  </div>
                  <div style={{ fontWeight: '700', fontSize: '16px' }}>
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
          gap: '16px',
          alignItems: 'center',
          flexWrap: 'wrap',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              position: 'relative',
              width: 12, height: 12,
            }}>
              <div style={{
                position: 'absolute',
                inset: 0,
                borderRadius: '50%',
                background: 'rgba(0,0,0,0.15)',
                transform: 'scale(2.2)',
              }} />
              <div style={{
                width: 12, height: 12,
                borderRadius: '50%',
                background: '#0A0A0A',
                border: '2px solid rgba(0,0,0,0.3)',
                position: 'relative',
              }} />
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Emission site · hover for data · click for detail
            </span>
          </div>
          <span style={{ marginLeft: 'auto', fontSize: '10px', color: 'var(--text-muted)' }}>
            Scroll to zoom
          </span>
        </div>
      </div>

      {/* ── Charts ───────────────────────────────────── */}
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
              <CartesianGrid strokeDasharray="1 6" vertical={false} stroke="rgba(0,0,0,0.07)" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-muted)', fontFamily: 'Raleway' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)', fontFamily: 'Raleway' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}t`} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v.toFixed(2)} tCO₂e`, 'Emissions']} />
              <ReferenceLine y={avg} stroke="var(--text-muted)" strokeDasharray="4 4" label={{ value: 'Avg', position: 'insideTopRight', fontSize: 9, fill: 'var(--text-muted)' }} />
              <Bar dataKey="value" fill="var(--black)" radius={[4, 4, 0, 0]} />
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
              <CartesianGrid strokeDasharray="1 6" horizontal={false} stroke="rgba(0,0,0,0.07)" />
              <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-muted)', fontFamily: 'Raleway' }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-muted)', fontFamily: 'Raleway' }} axisLine={false} tickLine={false} width={80} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v.toFixed(2)} tCO₂e`, 'Emissions']} />
              <ReferenceLine x={regionAvg} stroke="var(--text-muted)" strokeDasharray="4 4" />
              <Bar dataKey="value" fill="var(--black)" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Sites table ───────────────────────────────── */}
      <div className="card" style={{ padding: '24px' }}>
        <h2 style={{ marginBottom: '18px' }}>All Sites</h2>
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>Rank</th><th>Site Code</th><th>Name</th>
                <th>Region</th>
                <th>tCO₂e</th>
                <th>Records</th>
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
                    <td style={{
 fontWeight: '600', color: 'var(--text-primary)' }}>
                      {site.total_co2e_tonnes.toLocaleString()}
                    </td>
                    <td style={{
 color: 'var(--text-muted)' }}>{site.record_count}</td>
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
