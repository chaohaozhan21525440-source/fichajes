export interface Worker {
  id: string
  full_name: string
  employee_id: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CheckinRecord {
  id: string
  worker_id: string
  worker_name: string
  nfc_uid: string
  event_type: 'entrada' | 'salida'
  recorded_at: string
  device_id: string
  synced_from_local: boolean
}

export interface CheckinsPage {
  total: number
  page: number
  size: number
  items: CheckinRecord[]
}

export interface AuditEntry {
  id: string
  admin_id: string
  operation: string
  entity_type: string
  entity_id: string | null
  details: Record<string, unknown> | null
  performed_at: string
}
