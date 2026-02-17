import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getConfig, fetchTrends, fetchFunnel } from './api'

const styles = {
  layout: { display: 'flex', flexDirection: 'column', minHeight: '100vh' },
  header: {
    background: '#fff',
    borderBottom: '1px solid #eee',
    padding: '12px 24px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 16,
  },
  headerTitle: { margin: 0, fontSize: 18, fontWeight: 600 },
  headerMeta: { fontSize: 13, color: '#666' },
  disconnect: {
    padding: '6px 12px',
    background: 'transparent',
    border: '1px solid #ddd',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 13,
  },
  main: { flex: 1, padding: 24, maxWidth: 960, margin: '0 auto', width: '100%' },
  section: {
    background: '#fff',
    borderRadius: 12,
    boxShadow: '0 2px 8px rgba(0,0,0,.06)',
    padding: 24,
    marginBottom: 24,
  },
  sectionTitle: { margin: '0 0 16px', fontSize: 16, fontWeight: 600 },
  row: { display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 },
  input: {
    padding: '8px 12px',
    border: '1px solid #ddd',
    borderRadius: 8,
    fontSize: 14,
  },
  button: {
    padding: '8px 16px',
    background: '#0d6efd',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    fontSize: 14,
    cursor: 'pointer',
  },
  chart: {
    minHeight: 120,
    display: 'flex',
    alignItems: 'flex-end',
    gap: 4,
    marginTop: 16,
  },
  bar: { flex: 1, background: '#0d6efd', borderRadius: 4, minHeight: 4 },
  label: { fontSize: 11, color: '#666', marginTop: 4 },
  steps: { listStyle: 'none', padding: 0, margin: 0 },
  stepItem: {
    padding: '10px 12px',
    borderBottom: '1px solid #eee',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  error: { color: '#c00', fontSize: 13 },
  loading: { color: '#666', fontSize: 13 },
}

function formatDate(d) {
  return d.toISOString().slice(0, 10)
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [config, setConfig] = useState(null)
  const [trendData, setTrendData] = useState(null)
  const [funnelData, setFunnelData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [eventName, setEventName] = useState('$pageview')
  const [dateFrom, setDateFrom] = useState(() => formatDate(new Date(Date.now() - 7 * 24 * 3600 * 1000)))
  const [dateTo, setDateTo] = useState(() => formatDate(new Date()))
  const [funnelSteps, setFunnelSteps] = useState('$pageview, feature_click, signup_click')

  useEffect(() => {
    const c = getConfig()
    if (!c) {
      navigate('/')
      return
    }
    setConfig(c)
  }, [navigate])

  const loadTrends = async () => {
    if (!config) return
    setLoading(true)
    setError('')
    try {
      const data = await fetchTrends(config.apiUrl, config.projectId, eventName, dateFrom, dateTo, 'day')
      setTrendData(data)
    } catch (e) {
      setError(e.message)
      setTrendData(null)
    } finally {
      setLoading(false)
    }
  }

  const loadFunnel = async () => {
    if (!config) return
    setLoading(true)
    setError('')
    try {
      const steps = funnelSteps.split(',').map((s) => s.trim()).filter(Boolean)
      if (steps.length < 2) {
        setError('Enter at least 2 steps, comma-separated')
        setLoading(false)
        return
      }
      const data = await fetchFunnel(config.apiUrl, config.projectId, steps, dateFrom, dateTo)
      setFunnelData(data)
    } catch (e) {
      setError(e.message)
      setFunnelData(null)
    } finally {
      setLoading(false)
    }
  }

  const disconnect = () => {
    localStorage.removeItem('analytics_dashboard_config')
    navigate('/')
  }

  if (!config) return null

  const maxTrend = trendData?.series?.length ? Math.max(...trendData.series) : 1

  return (
    <div style={styles.layout}>
      <header style={styles.header}>
        <div>
          <h1 style={styles.headerTitle}>Analytics Dashboard</h1>
          <span style={styles.headerMeta}>
            {config.apiUrl} · project: {config.projectId}
          </span>
        </div>
        <button type="button" style={styles.disconnect} onClick={disconnect}>
          Disconnect
        </button>
      </header>

      <main style={styles.main}>
        {error && <p style={styles.error}>{error}</p>}
        {loading && <p style={styles.loading}>Loading…</p>}

        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>Trends</h2>
          <div style={styles.row}>
            <input
              style={styles.input}
              value={eventName}
              onChange={(e) => setEventName(e.target.value)}
              placeholder="Event name (e.g. $pageview)"
            />
            <input
              style={styles.input}
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
            <input
              style={styles.input}
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
            <button type="button" style={styles.button} onClick={loadTrends}>
              Load
            </button>
          </div>
          {trendData && (
            <div>
              <div style={styles.chart}>
                {trendData.series.map((v, i) => (
                  <div
                    key={i}
                    style={{
                      ...styles.bar,
                      height: maxTrend ? `${(v / maxTrend) * 100}%` : 0,
                    }}
                    title={`${trendData.labels?.[i] ?? i}: ${v}`}
                  />
                ))}
              </div>
              <p style={styles.label}>
                {trendData.labels?.length ? `${trendData.labels[0]} … ${trendData.labels[trendData.labels.length - 1]}` : ''}
                {' · '}Total: {trendData.series?.reduce((a, b) => a + b, 0) ?? 0} events
              </p>
            </div>
          )}
        </section>

        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>Funnel</h2>
          <div style={styles.row}>
            <input
              style={{ ...styles.input, minWidth: 280 }}
              value={funnelSteps}
              onChange={(e) => setFunnelSteps(e.target.value)}
              placeholder="Steps: event1, event2, event3"
            />
            <input
              style={styles.input}
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
            <input
              style={styles.input}
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
            <button type="button" style={styles.button} onClick={loadFunnel}>
              Load
            </button>
          </div>
          {funnelData?.steps?.length > 0 && (
            <ul style={styles.steps}>
              {funnelData.steps.map((s, i) => (
                <li key={i} style={styles.stepItem}>
                  <span>Step {s.step}: {s.event}</span>
                  <strong>{s.count}</strong>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  )
}
