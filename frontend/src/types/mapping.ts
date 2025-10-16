export interface Candidate {
  model: string
  field: string
  confidence: number
  method: string
  rationale: string
}

export interface Suggestion {
  id: number
  mapping_id: number
  candidates: Candidate[]
}

export interface SelectionOption {
  value: string
  label: string
}

export interface CustomFieldDefinition {
  technical_name: string
  field_label: string
  field_type: string
  target_model?: string
  required: boolean
  size?: number
  help_text?: string
  selection_options?: SelectionOption[]
  related_model?: string
}

export interface Transform {
  id: number
  mapping_id: number
  order: number
  fn: string
  params?: Record<string, any> | null
}

export interface Mapping {
  id: number
  dataset_id: number
  sheet_id: number
  header_name: string
  target_model: string | null
  target_field: string | null
  confidence: number | null
  status: 'pending' | 'confirmed' | 'ignored' | 'create_field'
  chosen: boolean
  rationale: string | null
  suggestions: Suggestion[]
  transforms?: Transform[]
  custom_field_definition?: CustomFieldDefinition
  lambda_function?: string
}

export interface FieldTypeSuggestion {
  field_type: string
  suggested_size?: number
  selection_options?: Array<{ value: string; label: string }>
  required: boolean
  rationale: string
}

export interface ColumnProfile {
  id: number
  name: string
  dtype_guess: string
  null_pct: number
  distinct_pct: number
  patterns: Record<string, number>
  sample_values: string[]
}

export interface Dataset {
  id: number
  name: string
  source_file_id: number
  created_at: string
  sheets: Sheet[]
}

export interface Sheet {
  id: number
  dataset_id: number
  name: string
  n_rows: number
  n_cols: number
}
