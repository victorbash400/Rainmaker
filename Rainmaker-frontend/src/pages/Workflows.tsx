import { useState, useEffect, useRef } from 'react'
import { Pause, RotateCcw, X, Clock, CheckCircle, AlertTriangle, Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { 
  getCampaignPlans, 
  getCampaignExecutionStatus,
  createWorkflowStatusWebSocket
} from '@/services/campaignPlanningService'
import BrowserViewer from '@/components/BrowserViewer'

// AI Thought Process Component
function AIThoughtProcess({ workflowId }: { workflowId: string }) {
  const [aiReasoning, setAiReasoning] = useState<string>('Analyzing page structure...')
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const connectToAI = () => {
      if (wsRef.current?.readyState === WebSocket.OPEN) return

      const wsUrl = `ws://localhost:8000/api/v1/browser-viewer/ws/${workflowId}`
      
      try {
        wsRef.current = new WebSocket(wsUrl)
        
        wsRef.current.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data)
            
            // Handle different message types
            if (message.type === 'browser_update' && message.data) {
              if (message.data.reasoning) {
                setAiReasoning(message.data.reasoning)
              }
            } else if (message.workflow_id && message.reasoning) {
              // Direct browser update with reasoning
              setAiReasoning(message.reasoning)
            }
          } catch (error) {
            console.error('Failed to parse AI reasoning update:', error)
          }
        }
        
        wsRef.current.onclose = () => {
          // Reconnect after 2 seconds
          setTimeout(connectToAI, 2000)
        }
        
      } catch (error) {
        console.error('Failed to connect to AI reasoning WebSocket:', error)
      }
    }

    connectToAI()
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [workflowId])

  return (
    <div className="space-y-2">
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">AI Thinking</div>
      <div className="text-sm text-black min-h-[3rem] transition-opacity duration-300 relative overflow-hidden">
        <div className="relative z-0">
          {aiReasoning}
        </div>
        {/* Shimmer effect - above the text */}
        <div className="absolute inset-0 pointer-events-none z-10">
          <div className="absolute inset-0 w-24 h-full shimmer-animation" 
               style={{
                 background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.1) 20%, rgba(255,255,255,0.8) 50%, rgba(255,255,255,0.1) 80%, transparent 100%)',
                 boxShadow: '0 0 10px rgba(255,255,255,0.3)'
               }}>
          </div>
        </div>
      </div>
    </div>
  )
}

interface WorkflowData {
  plan_id: string
  workflow_id: string
  campaign_name: string
  campaign_type: string
  status: 'ready' | 'executing' | 'completed' | 'failed'
  current_phase: string
  progress_percentage: number
  started_at: string
  stages: Array<{
    name: string
    status: 'complete' | 'active' | 'pending' | 'error'
    duration?: string
    error?: string
  }>
  metrics: {
    prospects_discovered: number
    outreach_sent: number
    meetings_scheduled: number
    proposals_generated: number
  }
}

