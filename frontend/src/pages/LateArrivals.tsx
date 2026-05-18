import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import client from '../api/client'
import type { LateArrivalsReport, Worker } from '../types'

// ── Helpers ───────────────────────────────────────────────────────────────

/** Devuelve YYYY-MM-DD para la fecha local del navegador (no UTC) — el
 *  backend espera la fecha en TZ local y la convierte internamente. */
function toLocalDateStr(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function defaultFrom(): string {
  const d = new Date()
  d.setDate(d.getDate() - 6) // últimos 7 días incluido hoy
  return toLocalDateStr(d)
}

function defaultTo(): string {
  return toLocalDateStr(new Date())
}

/** Formatea minutos como "1h 23m" (>=60) o "23m" */
function fmtMinutes(min: number): string {
  if (min < 60) return `${min}m`
  const h = Math.floor(min / 60)
  const m = min % 60
  return m === 0 ? `${h}h` : `${h}h ${m}m`
}

/** YYYY-MM-DD → dd/mm/yyyy con día de la semana en español */
function fmtDate(iso: string): string {
  // Construir el Date a las 12:00 evita que el navegador retroceda un día por TZ.
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
  // UTF-8 BOM para que Excel respete acentos
  const blob = new Blob(['﻿' + rows.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `retrasos_${report.expected_time.replace(':', '')}_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// ──────────────────────────────────────────────────────────────────────────

export default function LateArrivals() {
  const [fromDate, setFromDate] = useState(defaultFrom())
  const [toDate, setToDate] = useState(defaultTo())
  const [expectedTime, setExpectedTime] = useState('09:00')
  const [graceMinutes, setGraceMinutes] = useState(5)
  const [workerId, setWorkerId] = useState('')

  const params = useMemo(
    () => ({
      from: fromDate,
      to: toDate,
      expected_time: expectedTime,
      grace_minutes: graceMinutes,
      ...(workerId && { worker_id: workerId }),
    }),
    [fromDate, toDate, expectedTime, graceMinutes, workerId],
  )

  const { data: workers } = useQuery<Worker[]>({
    queryKey: ['workers'],
    queryFn: () => client.get('/api/v1/workers').then((r) => r.data),
  })

  const { data, isLoading, isError, refetch } = useQuery<LateArrivalsReport>({
    queryKey: ['late-arrivals', params],
    queryFn: () => client.get('/api/v1/reports/late-arrivals', { params }).then((r) => r.data),
    refetchInterval: 30000, // refresca cada 30s sin abusar
  })

  // % de trabajadores afectados — útil para que el dueño tenga contexto rápido
  const affectedPct = workers && data
    ? Math.round((data.summary.workers_affected / Math.max(1, workers.length)) * 100)
    : 0

  return (
    <div>
      <h1 className="page-title">⏰ Retrasos</h1>

      {/* ── Filtros ───────────────────────────────────────────────────── */}
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
            <label>Hora esperada</label>
            <input
              type="time"
              value={expectedTime}
              onChange={(e) => setExpectedTime(e.target.value || '09:00')}
            />
          </div>
          <div className="form-group">
            <label>Tolerancia (min)</label>
            <input
              type="number"
              min={0}
              max={240}
              value={graceMinutes}
              onChange={(e) => setGraceMinutes(Math.max(0, Math.min(240, parseInt(e.target.value || '0', 10))))}
              style={{ width: '90px' }}
            />
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
          <button
            className="btn btn-success"
            disabled={!data || data.items.length === 0}
            onClick={() => data && downloadCsv(data)}
          >
            ⬇ Exportar CSV
          </button>
        </div>
        <p style={{ fontSize: '.78rem', color: '#64748b', marginTop: '.5rem', marginBottom: 0 }}>
          Un retraso se cuenta cuando la primera <strong>entrada</strong> del día supera la hora esperada
          + tolerancia. Los minutos mostrados son contra la hora esperada (no contra la tolerancia).
        </p>
      </div>

      {/* ── Tarjetas resumen ──────────────────────────────────────────── */}
      {data && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{data.summary.total_late_events}</div>
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
                <span style={{ fontSize: '1rem', color: '#94a3b8', marginLeft: '.4rem' }}>
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

      {/* ── Estado de carga / error ──────────────────────────────────── */}
      {isLoading && (
        <div className="card"><p className="empty">Cargando informe…</p></div>
      )}
      {isError && (
        <div className="card">
          <p className="empty">
            Error al cargar el informe.{' '}
            <button className="btn btn-sm btn-outline" style={{ color: '#334155', borderColor: '#cbd5e1' }} onClick={() => refetch()}>
              Reintentar
            </button>
          </p>
        </div>
      )}

      {/* ── Resumen por trabajador ───────────────────────────────────── */}
      {data && data.by_worker.length > 0 && (
        <div className="card" style={{ marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '1.05rem', marginTop: 0, marginBottom: '1rem', color: '#0f172a' }}>
            Ranking por trabajador
          </h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Trabajador</th>
                  <th>ID empleado</th>
                  <th>Retrasos</th>
                  <th>Tiempo acumulado</th>
                  <th>Promedio</th>
                </tr>
              </thead>
              <tbody>
                {data.by_worker.map((w) => (
                  <tr key={w.worker_id}>
                    <td>{w.worker_name}</td>
                    <td><span className="badge badge-gray">{w.employee_id}</span></td>
                    <td>{w.late_count}</td>
                    <td>
                      <span className="badge badge-red">{fmtMinutes(w.total_late_minutes)}</span>
                    </td>
                    <td>{fmtMinutes(Math.round(w.total_late_minutes / w.late_count))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Detalle por evento ───────────────────────────────────────── */}
      <div className="card">
        <h2 style={{ fontSize: '1.05rem', marginTop: 0, marginBottom: '1rem', color: '#0f172a' }}>
          Detalle de retrasos
        </h2>
        {data && data.items.length === 0 ? (
          <p className="empty">
            🎉 Ningún retraso en el rango seleccionado.
          </p>
        ) : data ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Trabajador</th>
                  <th>ID empleado</th>
                  <th>Primera entrada</th>
                  <th>Retraso</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((it) => (
                  <tr key={`${it.date}-${it.worker_id}`}>
                    <td>{fmtDate(it.date)}</td>
                    <td>{it.worker_name}</td>
                    <td><span className="badge badge-gray">{it.employee_id}</span></td>
                    <td style={{ fontFamily: 'monospace' }}>{it.local_time.slice(0, 5)}</td>
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
