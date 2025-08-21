/**
 * Campaign Planning Service
 * Integrates with Master Planning Agent API endpoints
 */

import { api, apiGet, apiPost } from '@/lib/api'

// =============================================================================
// TYPE DEFINITIONS
// =============================================================================

export interface PlanningConversationRequest {
  initial_context?: Record<string, any>
}

export interface PlanningMessageRequest {
  conversation_id: string
  message: string
}

export interface PlanningResponse {
  conversation_id: string
  current_phase: string
  completion_percentage: number
  assistant_response: string
  is_complete: boolean
  clarifications_needed: string[]
  suggested_responses: string[]
  campaign_plan?: Record<string, any>
}

export interface CampaignPlan {
  plan_id: string
  campaign_name: string
  objectives: Record<string, any>
  target_profile: Record<string, any>
  execution_strategy: Record<string, any>
  expected_timeline: string
  resource_requirements: Record<string, any>
  risk_factors: string[]
  success_predictions: Record<string, any>
  created_at: string
  plan_metadata: Record<string, any>
}

export interface CampaignPlanSummary {
  plan_id: string
  campaign_name: string
  campaign_type: string
  objectives: Record<string, any>
  target_profile: Record<string, any>
  status: string
  created_at: string
}

export interface ExecutionStatus {
  plan_id: string
  workflow_id: string
  status: 'ready' | 'executing' | 'completed' | 'failed' | 'paused_for_manual_login'
  progress_percentage: number
  current_phase: string
  metrics: {
    prospects_discovered: number
    outreach_sent: number
    meetings_scheduled: number
    proposals_generated: number
  }
  last_updated: string
  message?: string
  resume_endpoint?: string
  login_info?: {
    paused_for_login: boolean
    workflow_id: string
    site_name: string
    resume_endpoint: string
    message: string
  }
}

export interface PlanningTemplates {
  campaign_types: Array<{
    type: string
    name: string
    description: string
    best_for: string[]
    typical_duration: string
    expected_results: string
  }>
  target_profiles: Array<{
    name: string
    event_types: string[]
    budget_ranges: [number, number][]
    prospect_types: string[]
    key_indicators: string[]
  }>
  objective_examples: Array<{
    goal: string
    description: string
    typical_targets: Record<string, any>
  }>
}

export interface PlanningInsights {
  market_trends: string[]
  optimization_tips: string[]
  seasonal_recommendations: Array<{
    season: string
    focus: string
    suggested_campaign: string
    target_increase: string
  }>
  success_factors: string[]
}

// =============================================================================
// PLANNING CONVERSATION API
// =============================================================================

/**
 * Start a new campaign planning conversation
 */
export const startPlanningConversation = async (
  initialContext?: Record<string, any>
): Promise<PlanningResponse> => {
  return api.post('/api/v1/campaign-planning/planning/start', {
    initial_context: initialContext
  }, {
    timeout: 120000 // 2 minutes for planning operations
  }).then(response => response.data)
}

/**
 * Send a message in the planning conversation
 */
export const sendPlanningMessage = async (
  conversationId: string,
  message: string
): Promise<PlanningResponse> => {
  return api.post('/api/v1/campaign-planning/planning/message', {
    conversation_id: conversationId,
    message
  }, {
    timeout: 120000 // 2 minutes for planning operations
  }).then(response => response.data)
}

/**
 * Get current state of planning conversation
 */
export const getPlanningConversation = async (conversationId: string) => {
  return apiGet(`/api/v1/campaign-planning/planning/conversation/${conversationId}`)
}

// =============================================================================
// CAMPAIGN PLAN MANAGEMENT API
// =============================================================================

/**
 * Get all campaign plans for current user
 */
export const getCampaignPlans = async (): Promise<CampaignPlanSummary[]> => {
  return apiGet<CampaignPlanSummary[]>('/api/v1/campaign-planning/plans')
}

/**
 * Get detailed campaign plan
 */
export const getCampaignPlan = async (planId: string): Promise<CampaignPlan> => {
  return apiGet<CampaignPlan>(`/api/v1/campaign-planning/plans/${planId}`)
}

/**
 * Execute a campaign plan
 */
export const executeCampaignPlan = async (planId: string) => {
  return apiPost(`/api/v1/campaign-planning/plans/${planId}/execute`)
}

/**
 * Get campaign execution status
 */
export const getCampaignExecutionStatus = async (planId: string): Promise<ExecutionStatus> => {
  return apiGet<ExecutionStatus>(`/api/v1/campaign-planning/plans/${planId}/status`)
}

/**
 * Resume a paused workflow after manual login
 */
export const resumeWorkflow = async (workflowId: string): Promise<{ success: boolean; message: string }> => {
  return apiPost<{ success: boolean; message: string }>(`/api/v1/browser/resume/${workflowId}`, {})
}

// =============================================================================
// PLANNING ASSISTANCE API
// =============================================================================

/**
 * Get campaign planning templates and suggestions
 */
export const getPlanningTemplates = async (): Promise<PlanningTemplates> => {
  return apiGet<PlanningTemplates>('/api/v1/campaign-planning/planning/templates')
}

/**
 * Get intelligent insights and recommendations
 */
export const getPlanningInsights = async (): Promise<PlanningInsights> => {
  return apiGet<PlanningInsights>('/api/v1/campaign-planning/planning/insights')
}

// =============================================================================
// WEBSOCKET CONNECTION
// =============================================================================

/**
 * Create WebSocket connection for real-time planning updates
 */
export const createPlanningWebSocket = (
  conversationId: string,
  onMessage?: (data: any) => void,
  onError?: (error: Event) => void,
  onClose?: (event: CloseEvent) => void
): WebSocket => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = import.meta.env.VITE_API_URL?.replace(/^https?:\/\//, '') || 'localhost:8000'
  const wsUrl = `${protocol}//${host}/api/v1/campaign-planning/planning/ws/${conversationId}`

  const ws = new WebSocket(wsUrl)

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage?.(data)
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error)
    }
  }

  ws.onerror = onError || ((error) => {
    console.error('WebSocket error:', error)
  })

  ws.onclose = onClose || ((event) => {
    console.log('WebSocket connection closed:', event.code, event.reason)
  })

  return ws
}

/**
 * Create WebSocket connection for real-time workflow status updates
 */
export const createWorkflowStatusWebSocket = (
  onMessage?: (data: any) => void,
  onError?: (error: Event) => void,
  onClose?: (event: CloseEvent) => void
): WebSocket => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = import.meta.env.VITE_API_URL?.replace(/^https?:\/\//, '') || 'localhost:8000'
  const wsUrl = `${protocol}//${host}/api/v1/campaign-planning/workflow-status/ws`

  const ws = new WebSocket(wsUrl)

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage?.(data)
    } catch (error) {
      console.error('Failed to parse workflow status WebSocket message:', error)
    }
  }

  ws.onerror = onError || ((error) => {
    console.error('Workflow status WebSocket error:', error)
  })

  ws.onclose = onClose || ((event) => {
    console.log('Workflow status WebSocket connection closed:', event.code, event.reason)
  })

  return ws
}