export default function Workflows() {
  const [workflows, setWorkflows] = useState<WorkflowData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const navigate = useNavigate()
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    loadWorkflows()
    setupWebSocket()
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const setupWebSocket = () => {
    try {
      wsRef.current = createWorkflowStatusWebSocket(
        (data) => {
          console.log('Received workflow status update:', data)
          
          if (data.type === 'workflow_status_update') {
            // Update specific workflow status in real-time (reduced logging)
            setWorkflows(prev => prev.map(workflow => {
              if (workflow.plan_id === data.plan_id) {
                // Only log significant status changes
                if (workflow.status !== data.status || workflow.current_phase !== data.current_phase) {
                  console.log(`Workflow ${data.plan_id}: ${data.current_phase} (${data.status})`)
                }
                return {
                  ...workflow,
                  status: data.status,
                  current_phase: data.current_phase,
                  progress_percentage: data.progress_percentage,
                  metrics: data.metrics || workflow.metrics
                }
              }
              return workflow
            }))
          }
        },
        (error) => {
          console.error('Workflow status WebSocket error:', error)
          setIsConnected(false)
          // Reconnect after 5 seconds
          setTimeout(setupWebSocket, 5000)
        },
        (event) => {
          console.log('Workflow status WebSocket closed:', event.code, event.reason)
          setIsConnected(false)
          // Reconnect if not manually closed
          if (event.code !== 1000) {
            setTimeout(setupWebSocket, 5000)
          }
        }
      )
      
      wsRef.current.onopen = () => {
        console.log('Workflow status WebSocket connected')
        setIsConnected(true)
      }
      
    } catch (error) {
      console.error('Failed to setup workflow status WebSocket:', error)
      setIsConnected(false)
    }
  }

  const loadWorkflows = async () => {
    try {
      setIsLoading(true)
      const campaignPlans = await getCampaignPlans()
      
      // Convert campaign plans to workflow data
      const workflowData: WorkflowData[] = await Promise.all(
        campaignPlans
          .filter(plan => plan.status !== 'ready') // Only show executing/completed workflows
          .map(async (plan) => {
            try {
              const status = await getCampaignExecutionStatus(plan.plan_id)
              console.log(`Campaign ${plan.plan_id} status:`, status)
              
              // Generate stages based on execution status
              const stages = [
                {
                  name: 'hunting',
                  status: status.metrics.prospects_discovered > 0 ? 'complete' as const : 
                          (status.current_phase === 'discovery' || status.current_phase === 'hunting') ? 'active' as const : 'pending' as const,
                  duration: status.metrics.prospects_discovered > 0 ? '2m 15s' : undefined
                },
                {
                  name: 'enriching',
                  status: status.metrics.outreach_sent > 0 ? 'complete' as const :
                          status.current_phase === 'enriching' ? 'active' as const : 'pending' as const,
                  duration: status.metrics.outreach_sent > 0 ? '1m 45s' : undefined
                },
                {
                  name: 'outreach',
                  status: status.metrics.outreach_sent > 0 ? 'complete' as const :
                          status.current_phase === 'outreach' ? 'active' as const : 'pending' as const,
                  duration: status.metrics.outreach_sent > 0 ? '3m 20s' : undefined
                },
                {
                  name: 'conversation',
                  status: status.metrics.meetings_scheduled > 0 ? 'complete' as const :
                          status.current_phase === 'conversation' ? 'active' as const : 'pending' as const,
                  duration: status.metrics.meetings_scheduled > 0 ? '12m 30s' : undefined
                },
                {
                  name: 'proposal',
                  status: status.metrics.proposals_generated > 0 ? 'complete' as const :
                          status.current_phase === 'proposal' ? 'active' as const : 'pending' as const,
                  duration: status.metrics.proposals_generated > 0 ? '5m 15s' : undefined
                },
                {
                  name: 'meeting',
                  status: status.status === 'completed' ? 'complete' as const :
                          status.current_phase === 'meeting' ? 'active' as const : 'pending' as const,
                  duration: status.status === 'completed' ? '45m' : undefined
                }
              ]

              return {
                plan_id: plan.plan_id,
                workflow_id: status.workflow_id,
                campaign_name: plan.campaign_name,
                campaign_type: plan.campaign_type,
                status: status.status,
                current_phase: status.current_phase,
                progress_percentage: status.progress_percentage,
                started_at: new Date(status.last_updated).toLocaleString(),
                stages,
                metrics: status.metrics
              } as WorkflowData
            } catch (error) {
              console.error(`Failed to load workflow status for ${plan.plan_id}:`, error)
              return null
            }
          })
      )
      
      setWorkflows(workflowData.filter((workflow): workflow is WorkflowData => workflow !== null))
      setError(null)
    } catch (err) {
      console.error('Failed to load workflows:', err)
      setError('Failed to load workflows')
    } finally {
      setIsLoading(false)
    }
  }

  const handleNewWorkflow = () => {
    navigate('/')
  }

  if (isLoading) {
    return (
      <div className="h-screen bg-white">
        <div className="max-w-4xl mx-auto px-6 py-6">
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-semibold text-black">Workflows</h1>
                <p className="mt-1 text-gray-500">
                  Monitor and control your AI agent workflows
                </p>
              </div>
            </div>
            <div className="flex items-center justify-center py-12">
              <div className="w-6 h-6 border-2 border-gray-400 border-t-black rounded-full animate-spin"></div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-screen bg-white">
        <div className="max-w-4xl mx-auto px-6 py-6">
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-semibold text-black">Workflows</h1>
                <p className="mt-1 text-gray-500">
                  Monitor and control your AI agent workflows
                </p>
              </div>
            </div>
            <div className="text-center py-12">
              <AlertTriangle className="h-12 w-12 mx-auto text-red-400 mb-4" />
              <h3 className="text-lg font-medium text-red-900">Error loading workflows</h3>
              <p className="text-red-600">{error}</p>
              <button onClick={loadWorkflows} className="mt-4 btn-primary">
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen bg-white">
      <div className="max-w-4xl mx-auto px-6 py-6">
        <div className="space-y-8">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-black">Workflows</h1>
              <p className="mt-1 text-gray-500">
                Monitor and control your AI agent workflows
              </p>
            </div>
            <div className="flex items-center space-x-3">
              {/* Real-time connection status */}
              <div className="flex items-center space-x-2 px-3 py-2 bg-gray-50 rounded-lg">
                <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="text-xs text-gray-600">
                  {isConnected ? 'Live Updates' : 'Disconnected'}
                </span>
              </div>
              <button 
                onClick={handleNewWorkflow}
                className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors duration-200"
              >
                <Plus className="h-4 w-4" />
                <span className="text-sm font-medium">New Workflow</span>
              </button>
            </div>
          </div>

          {/* Workflows List */}
          <div className="space-y-4">
            {workflows.map((workflow) => (
              <div key={workflow.plan_id} className="border border-gray-200 rounded-xl bg-white">
                <div className="p-6">
                <div className="flex items-start justify-between mb-6">
                  <div className="flex items-start space-x-4">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        <h3 className="font-medium text-black">{workflow.campaign_name}</h3>
                        {workflow.status === 'executing' && <div className="w-4 h-4 border-2 border-gray-400 border-t-black rounded-full animate-spin"></div>}
                        {workflow.status === 'failed' && <AlertTriangle className="h-4 w-4 text-red-600" />}
                        {workflow.status === 'completed' && <CheckCircle className="h-4 w-4 text-green-600" />}
                      </div>
                      <div className="text-sm text-gray-500 mt-1">
                        {workflow.campaign_type.replace('_', ' ')} • Started {workflow.started_at}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    {workflow.status === 'executing' && (
                      <button className="p-2 hover:bg-gray-50 rounded-lg transition-colors">
                        <Pause className="h-4 w-4" />
                      </button>
                    )}
                    <button className="p-2 hover:bg-gray-50 rounded-lg transition-colors">
                      <RotateCcw className="h-4 w-4" />
                    </button>
                    <button className="p-2 hover:bg-gray-50 rounded-lg transition-colors">
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {/* Browser Viewer for executing workflows */}
                {workflow.status === 'executing' && (
                  <div className="mb-6 ml-6">
                    <div className="flex space-x-6">
                      {/* Pure Browser Viewer - just the screenshot */}
                      <BrowserViewer 
                        workflowId={workflow.workflow_id}
                        className="flex-1 max-w-2xl"
                        onStatusChange={() => {
                          // Handle status updates if needed
                        }}
                      />
                      
                      {/* External status info - clean black text */}
                      <div className="w-64 space-y-4 pt-4">
                        <div className="flex items-center space-x-3">
                          <div className="w-6 h-6 flex items-center justify-center">
                            <svg className="w-4 h-4 text-black" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                          </div>
                          <span className="text-sm font-medium text-black">AI Navigation</span>
                        </div>
                        
                        <AIThoughtProcess workflowId={workflow.workflow_id} />
                      </div>
                    </div>
                  </div>
                )}

                {/* Workflow Progress */}
                <div className="space-y-4">
                  {workflow.stages.map((stage, index) => (
                    <div key={index} className="relative">
                      {/* Connecting line */}
                      {index > 0 && (
                        <div className="absolute left-3 -top-4 w-px h-4 bg-gray-200"></div>
                      )}
                      
                      <div className="flex items-start space-x-4">
                        {/* Status indicator - fixed position */}
                        <div className="relative">
                          {stage.status === 'complete' ? (
                            <div className="w-6 h-6 bg-black rounded-full flex items-center justify-center">
                              <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                              </svg>
                            </div>
                          ) : stage.status === 'active' ? (
                            <div className="w-6 h-6 flex items-center justify-center">
                              <div className="w-4 h-4 border-2 border-gray-400 border-t-black rounded-full animate-spin"></div>
                            </div>
                          ) : stage.status === 'error' ? (
                            <div className="w-6 h-6 bg-red-600 rounded-full flex items-center justify-center">
                              <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                              </svg>
                            </div>
                          ) : (
                            <div className="w-6 h-6 border-2 border-gray-300 rounded-full bg-white"></div>
                          )}
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <span className={
                              stage.status === 'active' ? 'text-black font-medium' : 
                              stage.status === 'complete' ? 'text-gray-600' : 
                              stage.status === 'error' ? 'text-red-600' : 'text-gray-400'
                            }>
                              {stage.name.charAt(0).toUpperCase() + stage.name.slice(1)} Agent
                              {stage.status === 'active' && workflow.status === 'executing' && (
                                <span className="ml-2 text-xs text-blue-600 font-normal">
                                  • Currently working...
                                </span>
                              )}
                            </span>
                            <div className="text-sm text-gray-400">
                              {stage.duration && stage.duration}
                              {stage.error && (
                                <span className="text-red-600 ml-2">{stage.error}</span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                </div>
              </div>
            ))}
          </div>

          {/* Empty State */}
          {workflows.length === 0 && (
            <div className="text-center py-12">
              <Clock className="h-12 w-12 mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-black mb-2">No active workflows</h3>
              <p className="text-gray-500 mb-6">
                Start your first workflow to begin automated prospect processing
              </p>
              <button 
                onClick={handleNewWorkflow}
                className="flex items-center space-x-2 px-4 py-2 bg-black text-white hover:bg-gray-900 rounded-lg transition-colors duration-200 mx-auto"
              >
                <Plus className="h-4 w-4" />
                <span className="text-sm font-medium">Start New Workflow</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}