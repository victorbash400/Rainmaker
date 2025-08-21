import { useState, useEffect } from 'react'
import { Play, Pause, RotateCcw, X, Clock, CheckCircle, AlertTriangle, Target, Users, Calendar, TrendingUp, Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { 
  getCampaignPlans, 
  getCampaignExecutionStatus, 
  executeCampaignPlan,
  resumeWorkflow,
  CampaignPlanSummary,
  ExecutionStatus
} from '@/services/campaignPlanningService'

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState<CampaignPlanSummary[]>([])
  const [executionStatuses, setExecutionStatuses] = useState<Record<string, ExecutionStatus>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    loadCampaigns()
  }, [])

  const loadCampaigns = async () => {
    try {
      setIsLoading(true)
      const campaignPlans = await getCampaignPlans()
      setCampaigns(campaignPlans)

      // Load execution status for each campaign
      const statuses: Record<string, ExecutionStatus> = {}
      await Promise.all(
        campaignPlans.map(async (campaign) => {
          try {
            const status = await getCampaignExecutionStatus(campaign.plan_id)
            statuses[campaign.plan_id] = status
          } catch (error) {
            console.error(`Failed to load status for campaign ${campaign.plan_id}:`, error)
          }
        })
      )
      setExecutionStatuses(statuses)
    } catch (err) {
      console.error('Failed to load campaigns:', err)
      setError('Failed to load campaigns')
    } finally {
      setIsLoading(false)
    }
  }

  const handleExecuteCampaign = async (planId: string) => {
    try {
      await executeCampaignPlan(planId)
      // Reload to get updated status
      await loadCampaigns()
    } catch (error) {
      console.error('Failed to execute campaign:', error)
    }
  }

  const handleResumeWorkflow = async (workflowId: string) => {
    try {
      const result = await resumeWorkflow(workflowId)
      if (result.success) {
        console.log('Workflow resumed:', result.message)
        // Reload to get updated status
        await loadCampaigns()
      } else {
        console.error('Failed to resume workflow:', result.message)
      }
    } catch (error) {
      console.error('Failed to resume workflow:', error)
    }
  }

  const handleCreateCampaign = () => {
    navigate('/')
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Campaigns</h1>
            <p className="mt-1 text-sm text-gray-500">
              Manage your outreach campaigns and track performance
            </p>
          </div>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="w-6 h-6 border-2 border-gray-400 border-t-black rounded-full animate-spin"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Campaigns</h1>
            <p className="mt-1 text-sm text-gray-500">
              Manage your outreach campaigns and track performance
            </p>
          </div>
        </div>
        <div className="text-center py-12">
          <AlertTriangle className="h-12 w-12 mx-auto text-red-400 mb-4" />
          <h3 className="text-lg font-medium text-red-900">Error loading campaigns</h3>
          <p className="text-red-600">{error}</p>
          <button onClick={loadCampaigns} className="mt-4 btn-primary">
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Campaigns</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage your outreach campaigns and track performance
          </p>
        </div>
        <button onClick={handleCreateCampaign} className="btn-primary flex items-center space-x-2">
          <Plus className="h-4 w-4" />
          <span>Create Campaign</span>
        </button>
      </div>

      {campaigns.length === 0 ? (
        <div className="card">
          <div className="card-content">
            <div className="text-center py-12">
              <div className="h-12 w-12 mx-auto bg-gray-100 rounded-full flex items-center justify-center">
                <Target className="h-6 w-6 text-gray-400" />
              </div>
              <h3 className="mt-4 text-lg font-medium text-gray-900">No campaigns yet</h3>
              <p className="mt-2 text-sm text-gray-500">
                Create your first outreach campaign to start engaging prospects
              </p>
              <div className="mt-6">
                <button onClick={handleCreateCampaign} className="btn-primary">
                  Create Your First Campaign
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="grid gap-6">
          {campaigns.map((campaign) => {
            const status = executionStatuses[campaign.plan_id]
            return (
              <div key={campaign.plan_id} className="card">
                <div className="card-content">
                  <div className="flex items-start justify-between mb-6">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">{campaign.campaign_name}</h3>
                        <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                          {campaign.campaign_type.replace('_', ' ')}
                        </span>
                        {status && (
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                            status.status === 'ready' ? 'bg-gray-100 text-gray-800' :
                            status.status === 'executing' ? 'bg-yellow-100 text-yellow-800' :
                            status.status === 'completed' ? 'bg-green-100 text-green-800' :
                            status.status === 'paused_for_manual_login' ? 'bg-orange-100 text-orange-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {status.status === 'paused_for_manual_login' ? 'paused for login' : status.status}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mb-3">
                        Created {new Date(campaign.created_at).toLocaleDateString()}
                      </p>
                      
                      {/* Campaign Objectives */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                        <div className="flex items-center space-x-2">
                          <Target className="h-4 w-4 text-gray-400" />
                          <span className="text-sm text-gray-600">
                            Target: {campaign.target_profile.industry || 'Various'}
                          </span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Users className="h-4 w-4 text-gray-400" />
                          <span className="text-sm text-gray-600">
                            Budget: ${campaign.target_profile.budget_range || 'Flexible'}
                          </span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Calendar className="h-4 w-4 text-gray-400" />
                          <span className="text-sm text-gray-600">
                            Goal: {campaign.objectives.primary_goal || 'Generate leads'}
                          </span>
                        </div>
                      </div>
                      
                      {/* Execution Progress */}
                      {status && status.status === 'executing' && (
                        <div className="mb-4">
                          <div className="flex items-center justify-between text-sm mb-2">
                            <span className="font-medium text-gray-700">Progress</span>
                            <span className="text-gray-600">{status.progress_percentage}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                              style={{ width: `${status.progress_percentage}%` }}
                            ></div>
                          </div>
                          <p className="text-xs text-gray-500 mt-1">
                            Current phase: {status.current_phase}
                          </p>
                        </div>
                      )}

                      {/* Login Pause Message */}
                      {status && status.status === 'paused_for_manual_login' && (
                        <div className="mb-4 p-3 bg-orange-50 border border-orange-200 rounded-lg">
                          <div className="flex items-center space-x-2 mb-2">
                            <Pause className="h-4 w-4 text-orange-600" />
                            <span className="font-medium text-orange-800">Manual Login Required</span>
                          </div>
                          <p className="text-sm text-orange-700 mb-2">
                            {status.message || status.login_info?.message || 'The workflow is paused waiting for manual login.'}
                          </p>
                          <p className="text-xs text-orange-600">
                            Please log into the required site manually, then click "Resume" to continue.
                          </p>
                        </div>
                      )}
                      
                      {/* Campaign Metrics */}
                      {status && (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                          <div className="bg-gray-50 rounded-lg p-3">
                            <div className="text-lg font-semibold text-gray-900">
                              {status.metrics.prospects_discovered}
                            </div>
                            <div className="text-xs text-gray-500">Prospects</div>
                          </div>
                          <div className="bg-gray-50 rounded-lg p-3">
                            <div className="text-lg font-semibold text-gray-900">
                              {status.metrics.outreach_sent}
                            </div>
                            <div className="text-xs text-gray-500">Outreach</div>
                          </div>
                          <div className="bg-gray-50 rounded-lg p-3">
                            <div className="text-lg font-semibold text-gray-900">
                              {status.metrics.meetings_scheduled}
                            </div>
                            <div className="text-xs text-gray-500">Meetings</div>
                          </div>
                          <div className="bg-gray-50 rounded-lg p-3">
                            <div className="text-lg font-semibold text-gray-900">
                              {status.metrics.proposals_generated}
                            </div>
                            <div className="text-xs text-gray-500">Proposals</div>
                          </div>
                        </div>
                      )}
                    </div>
                    
                    <div className="flex items-center space-x-2 ml-4">
                      {status?.status === 'ready' && (
                        <button 
                          onClick={() => handleExecuteCampaign(campaign.plan_id)}
                          className="p-2 hover:bg-green-50 text-green-600 rounded-lg transition-colors"
                          title="Execute Campaign"
                        >
                          <Play className="h-4 w-4" />
                        </button>
                      )}
                      {status?.status === 'executing' && (
                        <button className="p-2 hover:bg-yellow-50 text-yellow-600 rounded-lg transition-colors">
                          <Pause className="h-4 w-4" />
                        </button>
                      )}
                      {status?.status === 'paused_for_manual_login' && (
                        <button 
                          onClick={() => handleResumeWorkflow(status.workflow_id)}
                          className="px-3 py-1 bg-orange-600 hover:bg-orange-700 text-white text-sm rounded-lg transition-colors"
                          title="Resume after login"
                        >
                          Resume
                        </button>
                      )}
                      <button className="p-2 hover:bg-gray-50 text-gray-600 rounded-lg transition-colors">
                        <RotateCcw className="h-4 w-4" />
                      </button>
                      <button className="p-2 hover:bg-red-50 text-red-600 rounded-lg transition-colors">
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}