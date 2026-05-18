import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import client from '../api/client'
import type { AppSettings, LateArrivalsReport, Worker } from '../types'

// ── Helpers ───────────────────────────────────────────────────────────────

/** YYYY-MM-DD en la zona horaria local del navegador (no UTC). El backend
 *  espera fecha local y la convierte internamente. */
function toLocalDateStr(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const todayStr = () => toLocalDateStr(new Date())

/** Minutos → "1h 23m" si >=60 si no "23m" */
function fmtMinutes(min: number): string {
  if (min < 60) return `${min}m`
  const h = Math.floor(min / 60)
  const m = min % 60
  return m === 0 ? `${h}h` : `${h}h ${m}m`
}

/** YYYY-MM-DD → "lun., 19/05/2026" (es-ES). Forzar T12:00:00 evita que la
 *  conversión UTC retroceda un día en TZ negativas / DST. */
function fmtDate(iso: string): string {
  const d = new Date(iso + 'T12:00:00')
  return d.toLocaleDateString('es-ES', { weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric' })
}

// ── CSV export (cliente; no toca backend) ─────────────────────────────────

function downloadCsv(report: LateArrivalsReport) {
  const rows: string[] = []
  rows.push(['Fecha', 'Trabajador', 'ID empleado', 'Hora primera entrada', 'Minutos tarde'].join(','))
  for (const it of report.items) {
    const cell = (s: string) => `"${s.replace(/"/g, '""')}"`
    rows.push([
      it.date,
      cell(it.worker_name),
      cell(it.employee_id),
      it.local_time,
      String(it.late_minutes),
    ].join(','))
  }
  const blob = new Blob(['﻿' + rows.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `retrasos_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// ──────────────────────────────────────────────────────────────────────────

export default function LateArrivals() {
  // Defaults: cliente pidió "empezar a contar desde hoy" → from = hoy, to = hoy.
  // Si quiere ver historia puede mover los date pickers a un rango anterior.
  const [fromDate, setFromDate] = useState(todayStr())
  const [toDate, setToDate] = useState(todayStr())
  const [workerId, setWorkerId] = useState('')

  // Overrides puntuales: si están vacíos, el backend usa los settings persistidos.
  // Inicialmente vacíos para que la primera carga use lo configurado por el cliente.
  const [overrideExpected, setOverrideExpected] = useState('')
  const [overrideGrace, setOverrideGrace] = useState<string>('')

  // Settings persistidos — para mostrar como "hora actual configurada".
  const { data: settings } = useQuery<AppSettings>({
    queryKey: ['app-settings'],
    queryFn: () => client.get('/api/v1/settings').then((r) => r.data),
  })

  const params = useMemo(
    () => ({
      from: fromDate,
      to: toDate,
      ...(overrideExpected && { expected_time: overrideExpected }),
      ...(overrideGrace !== '' && { grace_minutes: parseInt(overrideGrace, 10) }),
      ...(workerId && { worker_id: workerId }),
    }),
    [fromDate, toDate, overrideExpected, overrideGrace, workerId],
  )

  const { data: workers } = useQuery<Worker[]>({
    queryKey: ['workers'],
    queryFn: () => client.get('/api/v1/workers').then((r) => r.data),
  })

  const { data, isLoading, isError, refetch, isFetching } = useQuery<LateArrivalsReport>({
    queryKey: ['late-arrivals', params],
    queryFn: () => client.get('/api/v1/reports/late-arrivals', { params }).then((r) => r.data),
    refetchInterval: 30000,
  })

  // Reset overrides cuando cambian los settings persistidos —
  // así "Volver a la config global" funciona implícitamente al limpiar.
  useEffect(() => {
    if (!overrideExpected && !overrideGrace) return
    // no-op por ahora; los overrides solo se aplican mientras tengan valor
  }, [settings, overrideExpected, overrideGrace])

  const affectedPct = workers && data
    ? Math.round((data.summary.workers_affected / Math.max(1, workers.length)) * 100)
    : 0

  // Texto descriptivo del criterio efectivo aplicado
  const effectiveExpected = data?.expected_time ?? settings?.expected_entry_time ?? '09:00'
  const effectiveGrace = data?.grace_minutes ?? settings?.grace_minutes ?? 5

  return (
    <div>
      <h1 className="page-title"><span className="accent" />Retrasos</h1>

      {/* ── Banner criterio actual ─────────────────────────────────── */}
      <div
        className="card"
        style={{
          marginBottom: '1rem',
          display: 'flex',
          gap: '1rem',
          alignItems: 'center',
          flexWrap: 'wrap',
          background: 'linear-gradient(90deg, var(--brand-soft) 0%, #fff 70%)',
          borderColor: '#FECACA',
        }}
      >
        <div style={{ flex: 1, minWidth: 240 }}>
          <div style={{ fontSize: '.78rem', color: 'var(--ink-500)', fontWeight: 600, letterSpacing: '.04em', textTransform: 'uppercase' }}>
            Criterio aplicado
          </div>
          <div style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--ink-900)', marginTop: '.25rem' }}>
            Entrada esperada{' '}
            <span style={{ fontFamily: 'monospace', color: 'var(--brand-dark)' }}>{effectiveExpected}</span>
            {' '}· tolerancia{' '}
            <span style={{ fontFamily: 'monospace', color: 'var(--brand-dark)' }}>{effectiveGrace} min</span>
            {(overrideExpected || overrideGrace) && (
              <span className="badge badge-brand" style={{ marginLeft: '.5rem' }}>override</span>
            )}
          </div>
        </div>
        <Link to="/settings" className="btn btn-outline btn-sm">
          ⚙ Configurar horario
        </Link>
      </div>

      {/* ── Filtros ───────────────────────────────────────────────── */}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <div className="filters">
          <div className="form-group">
            <label>Desde</label>
            <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Hasta</label>
            <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Trabajador</label>
            <select value={workerId} onChange={(e) => setWorkerId(e.target.value)}>
              <option value="">Todos</option>
              {workers?.map((w) => (
                <option key={w.id} value={w.id}>{w.full_name}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Hora esperada (override)</label>
            <input
              type="time"
              value={overrideExpected}
              onChange={(e) => setOverrideExpected(e.target.value)}
              placeholder="Usar configuración"
            />
          </div>
          <div className="form-group">
            <label>Tolerancia (override)</label>
            <input
              type="number"
              min={0}
              max={240}
              value={overrideGrace}
              onChange={(e) => setOverrideGrace(e.target.value)}
              placeholder="—"
              style={{ width: 110 }}
            />
          </div>
          <button
            className="btn btn-success"
            disabled={!data || data.items.length === 0}
            onClick={() => data && downloadCsv(data)}
          >
            ⬇ Exportar CSV
          </button>
        </div>
        <p className="helper-text">
          Por defecto se aplica la configuración global. Usa los campos "override" para hacer una
          simulación puntual sin guardar.
        </p>
      </div>

      {/* ── Tarjetas resumen ──────────────────────────────────────── */}
      {data && (
        <div className="stats-grid">
          <div className="stat-card stat-card-accent">
            <div className="stat-value is-brand">{data.summary.total_late_events}</div>
            <div className="stat-label">Retrasos detectados</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{fmtMinutes(data.summary.total_late_minutes)}</div>
            <div className="stat-label">Tiempo total acumulado</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">
              {data.summary.workers_affected}
              {workers && (
                <span style={{ fontSize: '1rem', color: 'var(--ink-400)', marginLeft: '.4rem' }}>
                  / {workers.length}
                </span>
              )}
            </div>
            <div className="stat-label">
              Trabajadores afectados
              {workers && data.summary.workers_affected > 0 && ` (${affectedPct}%)`}
            </div>
          </div>
        </div>
      )}

      {/* ── Estado de carga / error ───────────────────────────────── */}
      {isLoading && (
        <div className="card"><p className="empty">Cargando informe…</p></div>
      )}
      {isError && (
        <div className="card">
          <p className="empty">
            Error al cargar el informe.{' '}
            <button className="btn btn-sm btn-outline" onClick={() => refetch()}>
              Reintentar
            </button>
          </p>
        </div>
      )}

      {/* ── Ranking por trabajador ────────────────────────────────── */}
      {data && data.by_worker.length > 0 && (
        <div className="card" style={{ marginBottom: '1rem' }}>
          <h2 className="section-title">Ranking por trabajador</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Trabajador</th>
                  <th>ID</th>
                  <th style={{ width: 100 }}>Retrasos</th>
                  <th style={{ width: 160 }}>Tiempo acumulado</th>
                  <th style={{ width: 130 }}>Promedio</th>
                </tr>
              </thead>
              <tbody>
                {data.by_worker.map((w) => (
                  <tr key={w.worker_id}>
                    <td style={{ fontWeight: 600 }}>{w.worker_name}</td>
                    <td><span className="badge badge-gray">{w.employee_id}</span></td>
                    <td style={{ fontVariantNumeric: 'tabular-nums' }}>{w.late_count}</td>
                    <td>
                      <span className="badge badge-red">{fmtMinutes(w.total_late_minutes)}</span>
                    </td>
                    <td style={{ fontVariantNumeric: 'tabular-nums', color: 'var(--ink-500)' }}>
                      {fmtMinutes(Math.round(w.total_late_minutes / w.late_count))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Detalle por evento ────────────────────────────────────── */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <h2 className="section-title" style={{ margin: 0 }}>Detalle de retrasos</h2>
          {isFetching && !isLoading && (
            <span style={{ fontSize: '.75rem', color: 'var(--ink-400)' }}>Actualizando…</span>
          )}
        </div>
        {data && data.items.length === 0 ? (
          <p className="empty">
            🎉 Ningún retraso en el rango seleccionado.
          </p>
        ) : data ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 180 }}>Fecha</th>
                  <th>Trabajador</th>
                  <th style={{ width: 110 }}>ID</th>
                  <th style={{ width: 140 }}>Primera entrada</th>
                  <th style={{ width: 140 }}>Retraso</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((it) => (
                  <tr key={`${it.date}-${it.worker_id}`}>
                    <td style={{ color: 'var(--ink-700)' }}>{fmtDate(it.date)}</td>
                    <td style={{ fontWeight: 600 }}>{it.worker_name}</td>
                    <td><span className="badge badge-gray">{it.employee_id}</span></td>
                    <td style={{ fontFamily: 'monospace', fontVariantNumeric: 'tabular-nums' }}>
                      {it.local_time.slice(0, 5)}
                    </td>
                    <td>
                      <span className="badge badge-red">+{fmtMinutes(it.late_minutes)}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </div>
  )
}
