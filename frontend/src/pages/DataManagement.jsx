import { useState, useEffect, useRef } from 'react'
import { getOrganisations, getLineage, uploadCSV } from '../api/client'

function UploadZone({ onUpload, uploading }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  const handleFile = (file) => {
    if (!file) return
    if (!file.name.endsWith('.csv')) {
      alert('Please upload a CSV file.')
      return
    }
    onUpload(file)
  }

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        handleFile(e.dataTransfer.files[0])
      }}
      style={{
        border: `2px dashed ${dragging
          ? 'var(--text-primary)'
          : 'var(--border)'}`,
        borderRadius: '8px',
        padding: '48px 32px',
        textAlign: 'center',
        cursor: uploading ? 'not-allowed' : 'pointer',
        background: dragging ? 'var(--bg-elevated)' : 'transparent',
        transition: 'all 0.15s',
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        style={{ display: 'none' }}
        onChange={(e) => handleFile(e.target.files[0])}
      />
      <div style={{
        fontSize: '32px',
        marginBottom: '12px',
        color: 'var(--text-muted)',
      }}>
        ↑
      </div>
      <div style={{
        fontSize: '14px',
        fontWeight: '500',
        color: 'var(--text-primary)',
        marginBottom: '4px',
      }}>
        {uploading
          ? 'Uploading...'
          : 'Drop CSV file here or click to browse'}
      </div>
      <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
        Accepts .csv files · Max 10MB
      </div>
    </div>
  )
}

