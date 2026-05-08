import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import client from '../api/client'
import type { CheckinsPage, Worker } from '../types'

const PAGE_SIZE = 20

export default function Checkins() {
  const [workerId, setWorkerId] = useState('')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [eventType, setEventType] = useState('')
  const [page, setPage] = useState(1)

  const params = {
    ...(workerId && { worker_id: workerId }),
    ...(fromDate && { from: new Date(fromDate).toISOString() }),
    ...(toDate && { to: new Date(toDate + 'T23:59:59').toISOString() }),
    ...(eventType && { event_type: eventType }),
    page,
    size: PAGE_SIZE,
  }

  const { data, isLoading } = useQuery<CheckinsPage>({
    queryKey: ['checkins', params],
    queryFn: () => client.get('/api/v1/checkins', { params }).then((r) => r.data),
    refetchInterval: 5000,
  })

  const { data: workers } = useQuery<Worker[]>({
    queryKey: ['workers'],
    queryFn: () => client.get('/api/v1/workers').then((r) => r.data),
  })

  const handleExport = async () => {
    const exportParams = { ...params }
    delete (exportParams as Record<string, unknown>).page
    delete (exportParams as Record<string, unknown>).size
    const resp = await client.get('/api/v1/export/checkins.csv', {
      params: exportParams,
      responseType: 'blob',
    })
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'fichajes.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1

  return (
    <div>
      <h1 className="page-title">Registros de fichaje</h1>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <div className="filters">
          <div className="form-group">
            <label>Trabajador</label>
            <select value={workerId} onChange={(e) => { setWorkerId(e.target.value); setPage(1) }}>
              <option value="">Todos</option>
              {workers?.map((w) => (
                <option key={w.id} value={w.id}>{w.full_name}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Desde</label>
            <input type="date" value={fromDate} onChange={(e) => { setFromDate(e.target.value); setPage(1) }} />
          </div>
          <div className="form-group">
            <label>Hasta</label>
            <input type="date" value={toDate} onChange={(e) => { setToDate(e.target.value); setPage(1) }} />
          </div>
          <div className="form-group">
            <label>Tipo</label>
            <select value={eventType} onChange={(e) => { setEventType(e.target.value); setPage(1) }}>
              <option value="">Todos</option>
              <option value="entrada">Entrada</option>
              <option value="salida">Salida</option>
            </select>
          </div>
          <button className="btn btn-success" onClick={handleExport}>⬇ Exportar CSV</button>
        </div>
      </div>

      <div className="card">
        {isLoading ? (
          <p className="empty">Cargando…</p>
        ) : !data?.items.length ? (
          <p className="empty">No hay registros con los filtros aplicados.</p>
        ) : (
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Trabajador</th>
                    <th>Tipo</th>
                    <th>Fecha y hora</th>
                    <th>Dispositivo</th>
                    <th>Origen</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((r) => (
                    <tr key={r.id}>
                      <td>{r.worker_name}</td>
                      <td>
                        <span className={`badge ${r.event_type === 'entrada' ? 'badge-green' : 'badge-red'}`}>
                          {r.event_type}
                        </span>
                      </td>
                      <td>{new Date(r.recorded_at).toLocaleString('es-ES', { timeZoneName: 'short' })}</td>
                      <td>{r.device_id}</td>
                      <td>
                        {r.synced_from_local
                          ? <span className="badge badge-gray">offline</span>
                          : <span className="badge badge-blue">online</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <span>Total: {data.total} registros</span>
              <button className="btn btn-sm btn-outline" style={{ color: '#334155', borderColor: '#cbd5e1' }} onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>
                ‹ Anterior
              </button>
              <span>Página {page} de {totalPages}</span>
              <button className="btn btn-sm btn-outline" style={{ color: '#334155', borderColor: '#cbd5e1' }} onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
                Siguiente ›
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
