import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import client from '../api/client'
import type { AuditEntry } from '../types'

export default function Audit() {
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')

  const params = {
    ...(fromDate && { from: new Date(fromDate).toISOString() }),
    ...(toDate && { to: new Date(toDate + 'T23:59:59').toISOString() }),
  }

  const { data, isLoading } = useQuery<AuditEntry[]>({
    queryKey: ['audit', params],
    queryFn: () => client.get('/api/v1/audit', { params }).then((r) => r.data),
  })

  const opLabel: Record<string, string> = {
    'worker.create': 'Crear trabajador',
    'worker.update': 'Actualizar trabajador',
    'worker.deactivate': 'Desactivar trabajador',
    'worker.assign_token': 'Asignar token NFC',
  }

  return (
    <div>
      <h1 className="page-title">Log de auditoría</h1>

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
          {(fromDate || toDate) && (
            <button className="btn btn-outline" style={{ color: '#334155', borderColor: '#cbd5e1' }}
              onClick={() => { setFromDate(''); setToDate('') }}>
              Limpiar
            </button>
          )}
        </div>
      </div>

      <div className="card">
        {isLoading ? (
          <p className="empty">Cargando…</p>
        ) : !data?.length ? (
          <p className="empty">No hay entradas en el log.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Operación</th>
                  <th>Entidad</th>
                  <th>Detalles</th>
                  <th>Fecha y hora</th>
                </tr>
              </thead>
              <tbody>
                {data.map((e) => (
                  <tr key={e.id}>
                    <td><span className="badge badge-blue">{opLabel[e.operation] ?? e.operation}</span></td>
                    <td>{e.entity_type}</td>
                    <td style={{ fontSize: '.8rem', color: '#64748b', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {e.details ? JSON.stringify(e.details) : '—'}
                    </td>
                    <td>{new Date(e.performed_at).toLocaleString('es-ES', { timeZoneName: 'short' })}</td>
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
