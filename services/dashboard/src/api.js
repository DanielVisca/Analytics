const STORAGE_KEY = 'analytics_dashboard_config'

export function getConfig() {
  try {
    const s = localStorage.getItem(STORAGE_KEY)
    if (!s) return null
    return JSON.parse(s)
  } catch {
    return null
  }
}

export function setConfig({ apiUrl, projectId }) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    apiUrl: apiUrl || 'http://localhost:8001',
    projectId: projectId || 'default',
  }))
}

export async function fetchTrends(apiUrl, projectId, event, dateFrom, dateTo, interval = 'day') {
  const params = new URLSearchParams({
    project_id: projectId,
    event,
    date_from: dateFrom,
    date_to: dateTo,
    interval,
  })
  const r = await fetch(`${apiUrl.replace(/\/$/, '')}/api/trends?${params}`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function fetchFunnel(apiUrl, projectId, steps, dateFrom, dateTo) {
  const r = await fetch(`${apiUrl.replace(/\/$/, '')}/api/funnels`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: projectId,
      steps,
      date_from: dateFrom,
      date_to: dateTo,
    }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function fetchDashboards(apiUrl, projectId) {
  const r = await fetch(`${apiUrl.replace(/\/$/, '')}/api/dashboards?project_id=${encodeURIComponent(projectId)}`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function fetchDashboardWithResults(apiUrl, projectId, dashboardId) {
  const r = await fetch(`${apiUrl.replace(/\/$/, '')}/api/dashboards/${dashboardId}?project_id=${encodeURIComponent(projectId)}&with_results=true`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}
