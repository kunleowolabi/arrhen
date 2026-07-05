/**
 * Axios client — configured to talk to the FastAPI backend.
 * Attaches Supabase JWT token to every request via interceptor.
 */

import axios from 'axios'
import { supabase } from '../lib/supabase'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const client = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

// Attach auth token to every request
client.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession()
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`
  }
  return config
})

// Response interceptor — centralised error handling
client.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.message ||
      'An unexpected error occurred'
    return Promise.reject(new Error(message))
  }
)

export default client

// ── API functions ──────────────────────────────────────────────────────────

// Organisations
export const getOrganisations = () => client.get('/organisations')
export const getOrganisation = (id) => client.get(`/organisations/${id}`)

// Dashboard
export const getDashboardOverview = (orgId, year) =>
  client.get('/dashboard/overview', { params: { organisation_id: orgId, period_year: year } })

export const getScopeBreakdown = (orgId, year) =>
  client.get('/dashboard/scope-breakdown', { params: { organisation_id: orgId, period_year: year } })

export const getSiteBreakdown = (orgId, year) =>
  client.get('/dashboard/sites', { params: { organisation_id: orgId, period_year: year } })

export const getMateriality = (orgId, year) =>
  client.get('/dashboard/materiality', { params: { organisation_id: orgId, period_year: year } })

export const getTrends = (orgId) =>
  client.get('/dashboard/trends', { params: { organisation_id: orgId } })

export const getScope2Summary = (orgId, year) =>
  client.get('/dashboard/scope2-summary', { params: { organisation_id: orgId, period_year: year } })

// Activity records
export const getActivityRecords = (params) =>
  client.get('/activity', { params })

export const getLineage = () =>
  client.get('/activity/lineage')

export const uploadCSV = (orgId, file, uploadedBy) => {
  const formData = new FormData()
  formData.append('file', file)
  return client.post(
    `/activity/upload/csv?organisation_id=${orgId}&uploaded_by=${uploadedBy}`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
}

// Emission factors
export const getFactors = (params) =>
  client.get('/factors', { params })

// Calculations
export const runCalculations = (payload) =>
  client.post('/calculations/run', payload)

// Geospatial
export const getSitesGeoJSON = (orgId) =>
  client.get('/geo/sites', { params: { organisation_id: orgId } })

export const getEmissionIntensity = (orgId, year) =>
  client.get('/geo/emission-intensity', { params: { organisation_id: orgId, period_year: year } })

// Reports
export const downloadJsonReport = (orgId, year) =>
  client.get('/reports/json', { params: { organisation_id: orgId, period_year: year } })

// Auth
export const getMe = () => client.get('/auth/me')
