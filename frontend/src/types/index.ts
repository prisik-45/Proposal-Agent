export interface ProposalResponse {
  success: boolean
  message: string
  drive_link?: string
  extracted_params?: ExtractedParams
  error?: string
}

export interface ExtractedParams {
  client_business_name: string
  client_requirements: string
  timeline_days: number
  price_min: string
  price_max: string
  includes_text: string
  scope_of_work_max_words?: number
  project_objective_max_words?: number
  technology_stack_max_words?: number
  additional_notes_max_words?: number
}

export interface ProposalRequest {
  user_input: string
}
