import { useQuery } from '@tanstack/react-query'
import client from '../api/client'
import type { CheckinsPage, Worker } from '../types'

export default function Dashboard() {
  const { data: workers } = useQuery<Worker[]>({
    queryKey: ['workers'],
    queryFn: () => client.get('/api/v1/workers').then((r) => r.data),
    refetchInterval: 5000,
  })

  const { data: checkins } = useQuery<CheckinsPage>({
    queryKey: ['checkins-today'],
    queryFn: () => {
      const from = new Date()
      from.setHours(0, 0, 0, 0)
      return client
        .get('/api/v1/checkins', { params: { from: from.toISOString(), size: 1 } })
        .then((r) => r.data)
    },
    refetchInterval: 5000,
  })

  const active = workers?.filter((w) => w.is_active).length ?? '…'
  const total = workers?.length ?? '…'
  const today = checkins?.total ?? '…'

  return (
    <div>
      <h1 className="page-title">Panel de control</h1>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{active}</div>
          <div className="stat-label">Trabajadores activos</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{total}</div>
          <div className="stat-label">Total trabajadores</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{today}</div>
          <div className="stat-label">Fichajes hoy</div>
        </div>
      </div>
      <div className="card">
        <p style={{ color: '#64748b', fontSize: '.9rem' }}>
          Usa el menú lateral para gestionar trabajadores, consultar fichajes o revisar el log de auditoría.
        </p>
      </div>
    </div>
  )
}
