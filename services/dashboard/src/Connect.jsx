import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getConfig, setConfig } from './api'

const styles = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  card: {
    background: '#fff',
    borderRadius: 12,
    boxShadow: '0 2px 12px rgba(0,0,0,.08)',
    padding: 32,
    width: '100%',
    maxWidth: 420,
  },
  title: { margin: '0 0 8px', fontSize: 24, fontWeight: 600 },
  subtitle: { margin: '0 0 24px', color: '#666', fontSize: 14 },
  label: { display: 'block', marginBottom: 6, fontSize: 13, fontWeight: 500 },
  input: {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #ddd',
    borderRadius: 8,
    fontSize: 14,
    marginBottom: 16,
  },
  button: {
    width: '100%',
    padding: 12,
    background: '#0d6efd',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    fontSize: 15,
    fontWeight: 500,
    cursor: 'pointer',
  },
  error: { color: '#c00', fontSize: 13, marginTop: 8 },
}

export default function Connect() {
  const navigate = useNavigate()
  const [apiUrl, setApiUrl] = useState('http://localhost:8001')
  const [projectId, setProjectId] = useState('default')
  const [error, setError] = useState('')

  useEffect(() => {
    const c = getConfig()
    if (c) {
      setApiUrl(c.apiUrl || 'http://localhost:8001')
      setProjectId(c.projectId || 'default')
    }
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    const url = apiUrl.replace(/\/$/, '')
    try {
      const r = await fetch(`${url}/health`)
      if (!r.ok) throw new Error('Query API not reachable')
      setConfig({ apiUrl: url, projectId })
      navigate('/dashboard')
    } catch (err) {
      setError(err.message || 'Could not connect. Is the Query API running on that URL?')
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.title}>Connect</h1>
        <p style={styles.subtitle}>Point to your Analytics Query API to view trends and funnels.</p>
        <form onSubmit={handleSubmit}>
          <label style={styles.label}>Query API URL</label>
          <input
            style={styles.input}
            type="url"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            placeholder="http://localhost:8001"
          />
          <label style={styles.label}>Project ID</label>
          <input
            style={styles.input}
            type="text"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            placeholder="default"
          />
          <button type="submit" style={styles.button}>Connect & go to Dashboard</button>
          {error && <p style={styles.error}>{error}</p>}
        </form>
      </div>
    </div>
  )
}
