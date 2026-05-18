import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from '../api/client'
import type { AppSettings } from '../types'

export default function Settings() {
  const qc = useQueryClient()
  const [entry, setEntry] = useState('09:00')
  const [exit, setExit] = useState('18:00')
  const [grace, setGrace] = useState(5)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  const { data, isLoading } = useQuery<AppSettings>({
    queryKey: ['app-settings'],
    queryFn: () => client.get('/api/v1/settings').then((r) => r.data),
  })

  // Sincronizar form con los datos cargados (solo la primera vez para no
  // pisar lo que el usuario está editando).
  const [hydrated, setHydrated] = useState(false)
  useEffect(() => {
    if (data && !hydrated) {
      setEntry(data.expected_entry_time)
      setExit(data.expected_exit_time)
      setGrace(data.grace_minutes)
      setHydrated(true)
    }
  }, [data, hydrated])

  const mutation = useMutation({
    mutationFn: (body: Partial<AppSettings>) =>
      client.patch<AppSettings>('/api/v1/settings', body).then((r) => r.data),
    onSuccess: (updated) => {
      qc.setQueryData(['app-settings'], updated)
      qc.invalidateQueries({ queryKey: ['late-arrivals'] })
      setSaved(true)
      setError('')
      window.setTimeout(() => setSaved(false), 2500)
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'No se pudo guardar')
    },
  })

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    mutation.mutate({
      expected_entry_time: entry,
      expected_exit_time: exit,
      grace_minutes: grace,
    })
  }

  return (
    <div>
      <h1 className="page-title"><span className="accent" />Configuración</h1>

      <div className="card" style={{ maxWidth: 640 }}>
        <h2 className="section-title">Horario laboral</h2>
        <p className="helper-text" style={{ marginTop: 0, marginBottom: '1.25rem' }}>
          Define el horario esperado del personal. El informe de retrasos usa la <strong>hora de entrada</strong>{' '}
          + la <strong>tolerancia</strong> para detectar quién llega tarde.
        </p>

        {isLoading ? (
          <p className="empty">Cargando configuración…</p>
        ) : (
          <form onSubmit={onSubmit}>
            {error && <div className="error-msg">{error}</div>}
            {saved && <div className="success-msg">✓ Configuración guardada</div>}

            <div className="form-row">
              <div className="form-group">
                <label>Hora de entrada</label>
                <input
                  type="time"
                  value={entry}
                  onChange={(e) => setEntry(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>Hora de salida</label>
                <input
                  type="time"
                  value={exit}
                  onChange={(e) => setExit(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>Tolerancia (min)</label>
                <input
                  type="number"
                  min={0}
                  max={240}
                  value={grace}
                  onChange={(e) =>
                    setGrace(Math.max(0, Math.min(240, parseInt(e.target.value || '0', 10))))
                  }
                  style={{ width: 110 }}
                  required
                />
              </div>
            </div>

            <p className="helper-text" style={{ marginBottom: '1.25rem' }}>
              Ejemplo: si entrada = <strong>09:00</strong> y tolerancia = <strong>5</strong>,{' '}
              cualquier primera entrada después de las <strong>09:05</strong> se marca como
              retraso (los minutos se cuentan desde las 09:00, no desde las 09:05).
            </p>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={mutation.isPending}
            >
              {mutation.isPending ? 'Guardando…' : 'Guardar cambios'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