function UploadResult({ result, onDismiss }) {
  if (!result) return null

  const hasErrors = result.errors && result.errors.length > 0
  const hasWarnings = result.warnings && result.warnings.length > 0

  return (
    <div style={{
      border: '1px solid var(--border)',
      borderRadius: '8px',
      overflow: 'hidden',
      marginTop: '16px',
    }}>
      <div style={{
        background: 'var(--bg-elevated)',
        padding: '16px 20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px',
      }}>
        <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
          {[
            { label: 'Total', value: result.total },
            { label: 'Valid', value: result.valid },
            { label: 'Quarantined', value: result.quarantined },
            { label: 'Duplicates', value: result.duplicate },
          ].map((stat) => (
            <div key={stat.label}>
              <div style={{
                fontSize: '18px',
                fontWeight: '700',
                color: 'var(--text-primary)',
              }}>
                {stat.value}
              </div>
              <div style={{
                fontSize: '10px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                color: 'var(--text-muted)',
              }}>
                {stat.label}
              </div>
            </div>
          ))}
        </div>
        <button
          className="btn"
          style={{ fontSize: '12px' }}
          onClick={onDismiss}
        >
          Dismiss
        </button>
      </div>

      {hasErrors && (
        <div style={{ padding: '16px 20px' }}>
          <div style={{
            fontSize: '11px',
            fontWeight: '500',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--text-muted)',
            marginBottom: '12px',
          }}>
            Quarantined Rows
          </div>
          {result.errors.map((err, i) => (
            <div key={i} style={{
              padding: '10px 12px',
              background: 'var(--bg-elevated)',
              borderRadius: '6px',
              marginBottom: '8px',
              fontSize: '12px',
            }}>
              <div style={{
                fontWeight: '500',
                color: 'var(--text-primary)',
                marginBottom: '4px',
              }}>
                Row {err.row}
              </div>
              {err.errors.map((e, j) => (
                <div key={j} style={{ color: 'var(--text-muted)' }}>
                  · {e}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {hasWarnings && (
        <div style={{ padding: '0 20px 16px' }}>
          <div style={{
            fontSize: '11px',
            fontWeight: '500',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--text-muted)',
            marginBottom: '12px',
          }}>
            Warnings
          </div>
          {result.warnings.map((w, i) => (
            <div key={i} style={{
              fontSize: '12px',
              color: 'var(--text-secondary)',
              marginBottom: '4px',
            }}>
              Row {w.row}: {w.warning}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function PendingStatus({ pending, onRefresh }) {
  if (!pending) return null

  const {
    pending_count,
    uploads_since_last_calc,
    last_calculated_at,
    is_up_to_date,
  } = pending

  const lastCalcLabel = last_calculated_at
    ? new Date(last_calculated_at).toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : 'Never'

  if (is_up_to_date) {
    return (
      <div style={{
        fontSize: '12px',
        color: 'var(--text-muted)',
        marginTop: '10px',
      }}>
        ✓ All records up to date · Last calculated {lastCalcLabel}
      </div>
    )
  }

  return (
    <div style={{
      fontSize: '12px',
      color: 'var(--text-secondary)',
      marginTop: '10px',
    }}>
      <span style={{
        color: 'var(--text-primary)',
        fontWeight: '500',
      }}>
        {pending_count} records pending
      </span>
      {uploads_since_last_calc > 0 && (
        <span style={{ color: 'var(--text-muted)' }}>
          {' '}·{' '}
          {uploads_since_last_calc} upload
          {uploads_since_last_calc !== 1 ? 's' : ''} since
          last calculation
        </span>
      )}
      {last_calculated_at && (
        <span style={{ color: 'var(--text-muted)' }}>
          {' '}· Last calculated {lastCalcLabel}
        </span>
      )}
    </div>
  )
}

export default function DataManagement() {
  const [org, setOrg] = useState(null)
  const [lineage, setLineage] = useState([])
  const [pending, setPending] = useState(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [error, setError] = useState(null)
  const [calculating, setCalculating] = useState(false)
  const [calcResult, setCalcResult] = useState(null)
  const [elapsed, setElapsed] = useState(0)
  const elapsedRef = useRef(null)

  const loadLineage = () =>
    getLineage().then(setLineage).catch(() => {})

  const loadPending = (orgId) =>
    fetch(
      `http://localhost:8000/api/v1/calculations/pending?organisation_id=${orgId}`
    )
      .then((r) => r.json())
      .then(setPending)
      .catch(() => {})

  useEffect(() => {
    Promise.all([getOrganisations(), getLineage()])
      .then(([orgs, lin]) => {
        if (orgs && orgs.length > 0) {
          setOrg(orgs[0])
          loadPending(orgs[0].id)
        }
        setLineage(lin)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const handleUpload = async (file) => {
    if (!org) return
    setUploading(true)
    setUploadResult(null)
    setError(null)
    try {
      const result = await uploadCSV(org.id, file, 'dashboard_user')
      setUploadResult(result)
      loadLineage()
      loadPending(org.id)
    } catch (e) {
      setError(e.message)
    } finally {
      setUploading(false)
    }
  }

  const runCalculations = async () => {
    if (!org) return
    setCalculating(true)
    setCalcResult(null)
    setElapsed(0)

    // Start elapsed timer
    elapsedRef.current = setInterval(() => {
      setElapsed((s) => s + 1)
    }, 1000)

    try {
      const res = await fetch(
        'http://localhost:8000/api/v1/calculations/run',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            gwp_version: 'AR6',
            organisation_id: org.id,
          }),
        }
      )
      const data = await res.json()
      setCalcResult(data)
      loadPending(org.id)
    } catch (e) {
      setCalcResult({ error: e.message })
    } finally {
      clearInterval(elapsedRef.current)
      setCalculating(false)
    }
  }

  const downloadTemplate = () => {
    const headers = [
      'site_code', 'scope', 'ghg_category', 'fuel_or_material',
      'quantity', 'unit', 'period_year', 'period_month',
      'scope_2_method', 'activity_description',
      'supplier_name', 'supplier_tier',
    ].join(',')

    const example = [
      'LAGOS-HQ', '1', 'stationary_combustion', 'diesel',
      '1000', 'litre', '2024', '1',
      '', 'Generator fuel consumption', '', '',
    ].join(',')

    const content = `${headers}\n${example}`
    const blob = new Blob([content], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'carbon_platform_upload_template.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) return (
    <div style={{ color: 'var(--text-muted)' }}>Loading...</div>
  )

  return (
    <div>
      {/* ── Header ───────────────────────────────────────── */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '32px',
        flexWrap: 'wrap',
        gap: '16px',
      }}>
        <div>
          <h1>Data Management</h1>
          <p style={{ color: 'var(--text-muted)', marginTop: '6px' }}>
            Upload activity data and review ingestion history
          </p>
        </div>
        <button className="btn" onClick={downloadTemplate}>
          ↓ Download Template
        </button>
      </div>

      {/* ── Upload zone ───────────────────────────────────── */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h2 style={{ marginBottom: '16px' }}>Upload CSV</h2>
        <UploadZone onUpload={handleUpload} uploading={uploading} />
        {error && (
          <div style={{
            marginTop: '12px',
            fontSize: '13px',
            color: 'var(--status-bad)',
          }}>
            {error}
          </div>
        )}
        <UploadResult
          result={uploadResult}
          onDismiss={() => setUploadResult(null)}
        />
      </div>

      {/* ── Process pending ───────────────────────────────── */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '16px',
        }}>
          <div style={{ flex: 1 }}>
            <h2>Process Pending Records</h2>
            <p style={{
              fontSize: '13px',
              color: 'var(--text-muted)',
              marginTop: '6px',
            }}>
              Converts validated activity records into emission
              figures. Run after every upload.
            </p>
            <PendingStatus pending={pending} />
          </div>

          <button
            className={`btn ${
              !calculating &&
              pending &&
              !pending.is_up_to_date
                ? 'btn-primary'
                : ''
            }`}
            style={{ minWidth: '180px', marginTop: '4px' }}
            onClick={runCalculations}
            disabled={
              calculating ||
              !pending ||
              pending.is_up_to_date
            }
          >
            {calculating
              ? `Processing... ${elapsed}s`
              : pending?.is_up_to_date
                ? 'Up to date'
                : 'Process Pending Records'}
          </button>
        </div>

        {/* Calculation result */}
        {calcResult && (
          <div style={{
            marginTop: '20px',
            padding: '14px 16px',
            background: 'var(--bg-elevated)',
            borderRadius: '6px',
          }}>
            {calcResult.error ? (
              <div style={{
                fontSize: '13px',
                color: 'var(--status-bad)',
              }}>
                {calcResult.error}
              </div>
            ) : (
              <div style={{
                display: 'flex',
                gap: '28px',
                flexWrap: 'wrap',
                alignItems: 'center',
              }}>
                {[
                  {
                    label: 'Calculated',
                    value: calcResult.success,
                  },
                  {
                    label: 'Failed',
                    value: calcResult.failed,
                  },
                  {
                    label: 'Total',
                    value: calcResult.total,
                  },
                ].map((stat) => (
                  <div key={stat.label}>
                    <div style={{
                      fontSize: '11px',
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      color: 'var(--text-muted)',
                      marginBottom: '2px',
                    }}>
                      {stat.label}
                    </div>
                    <div style={{
                      fontSize: '18px',
                      fontWeight: '700',
                      color: 'var(--text-primary)',
                    }}>
                      {stat.value}
                    </div>
                  </div>
                ))}

                {calcResult.failed === 0 && (
                  <div style={{
                    fontSize: '12px',
                    color: 'var(--text-secondary)',
                    marginLeft: 'auto',
                  }}>
                    ✓ All records processed successfully
                  </div>
                )}

                {calcResult.errors &&
                  calcResult.errors.length > 0 && (
                  <div style={{
                    width: '100%',
                    marginTop: '8px',
                    fontSize: '12px',
                    color: 'var(--text-muted)',
                  }}>
                    {calcResult.errors.slice(0, 5).map((e, i) => (
                      <div key={i} style={{ marginBottom: '2px' }}>
                        · {e}
                      </div>
                    ))}
                    {calcResult.errors.length > 5 && (
                      <div style={{ marginTop: '4px' }}>
                        + {calcResult.errors.length - 5} more
                        failed records
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Upload history ────────────────────────────────── */}
      <div className="card">
        <h2 style={{ marginBottom: '20px' }}>Upload History</h2>
        {lineage.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
            No uploads yet.
          </p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>File / Form</th>
                  <th>Uploaded By</th>
                  <th>Date</th>
                  <th style={{ textAlign: 'right' }}>Total</th>
                  <th style={{ textAlign: 'right' }}>Valid</th>
                  <th style={{ textAlign: 'right' }}>Quarantined</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {lineage.map((item) => (
                  <tr key={item.id}>
                    <td style={{
                      fontSize: '12px',
                      color: 'var(--text-secondary)',
                    }}>
                      {item.source.replace('_', ' ')}
                    </td>
                    <td style={{
                      color: 'var(--text-primary)',
                      fontWeight: '500',
                      maxWidth: '200px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      {item.filename || item.odk_form_id || '—'}
                    </td>
                    <td style={{ color: 'var(--text-muted)' }}>
                      {item.uploaded_by || '—'}
                    </td>
                    <td style={{
                      color: 'var(--text-muted)',
                      fontSize: '12px',
                      whiteSpace: 'nowrap',
                    }}>
                      {new Date(item.uploaded_at).toLocaleDateString(
                        'en-GB', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric',
                        }
                      )}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      {item.record_count}
                    </td>
                    <td style={{
                      textAlign: 'right',
                      color: 'var(--text-secondary)',
                    }}>
                      {item.valid_count}
                    </td>
                    <td style={{
                      textAlign: 'right',
                      color: item.quarantine_count > 0
                        ? 'var(--status-warn)'
                        : 'var(--text-muted)',
                    }}>
                      {item.quarantine_count}
                    </td>
                    <td style={{
                      color: 'var(--text-muted)',
                      fontSize: '12px',
                      maxWidth: '200px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      {item.notes || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}