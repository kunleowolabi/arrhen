import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import {
  getOrganisations,
  getSiteBreakdown,
  getEmissionIntensity,
} from '../api/client'

// Marker colours for dark map
const INTENSITY_COLOUR = (score) => {
  if (score >= 0.66) return '#FFFFFF'
  if (score >= 0.33) return '#AAAAAA'
  return '#666666'
}

function AddSiteModal({ orgId, onClose, onSaved }) {
  const [form, setForm] = useState({
    name: '', site_code: '', region: '',
    country: 'Nigeria', address: '',
    latitude: '', longitude: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleSubmit = async () => {
    if (!form.name || !form.country) {
      setError('Name and country are required.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const res = await fetch(
        `${API_BASE}/api/v1/organisations/${orgId}/sites`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...form,
            latitude: form.latitude ? parseFloat(form.latitude) : null,
            longitude: form.longitude ? parseFloat(form.longitude) : null,
          }),
        }
      )
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to create site')
      }
      onSaved()
      onClose()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
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
        padding: '32px',
        background: 'var(--bg-surface)',
      }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', marginBottom: '28px',
        }}>
          <h2>Add Site</h2>
          <button className="btn" style={{ padding: '4px 12px' }} onClick={onClose}>✕</button>
        </div>

        {fields.map((f) => (
          <div key={f.name} style={{ marginBottom: '16px' }}>
            <label style={{
              display: 'block',
              fontSize: '11px', fontWeight: '600',
              textTransform: 'uppercase', letterSpacing: '0.05em',
              color: 'var(--text-muted)', marginBottom: '6px',
            }}>
              {f.label}{f.required && ' *'}
            </label>
            <input name={f.name} value={form[f.name]} onChange={handleChange} placeholder={f.label} />
          </div>
        ))}

        {error && (
          <div style={{ fontSize: '12px', color: 'var(--status-bad)', marginBottom: '16px' }}>
            {error}
          </div>
        )}

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
  const [showModal, setShowModal] = useState(false)
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

  const mapCenter = [9.0820, 8.6753]

  // Portfolio average for reference line
  const avg = sites.length > 0
    ? sites.reduce((sum, s) => sum + s.total_co2e_tonnes, 0) / sites.length
    : 0

  // Site comparison chart data
  const siteChartData = sites.map((s) => ({
    name: s.site_code,
    value: s.total_co2e_tonnes,
  }))

  // Regional aggregation
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
      {/* ── Header ─────────────────────────────────────── */}
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

      {/* ── Map — CartoDB Dark Matter ───────────────────── */}
      <div style={{
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
        border: '1px solid var(--border)',
        marginBottom: '20px',
      }}>
        <div style={{ height: 'clamp(220px, 40vw, 400px)' }}>
          <MapContainer
            center={mapCenter}
            zoom={6}
            style={{ height: '100%', width: '100%' }}
            scrollWheelZoom={true}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />
            {geoData.map((feature) => {
              const { coordinates } = feature.geometry
              const props = feature.properties
              const isSelected = selectedSite === props.site_code
              return (
                <CircleMarker
                  key={props.id}
                  center={[coordinates[1], coordinates[0]]}
                  radius={isSelected ? 14 : 10}
                  pathOptions={{
                    color: INTENSITY_COLOUR(props.intensity_score),
                    fillColor: INTENSITY_COLOUR(props.intensity_score),
                    fillOpacity: isSelected ? 1 : 0.8,
                    weight: isSelected ? 2 : 1,
                  }}
                  eventHandlers={{
                    click: () => setSelectedSite(
                      isSelected ? null : props.site_code
                    ),
                  }}
                >
                  <Popup>
                    <div style={{
                      fontSize: '13px',
                      minWidth: '160px',
                      fontFamily: "'Raleway', sans-serif",
                    }}>
                      <div style={{ fontWeight: '600', marginBottom: '4px' }}>
                        {props.name}
                      </div>
                      <div style={{ color: '#888', fontSize: '12px' }}>
                        {props.site_code} · {props.region}
                      </div>
                      <hr style={{ margin: '8px 0', borderColor: '#E4E4E4' }} />
                      <div style={{ fontWeight: '600' }}>
                        {props.total_co2e_tonnes} tCO₂e
                      </div>
                      <div style={{ color: '#888', fontSize: '11px' }}>
                        {props.record_count} records
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              )
            })}
          </MapContainer>
        </div>

        {/* Map legend */}
        <div style={{
          padding: '10px 20px',
          background: '#111111',
          display: 'flex',
          gap: '20px',
          alignItems: 'center',
          flexWrap: 'wrap',
        }}>
          <span style={{ fontSize: '10px', color: '#555', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            Emission intensity
          </span>
          {[
            { label: 'High', colour: '#FFFFFF' },
            { label: 'Medium', colour: '#AAAAAA' },
            { label: 'Low', colour: '#666666' },
          ].map((item) => (
            <div key={item.label} style={{
              display: 'flex', alignItems: 'center',
              gap: '6px', fontSize: '12px', color: '#888',
            }}>
              <div style={{
                width: '8px', height: '8px',
                borderRadius: '50%',
                background: item.colour,
              }} />
              {item.label}
            </div>
          ))}
          <span style={{ marginLeft: 'auto', fontSize: '10px', color: '#444' }}>
            Scroll to zoom · Click marker for details
          </span>
        </div>
      </div>

      {/* ── Charts row ────────────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '20px',
        marginBottom: '20px',
      }}>
        {/* Site comparison */}
        <div className="card">
          <div style={{ marginBottom: '16px' }}>
            <h2>Emissions by Site</h2>
            <p style={{
              fontSize: '12px',
              color: 'var(--text-muted)',
              marginTop: '2px',
            }}>
              Portfolio average {avg.toFixed(1)} tCO₂e
            </p>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart
              data={siteChartData}
              margin={{ left: 0, right: 8, top: 4, bottom: 4 }}
              barSize={16}
            >
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-muted)', fontFamily: 'Raleway' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)', fontFamily: 'Raleway' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}t`} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v.toFixed(2)} tCO₂e`, 'Emissions']} />
              <ReferenceLine y={avg} stroke="var(--text-muted)" strokeDasharray="4 4" label={{ value: 'Avg', position: 'insideTopRight', fontSize: 9, fill: 'var(--text-muted)', fontFamily: 'Raleway' }} />
              <Bar dataKey="value" fill="var(--black)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Regional intensity */}
        <div className="card">
          <div style={{ marginBottom: '16px' }}>
            <h2>Emissions by Region</h2>
            <p style={{
              fontSize: '12px',
              color: 'var(--text-muted)',
              marginTop: '2px',
            }}>
              Regional average {regionAvg.toFixed(1)} tCO₂e
            </p>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart
              data={regionChartData}
              layout="vertical"
              margin={{ left: 0, right: 8, top: 4, bottom: 4 }}
              barSize={14}
            >
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

      {/* ── Sites table ────────────────────────────────── */}
      <div className="card" style={{ padding: '24px' }}>
        <h2 style={{ marginBottom: '18px' }}>All Sites</h2>
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Site Code</th>
                <th>Name</th>
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
                    onClick={() => setSelectedSite(selectedSite === site.site_code ? null : site.site_code)}
                  >
                    <td style={{ color: 'var(--text-muted)' }}>{site.rank}</td>
                    <td>
                      <span style={{ fontWeight: selectedSite === site.site_code ? '700' : '600', color: 'var(--text-primary)' }}>
                        {site.site_code}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-secondary)' }}>{site.site_name}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{site.region || '—'}</td>
                    <td style={{ textAlign: 'right', fontWeight: '600', color: 'var(--text-primary)' }}>
                      {site.total_co2e_tonnes.toLocaleString()}
                    </td>
                    <td style={{ textAlign: 'right', color: 'var(--text-muted)' }}>
                      {site.record_count}
                    </td>
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
