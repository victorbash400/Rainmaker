import { useState, useEffect, useRef } from 'react'
import { Pause, RotateCcw, X, Clock, CheckCircle, AlertTriangle, Plus, Radio, MessageSquarePlus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { 
  getCampaignPlans, 
  getCampaignExecutionStatus,
  createWorkflowStatusWebSocket
} from '@/services/campaignPlanningService'
import BrowserViewer from '@/components/BrowserViewer'
import EnrichmentViewer from '@/components/EnrichmentViewer'
import OutreachViewer from '@/components/OutreachViewer'
import ProposalViewer from '@/components/ProposalViewer'
import MeetingViewer from '@/components/MeetingViewer'

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

  const generateStages = (status: { current_phase: string, status: string, metrics: any }) => {
    const stages = [
      {
        name: 'hunting',
        status: (['enriching', 'outreach', 'awaiting_reply', 'conversation', 'awaiting_overview', 'awaiting_overview_reply', 'proposal', 'meeting', 'completed'].includes(status.current_phase) || status.status === 'completed') ? 'complete' as const : 
                (['discovery', 'hunting'].includes(status.current_phase)) ? 'active' as const : 'pending' as const,
        duration: (['enriching', 'outreach', 'awaiting_reply', 'conversation', 'awaiting_overview', 'awaiting_overview_reply', 'proposal', 'meeting', 'completed'].includes(status.current_phase) || status.status === 'completed') ? '2m 15s' : undefined
      },
      {
        name: 'enriching',
        status: (['outreach', 'awaiting_reply', 'conversation', 'awaiting_overview', 'awaiting_overview_reply', 'proposal', 'meeting', 'completed'].includes(status.current_phase) || status.status === 'completed') ? 'complete' as const :
                status.current_phase === 'enriching' ? 'active' as const : 'pending' as const,
        duration: (['outreach', 'awaiting_reply', 'conversation', 'awaiting_overview', 'awaiting_overview_reply', 'proposal', 'meeting', 'completed'].includes(status.current_phase) || status.status === 'completed') ? '1m 45s' : undefined
      },
      {
        name: 'outreach',
        status: (['conversation', 'awaiting_overview', 'awaiting_overview_reply', 'proposal', 'meeting', 'completed'].includes(status.current_phase) || status.status === 'completed') ? 'complete' as const :
                (['outreach', 'awaiting_reply'].includes(status.current_phase)) ? 'active' as const : 'pending' as const,
        duration: (['conversation', 'awaiting_overview', 'awaiting_overview_reply', 'proposal', 'meeting', 'completed'].includes(status.current_phase) || status.status === 'completed') ? '3m 20s' : undefined
      },
      {
        name: 'conversation',
        status: (['proposal', 'meeting', 'completed'].includes(status.current_phase) || status.status === 'completed') ? 'complete' as const :
                (['conversation', 'awaiting_overview', 'awaiting_overview_reply'].includes(status.current_phase)) ? 'active' as const : 'pending' as const,
        duration: (['proposal', 'meeting', 'completed'].includes(status.current_phase) || status.status === 'completed') ? '12m 30s' : undefined
      },
      {
        name: 'proposal',
        status: (status.metrics.proposals_generated > 0 || status.status === 'completed' || ['meeting'].includes(status.current_phase)) ? 'complete' as const :
                status.current_phase === 'proposal' ? 'active' as const : 'pending' as const,
        duration: (status.metrics.proposals_generated > 0 || status.status === 'completed' || ['meeting'].includes(status.current_phase)) ? '5m 15s' : undefined
      },
      {
        name: 'meeting',
        status: status.status === 'completed' ? 'complete' as const :
                status.current_phase === 'meeting' ? 'active' as const : 'pending' as const,
        duration: status.status === 'completed' ? '45m' : undefined
      }
    ];
  
    if (status.status === 'completed') {
      // Mark all previous stages as complete
      stages.forEach(stage => stage.status = 'complete');
      stages.push({
        name: 'Done',
        status: 'complete' as const,
        duration: ''
      });
    }
    return stages;
  }

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
                  console.log(`🔄 Workflow ${data.plan_id}: ${data.current_phase} (${data.status})`)
                }
                console.log(`📊 All workflow data:`, data)
                console.log(`🎯 Current phase in data:`, data.current_phase, `Status:`, data.status)
                
                // Regenerate stages with updated current_phase
                const updatedStatus = {
                  current_phase: data.current_phase,
                  status: data.status,
                  metrics: data.metrics || workflow.metrics
                }
                
                const stages = generateStages(updatedStatus)
                
                return {
                  ...workflow,
                  status: data.status,
                  current_phase: data.current_phase,
                  progress_percentage: data.progress_percentage,
                  metrics: data.metrics || workflow.metrics,
                  stages: stages
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
              
              const stages = generateStages(status)

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
      <div className="h-full flex">
        <div className="flex-1 relative">
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
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2 text-sm text-gray-600">
                    <Radio className={`h-4 w-4 ${isConnected ? 'text-green-500' : 'text-gray-400'}`} />
                    <span>Live Updates</span>
                  </div>
                  <button 
                    onClick={handleNewWorkflow}
                    className="flex items-center space-x-2 px-3 py-1.5 bg-black text-white hover:bg-gray-800 rounded-md transition-colors text-sm"
                  >
                    <MessageSquarePlus className="h-4 w-4" />
                    <span>New Workflow</span>
                  </button>
                </div>
              </div>

              {/* Workflows List */}
              <div className="space-y-6">
                {workflows.map((workflow) => (
                  <div key={workflow.plan_id} className="border border-gray-200 rounded-xl bg-white">
                  <div className="p-6">
                    <div className="flex items-start justify-between mb-6">
                      <div className="flex items-start space-x-4">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3">
                            <h3 className="font-medium text-black">{workflow.campaign_name}</h3>
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

                    {/* Agent Viewers for executing workflows */}
                    {workflow.status === 'executing' && (
                      <div className="mb-6">
                        <div className="flex space-x-6">
                          {/* Show different viewers based on current phase */}
                          {(workflow.current_phase === 'discovery' || workflow.current_phase === 'hunting') && (
                            <>
                              {console.log('🔍 RENDERING BrowserViewer for workflow:', workflow.workflow_id, 'phase:', workflow.current_phase)}
                              {/* Browser Viewer for prospect hunting */}
                              <BrowserViewer 
                                workflowId={workflow.workflow_id}
                                className="flex-1 max-w-2xl"
                                onStatusChange={() => {
                                  // Handle status updates if needed
                                }}
                              />
                              
                              {/* External status info for hunting */}
                              <div className="w-64 space-y-4 pt-4">
                                <div className="flex items-center space-x-3">
                                  <div className="w-6 h-6 flex items-center justify-center">
                                    <svg className="w-4 h-4 text-black" fill="currentColor" viewBox="0 0 20 20">
                                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                    </svg>
                                  </div>
                                  <span className="text-sm font-medium text-black">🔍 AI Prospect Hunting</span>
                                </div>
                                
                                <AIThoughtProcess workflowId={workflow.workflow_id} />
                              </div>
                            </>
                          )}
                          
                          {workflow.current_phase === 'enriching' && (
                            <>
                              {console.log('🟢 RENDERING EnrichmentViewer for workflow:', workflow.workflow_id, 'phase:', workflow.current_phase)}
                              {/* Enrichment Viewer for prospect enrichment */}
                              <EnrichmentViewer 
                                workflowId={workflow.workflow_id}
                                className="flex-1 max-w-2xl"
                                onStatusChange={() => {
                                  // Handle status updates if needed
                                }}
                              />
                            </>
                          )}
                          
                          {(workflow.current_phase === 'outreach' || workflow.current_phase === 'awaiting_reply' || workflow.current_phase === 'conversation' || workflow.current_phase === 'awaiting_overview' || workflow.current_phase === 'awaiting_overview_reply') && (
                            <>
                              {console.log('📧 RENDERING OutreachViewer for workflow:', workflow.workflow_id, 'phase:', workflow.current_phase)}
                              {/* Outreach Viewer for email campaigns and reply monitoring */}
                              <OutreachViewer 
                                workflowId={workflow.workflow_id}
                                onComplete={() => {
                                  // Refresh workflow data when outreach completes
                                  loadWorkflows();
                                }}
                              />
                            </>
                          )}
                          
                          {workflow.current_phase === 'proposal' && (
                            <>
                              {console.log('📋 RENDERING ProposalViewer for workflow:', workflow.workflow_id, 'phase:', workflow.current_phase)}
                              {/* Proposal Viewer for proposal generation and sending */}
                              <ProposalViewer 
                                workflowId={workflow.workflow_id}
                                onComplete={() => {
                                  // Refresh workflow data when proposal workflow completes
                                  loadWorkflows();
                                }}
                              />
                            </>
                          )}
                          
                          {workflow.current_phase === 'meeting' && (
                            <>
                              {console.log('📅 RENDERING MeetingViewer for workflow:', workflow.workflow_id, 'phase:', workflow.current_phase)}
                              {/* Meeting Viewer for meeting response checking and scheduling */}
                              <MeetingViewer 
                                workflowId={workflow.workflow_id}
                                onComplete={() => {
                                  // Refresh workflow data when meeting workflow completes
                                  loadWorkflows();
                                }}
                              />
                            </>
                          )}
                          
                          {/* Debug: Show current phase */}
                          {console.log('🔍 WORKFLOW DEBUG:', {
                            plan_id: workflow.plan_id,
                            current_phase: workflow.current_phase,
                            status: workflow.status,
                            all_phases: ['discovery', 'hunting', 'enriching', 'outreach', 'awaiting_reply', 'conversation', 'awaiting_overview', 'awaiting_overview_reply', 'proposal', 'meeting'],
                            should_show_proposal: workflow.current_phase === 'proposal',
                            should_show_meeting: workflow.current_phase === 'meeting'
                          })}
                          
                          {/* Default view for other phases */}
                          {!['discovery', 'hunting', 'enriching', 'outreach', 'awaiting_reply', 'conversation', 'awaiting_overview', 'awaiting_overview_reply', 'proposal', 'meeting'].includes(workflow.current_phase) && (
                            <div className="flex-1 max-w-2xl">
                              <div className="bg-gray-50 rounded-lg p-6 min-h-[400px] flex items-center justify-center">
                                <div className="text-center text-gray-500">
                                  <div className="w-16 h-16 mx-auto mb-4 bg-gray-200 rounded-full flex items-center justify-center">
                                    <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                    </svg>
                                  </div>
                                  <h3 className="text-lg font-medium text-gray-900 mb-2">{workflow.current_phase.charAt(0).toUpperCase() + workflow.current_phase.slice(1)} Phase</h3>
                                  <p className="text-sm text-gray-600">Agent working on {workflow.current_phase} tasks</p>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
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

        {/* Agent Progress Sidebar - Clean Tasteful Design */}
        {workflows.length > 0 && (
          <div className="w-72 bg-white p-6 pl-12 flex-shrink-0 flex items-center">
            <div className="w-full">
              <h3 className="text-base font-medium text-black mb-6">Agent Progress</h3>
              <div className="space-y-8">
                {workflows.map((workflow) => (
                  <div key={workflow.plan_id} className="space-y-5">
                    {/* Workflow header */}
                    <div className="pb-3 border-b border-gray-100">
                      <h4 className="text-sm font-medium text-black">
                        {workflow.campaign_name}
                      </h4>
                      <p className="text-xs text-gray-500 mt-1">
                        {workflow.status === 'completed' ? 'Done' : workflow.status.replace('_', ' ')}
                      </p>
                    </div>
                    
                    {/* Progress steps */}
                    <div className="space-y-5">
                      {workflow.stages.map((stage, index) => (
                        <div key={index} className="relative">
                          {/* Connecting line */}
                          {index > 0 && (
                            <div className={`absolute left-3 -top-4 w-px h-4 ${
                              workflow.stages[index - 1].status === 'complete' ? 'bg-black' : 'bg-gray-200'
                            }`}></div>
                          )}
                          
                          <div className="flex items-center space-x-4">
                            {/* Status indicator */}
                            <div className="relative flex-shrink-0">
                              {stage.status === 'complete' ? (
                                <div className="w-6 h-6 bg-black rounded-full flex items-center justify-center">
                                  <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                                  </svg>
                                </div>
                              ) : stage.status === 'active' ? (
                                <div className="w-6 h-6 flex items-center justify-center">
                                  <div className="w-4 h-4 border-2 border-gray-300 border-t-black rounded-full animate-spin"></div>
                                </div>
                              ) : stage.status === 'error' ? (
                                <div className="w-6 h-6 bg-red-500 rounded-full flex items-center justify-center">
                                  <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                  </svg>
                                </div>
                              ) : (
                                <div className="w-6 h-6 flex items-center justify-center">
                                  <div className="w-4 h-4 border-2 border-gray-200 rounded-full bg-white"></div>
                                </div>
                              )}
                            </div>
                            
                            {/* Stage info */}
                            <div className="flex-1">
                              <div className="flex items-center justify-between">
                                <span className={`text-sm font-medium ${
                                  stage.status === 'active' ? 'text-black' : 
                                  stage.status === 'complete' ? 'text-gray-700' : 
                                  stage.status === 'error' ? 'text-red-600' : 'text-gray-400'
                                }`}>
                                  {stage.name.charAt(0).toUpperCase() + stage.name.slice(1)}
                                </span>
                                
                                {stage.status === 'complete' && stage.duration && (
                                  <span className="text-xs text-gray-400">
                                    {stage.duration}
                                  </span>
                                )}
                              </div>
                              
                              {stage.error && (
                                <p className="text-xs text-red-500 mt-1">
                                  {stage.error}
                                </p>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}