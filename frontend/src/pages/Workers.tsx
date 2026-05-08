import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import client from '../api/client'
import type { Worker } from '../types'

interface WorkerForm { full_name: string; employee_id: string; nfc_uid: string }
const emptyForm: WorkerForm = { full_name: '', employee_id: '', nfc_uid: '' }

export default function Workers() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<WorkerForm>(emptyForm)
  const [formError, setFormError] = useState('')
  const [tokenTarget, setTokenTarget] = useState<Worker | null>(null)
  const [newToken, setNewToken] = useState('')
  const [tokenError, setTokenError] = useState('')
  const [confirmDeactivate, setConfirmDeactivate] = useState<Worker | null>(null)

  const { data: workers, isLoading } = useQuery<Worker[]>({
    queryKey: ['workers'],
    queryFn: () => client.get('/api/v1/workers').then((r) => r.data),
  })

  const createMutation = useMutation({
    mutationFn: (data: WorkerForm) => client.post('/api/v1/workers', data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['workers'] }); setShowForm(false); setForm(emptyForm); setFormError('') },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: { message?: string } } } }).response?.data?.detail?.message
      setFormError(msg ?? 'Error al crear el trabajador')
    },
  })

  const deactivateMutation = useMutation({
    mutationFn: (id: string) => client.patch(`/api/v1/workers/${id}/deactivate`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['workers'] }); setConfirmDeactivate(null) },
  })

  const tokenMutation = useMutation({
    mutationFn: ({ id, uid }: { id: string; uid: string }) =>
      client.post(`/api/v1/workers/${id}/nfc-tokens`, { nfc_uid: uid }),
    onSuccess: () => { setTokenTarget(null); setNewToken(''); setTokenError('') },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: { message?: string } } } }).response?.data?.detail?.message
      setTokenError(msg ?? 'Error al asignar token')
    },
  })

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 className="page-title" style={{ marginBottom: 0 }}>Trabajadores</h1>
        <button className="btn btn-primary" onClick={() => { setShowForm(true); setFormError('') }}>+ Nuevo trabajador</button>
      </div>

      <div className="card">
        {isLoading ? <p className="empty">Cargando…</p> : !workers?.length ? (
          <p className="empty">No hay trabajadores registrados.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>ID Empleado</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {workers.map((w) => (
                  <tr key={w.id}>
                    <td>{w.full_name}</td>
                    <td>{w.employee_id}</td>
                    <td>
                      <span className={`badge ${w.is_active ? 'badge-green' : 'badge-gray'}`}>
                        {w.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td style={{ display: 'flex', gap: '.5rem' }}>
                      {w.is_active && (
                        <>
                          <button className="btn btn-sm btn-primary" onClick={() => { setTokenTarget(w); setTokenError('') }}>
                            + Token NFC
                          </button>
                          <button className="btn btn-sm btn-danger" onClick={() => setConfirmDeactivate(w)}>
                            Desactivar
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal nuevo trabajador */}
      {showForm && (
        <div className="modal-bg" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Nuevo trabajador</h2>
            {formError && <div className="error-msg">{formError}</div>}
            {(['full_name', 'employee_id', 'nfc_uid'] as const).map((field) => (
              <div className="form-group" key={field}>
                <label>{field === 'full_name' ? 'Nombre completo' : field === 'employee_id' ? 'ID empleado' : 'UID token NFC'}</label>
                <input value={form[field]} onChange={(e) => setForm({ ...form, [field]: e.target.value })} />
              </div>
            ))}
            <div className="modal-actions">
              <button className="btn btn-outline" style={{ color: '#334155', borderColor: '#cbd5e1' }} onClick={() => setShowForm(false)}>Cancelar</button>
              <button className="btn btn-primary" onClick={() => createMutation.mutate(form)} disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Guardando…' : 'Crear'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal asignar token NFC */}
      {tokenTarget && (
        <div className="modal-bg" onClick={() => setTokenTarget(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Añadir token NFC — {tokenTarget.full_name}</h2>
            {tokenError && <div className="error-msg">{tokenError}</div>}
            <div className="form-group">
              <label>UID del nuevo token</label>
              <input value={newToken} onChange={(e) => setNewToken(e.target.value)} placeholder="04:XX:XX:XX:XX" />
            </div>
            <div className="modal-actions">
              <button className="btn btn-outline" style={{ color: '#334155', borderColor: '#cbd5e1' }} onClick={() => setTokenTarget(null)}>Cancelar</button>
              <button className="btn btn-primary" onClick={() => tokenMutation.mutate({ id: tokenTarget.id, uid: newToken })} disabled={tokenMutation.isPending}>
                {tokenMutation.isPending ? 'Asignando…' : 'Asignar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal confirmar desactivación */}
      {confirmDeactivate && (
        <div className="modal-bg" onClick={() => setConfirmDeactivate(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Confirmar desactivación</h2>
            <p style={{ color: '#475569', marginBottom: '1rem' }}>
              ¿Seguro que quieres desactivar a <strong>{confirmDeactivate.full_name}</strong>?
              Sus fichajes históricos se conservarán.
            </p>
            <div className="modal-actions">
              <button className="btn btn-outline" style={{ color: '#334155', borderColor: '#cbd5e1' }} onClick={() => setConfirmDeactivate(null)}>Cancelar</button>
              <button className="btn btn-danger" onClick={() => deactivateMutation.mutate(confirmDeactivate.id)} disabled={deactivateMutation.isPending}>
                {deactivateMutation.isPending ? 'Desactivando…' : 'Desactivar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
