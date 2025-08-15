// Shared common types for Rainmaker

export type EventType = 
  | 'wedding' 
  | 'corporate_event' 
  | 'birthday' 
  | 'anniversary' 
  | 'graduation' 
  | 'other';

export interface EventRequirements {
  id: number;
  prospect_id: number;
  event_type: EventType;
  event_date?: string;
  guest_count?: number;
  budget_min?: number;
  budget_max?: number;
  location_preference?: string;
  venue_type?: string;
  special_requirements?: string;
  style_preferences?: string;
  dietary_restrictions?: string;
  accessibility_needs?: string;
  created_at: string;
  updated_at: string;
}

export interface AgentActivity {
  id: number;
  agent_name: string;
  activity_type: string;
  prospect_id?: number;
  description: string;
  input_data?: Record<string, any>;
  output_data?: Record<string, any>;
  status: 'started' | 'completed' | 'failed' | 'cancelled';
  error_message?: string;
  duration_seconds?: number;
  created_at: string;
  completed_at?: string;
}

export interface WorkflowState {
  workflow_id: string;
  prospect_id: number;
  current_stage: string;
  completed_stages: string[];
  progress_percentage: number;
  errors: Array<{
    agent: string;
    type: string;
    details: Record<string, any>;
    timestamp: string;
  }>;
  human_intervention_needed: boolean;
  workflow_started_at: string;
  last_updated_at: string;
}

export interface DashboardMetrics {
  total_prospects: number;
  prospects_by_status: Record<string, number>;
  campaigns_sent_today: number;
  response_rate: number;
  conversion_rate: number;
  active_workflows: number;
  recent_activities: AgentActivity[];
}

export interface User {
  id: number;
  email: string;
  name: string;
  role: 'admin' | 'sales_rep' | 'manager';
  created_at: string;
  last_login?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}