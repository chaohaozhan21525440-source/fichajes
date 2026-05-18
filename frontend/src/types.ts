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

// ── Informe de retrasos (/api/v1/reports/late-arrivals) ──
export interface LateArrivalItem {
  date: string            // YYYY-MM-DD (fecha local)
  worker_id: string
  worker_name: string
  employee_id: string
  first_entry_at: string  // ISO UTC
  local_time: string      // HH:MM:SS local
  late_minutes: number
}

export interface LateArrivalWorkerSummary {
  worker_id: string
  worker_name: string
  employee_id: string
  late_count: number
  total_late_minutes: number
}

export interface LateArrivalSummary {
  total_late_events: number
  total_late_minutes: number
  workers_affected: number
}

export interface LateArrivalsReport {
  expected_time: string
  grace_minutes: number
  tz: string
  items: LateArrivalItem[]
  by_worker: LateArrivalWorkerSummary[]
  summary: LateArrivalSummary
}
