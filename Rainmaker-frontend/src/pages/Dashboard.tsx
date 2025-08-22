import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bot, ArrowRight, User, CheckCircle, Clock, Zap, Target, Mail, Phone, Plus, Play } from 'lucide-react'
import { 
  startPlanningConversation, 
  sendPlanningMessage, 
  createPlanningWebSocket,
  executeCampaignPlan,
  PlanningResponse 
} from '@/services/campaignPlanningService'
import { useChatStore } from '@/store/chatStore'
import ChatInput from '@/components/ChatInput'

// Mock current workflow
const currentWorkflow = {
  id: '1',
  prospect: {
    name: 'Sarah Johnson',
    company: 'Tech Corp',
    email: 'sarah.j@techcorp.com',
    location: 'San Francisco, CA',
    eventType: 'Corporate Event'
  },
  currentStage: 'enriching',
  stages: [
    { name: 'hunting', status: 'complete', message: 'Found 12 potential prospects matching your criteria', timestamp: '2m ago' },
    { name: 'enriching', status: 'active', message: 'Analyzing company data and event preferences...', timestamp: 'now' },
    { name: 'outreach', status: 'pending' },
    { name: 'conversation', status: 'pending' },
    { name: 'proposal', status: 'pending' },
    { name: 'meeting', status: 'pending' },
  ]
}

interface PlanningMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  clarifications_needed?: string[]
  suggested_responses?: string[]
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  
  // Use global chat store
  const {
    messages,
    conversationId,
    planningResponse,
    hasWorkflow,
    wsConnection,
    setMessages,
    setConversationId,
    setPlanningResponse,
    setHasWorkflow,
    setWsConnection,
    addMessage,
    clearChat
  } = useChatStore()

  const handleNewWorkflow = () => {
    // Close WebSocket connection
    if (wsConnection) {
      wsConnection.close()
    }
    
    clearChat()
    setInput('')
    setIsLoading(false)
    setHasWorkflow(false) // This was missing!
  }

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }, [messages, isLoading])

  const handleStart = async () => {
    if (!input.trim() || isLoading) return
    
    const userMessage = input.trim()
    setInput('')
    setIsLoading(true)
    
    // Immediately add user message to chat for better UX
    const userMessageObj: PlanningMessage = {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toLocaleTimeString()
    }
    addMessage(userMessageObj)
    
    try {
      let response: PlanningResponse
      
      if (!conversationId) {
        // Start new planning conversation with user's first message
        response = await startPlanningConversation({ user_first_message: userMessage })
        setConversationId(response.conversation_id)
        
        // Setup WebSocket for real-time updates (optional)
        try {
          const ws = createPlanningWebSocket(
            response.conversation_id,
            (data) => {
              if (data.type === 'planning_update') {
                setPlanningResponse(data.data)
              }
            }
          )
          setWsConnection(ws)
        } catch (error) {
          console.warn('WebSocket connection failed, continuing without real-time updates:', error)
        }
        
        // Add assistant response (user message already added above)
        const assistantMessage: PlanningMessage = {
          role: 'assistant',
          content: response.assistant_response,
          timestamp: new Date().toLocaleTimeString(),
          clarifications_needed: response.clarifications_needed,
          suggested_responses: response.suggested_responses
        }
        
        addMessage(assistantMessage)
        setPlanningResponse(response)
        
      } else {
        // Continue existing conversation
        response = await sendPlanningMessage(conversationId, userMessage)
        
        // Add only assistant response (user message already added above)
        const assistantMessage: PlanningMessage = {
          role: 'assistant',
          content: response.assistant_response,
          timestamp: new Date().toLocaleTimeString(),
          clarifications_needed: response.clarifications_needed,
          suggested_responses: response.suggested_responses
        }
        
        addMessage(assistantMessage)
        setPlanningResponse(response)
      }
      
      // If planning is complete and we have a campaign plan, show workflow view
      const activeResponse = planningResponse || response;
      if (activeResponse && activeResponse.is_complete && activeResponse.campaign_plan) {
        setTimeout(() => {
          setHasWorkflow(true)
        }, 1000)
      }
      
    } catch (error) {
      console.error('Failed to process planning message:', error)
      
      // Provide specific error messages based on error type
      let errorMessage = 'Sorry, I encountered an error. Please try again.'
      
      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        errorMessage = 'The planning process is taking longer than expected. This is normal for complex analysis. Please try again.'
      } else if (error.response?.status === 500) {
        errorMessage = 'There was a server error. Please try again in a moment.'
      } else if (error.response?.status === 400) {
        errorMessage = 'There was an issue with your request. Please check your input and try again.'
      }
      
      // Add error message to chat (user message already added above)
      addMessage({ role: 'assistant', content: errorMessage, timestamp: new Date().toLocaleTimeString() })
    } finally {
      setIsLoading(false)
    }
  }
  

  if (!hasWorkflow) {
    return (
      <div className={`h-screen relative overflow-hidden transition-all duration-1000 ease-out ${
        messages.length === 0 
          ? 'bg-cover bg-center bg-no-repeat' 
          : 'bg-white'
      }`}
      style={{
        backgroundImage: messages.length === 0 ? 'url(/assets/before.jpg)' : 'none'
      }}>
        {messages.length === 0 && (
          // Soft overlay for better text readability
          <div className="absolute inset-0 bg-white/10 pointer-events-none"></div>
        )}
        {messages.length === 0 ? (
          // Initial centered state
          <div className="h-full flex flex-col items-center justify-center -mt-16 relative z-10">
            <div className="text-center mb-10">
              <div className="flex items-center justify-center space-x-6 mb-4">
                <img src="/favicon.svg" alt="Rainmaker Logo" className="w-12 h-12" />
                <h1 className="text-6xl font-light text-gray-800">Rainmaker</h1>
              </div>
            </div>
            
            {/* Centered Chat Input - Narrower */}
            <div className="w-full max-w-xl px-6">
              <div className="relative transform hover:scale-105 focus-within:scale-105 transition-all duration-300 ease-out">
                <ChatInput
                  value={input}
                  onChange={setInput}
                  onSubmit={handleStart}
                  placeholder="Tell me what kind of prospects you're looking for..."
                  disabled={isLoading}
                  isLoading={isLoading}
                />
                
                
              </div>
            </div>
          </div>
        ) : (
          // Chat mode with messages
          <div className="h-screen flex">
            <div className="flex-1 relative">
              {/* Floating Chat Header */}
              <div className="absolute top-0 left-0 right-0 z-10 bg-gradient-to-b from-white via-white to-transparent px-8 py-3">
                <div className="max-w-2xl mx-auto flex justify-between items-center">
                  <div className="flex items-center space-x-2">
                    <h1 className="text-base font-medium text-gray-900">Rainmaker</h1>
                  </div>
                  <button
                    onClick={handleNewWorkflow}
                    className="flex items-center space-x-2 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors duration-200"
                  >
                    <Plus className="w-4 h-4" />
                    <span>New Chat</span>
                  </button>
                </div>
              </div>
              
              <div ref={chatContainerRef} className="h-full overflow-y-auto pt-16 pb-24 scrollbar-hide">
                <div className="max-w-2xl mx-auto px-8 py-6">
                  <div className="space-y-8">
                    {messages.map((message, index) => (
                      <div key={index}>
                        {message.role === 'user' && (
                          <div className="flex justify-end mb-8">
                            <div className="bg-gray-800 text-white rounded-3xl px-5 py-3 max-w-md shadow-sm">
                              <p className="text-base leading-relaxed">{message.content}</p>
                            </div>
                          </div>
                        )}
                        {message.role === 'assistant' && (
                          <div className="mb-8">
                            <div className="w-full text-gray-900">
                              <div className="text-lg font-normal text-left prose prose-lg max-w-none" style={{ lineHeight: '1.8' }}>
                                <p className="text-left mb-4">{message.content}</p>
                              </div>
                              
                              {/* Clarifications Needed */}
                              {message.clarifications_needed && message.clarifications_needed.length > 0 && (
                                <div className="mt-4 p-4 bg-slate-50 border-l-4 border-slate-900 rounded-r-lg">
                                  <div className="text-sm font-medium text-slate-900 mb-3">I need clarification on:</div>
                                  <ul className="text-sm text-slate-700 space-y-1 pl-2">
                                    {message.clarifications_needed.map((clarification, idx) => (
                                      <li key={idx} className="flex items-start space-x-2">
                                        <span className="text-slate-400 mt-1 text-xs">•</span>
                                        <span>{clarification}</span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              
                              {/* Campaign Execution Button */}
                              {planningResponse && planningResponse.is_complete && planningResponse.campaign_plan && index === messages.length - 1 && (
                                <div className="mt-4 flex items-center space-x-3">
                                  <button
                                    onClick={() => {
                                      console.log('Start Campaign button clicked')
                                      console.log('Campaign plan to execute:', planningResponse.campaign_plan)
                                      console.log('Plan ID:', planningResponse.campaign_plan.plan_id)
                                      
                                      // Start campaign execution (don't wait for it to complete)
                                      executeCampaignPlan(planningResponse.campaign_plan.plan_id)
                                        .then(result => {
                                          console.log('Campaign execution started:', result)
                                        })
                                        .catch(error => {
                                          console.error('Failed to start campaign execution:', error)
                                        })
                                      
                                      // Show success message
                                      addMessage({
                                        role: 'assistant',
                                        content: '🚀 Campaign launched! Redirecting to workflows...',
                                        timestamp: new Date().toLocaleTimeString()
                                      })
                                      
                                      // Navigate to workflows page immediately
                                      console.log('Navigating to workflows page')
                                      window.location.href = '/workflows'
                                    }}
                                    className="flex items-center space-x-2 px-4 py-2.5 bg-black hover:bg-gray-900 text-white rounded-lg transition-all duration-200 text-sm font-medium shadow-sm hover:shadow-md"
                                  >
                                    <Play className="h-4 w-4" />
                                    <span>Start Campaign</span>
                                  </button>
                                  <span className="text-sm text-gray-500">or continue refining the plan below</span>
                                </div>
                              )}

                              {/* Suggested Responses */}
                              {message.suggested_responses && message.suggested_responses.length > 0 && (
                                <div className="mt-4">
                                  <div className="text-sm font-medium text-gray-700 mb-2">Quick responses:</div>
                                  <div className="flex flex-wrap gap-2">
                                    {message.suggested_responses.map((suggestion, idx) => (
                                      <button
                                        key={idx}
                                        onClick={() => setInput(suggestion)}
                                        className="px-3 py-1 text-sm bg-white border border-gray-200 rounded-full hover:bg-gray-50 transition-colors"
                                      >
                                        {suggestion}
                                      </button>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                    
                    {isLoading && (
                      <div className="mb-8">
                        <div className="flex items-center space-x-3">
                          <div className="flex items-center space-x-1">
                            <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse"></div>
                            <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                            <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                          </div>
                          <span className="text-sm text-gray-500">Analyzing your requirements and creating a tailored strategy...</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              
              {/* Floating bottom chat input */}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-white via-white to-transparent p-6">
                <div className="max-w-2xl mx-auto">
                  <ChatInput
                    value={input}
                    onChange={setInput}
                    onSubmit={handleStart}
                    placeholder="Continue the conversation..."
                    disabled={isLoading}
                    isLoading={isLoading}
                  />
                </div>
              </div>
            </div>
            
            {/* Planning Progress - Right Side - FIXED */}
            {planningResponse && (
              <div className="w-64 bg-white p-6 flex-shrink-0 flex items-center">
                <div className="w-full">
                  <h3 className="text-sm font-medium text-gray-900 mb-4">Data Collection Progress</h3>
                  <div className="space-y-4">
                    {/* Progress Bar */}
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-black h-2 rounded-full transition-all duration-300" 
                        style={{ width: `${Math.round(planningResponse.completion_percentage * 100)}%` }}
                      ></div>
                    </div>
                    <div className="text-sm text-gray-600">
                      {planningResponse.completion_percentage >= 1.0 
                        ? "100% complete - Ready to launch!" 
                        : `${Math.round(planningResponse.completion_percentage * 100)}% complete`}
                    </div>
                    
                    {/* Requirements Checklist */}
                    <div className="space-y-4 mt-4">
                      <div className="text-xs font-medium text-gray-700 mb-2">Required Information:</div>
                      
                      {planningResponse.completion_percentage >= 1.0 ? (
                        <div className="flex items-center space-x-3">
                          <div className="relative">
                            <div className="w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
                              <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                              </svg>
                            </div>
                          </div>
                          <span className="text-xs text-gray-600 font-medium">
                            Ready to launch campaign!
                          </span>
                        </div>
                      ) : (
                        [
                          { name: "Event types", threshold: 0.25 },
                          { name: "Geographic location", threshold: 0.50 },
                          { name: "Search methods", threshold: 0.75 },
                          { name: "Number of prospects", threshold: 0.90 },
                          { name: "Ready to proceed", threshold: 1.00 }
                        ].map((step, index) => {
                          const isCompleted = planningResponse.completion_percentage >= step.threshold
                          const isCurrentStep = 
                            planningResponse.completion_percentage < step.threshold && 
                            (index === 0 || planningResponse.completion_percentage >= ([0.25, 0.50, 0.75, 0.90][index - 1] || 0))
                          const isPending = !isCompleted && !isCurrentStep
                          
                          // Don't show the "Ready to proceed" step until we're actually at 100%
                          if (step.threshold === 1.00 && planningResponse.completion_percentage < 1.00) {
                            return null
                          }
                          
                          return (
                            <div key={index} className="relative">
                              {/* Connecting line */}
                              {index > 0 && (
                                <div className={`absolute left-2 -top-3 w-px h-3 ${
                                  planningResponse.completion_percentage >= ([0.25, 0.50, 0.75, 0.90][index - 1] || 0)
                                    ? 'bg-black' 
                                    : 'bg-gray-200'
                                }`}></div>
                              )}
                              
                              <div className="flex items-center space-x-3">
                                {/* Status indicator */}
                                <div className="relative">
                                  {isCompleted ? (
                                    <div className="w-4 h-4 bg-black rounded-full flex items-center justify-center">
                                      <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                      </svg>
                                    </div>
                                  ) : isCurrentStep ? (
                                    <div className="w-4 h-4 flex items-center justify-center">
                                      <div className="w-3 h-3 border-2 border-gray-400 border-t-black rounded-full animate-spin"></div>
                                    </div>
                                  ) : (
                                    <div className="w-4 h-4 border border-gray-300 rounded-full"></div>
                                  )}
                                </div>
                                
                                <span className={`text-xs ${
                                  isPending ? 'text-gray-400' : 'text-gray-600'
                                }`}>
                                  {step.name}
                                </span>
                              </div>
                            </div>
                          )
                        })
                      )}
                    </div>
                    
                    {/* Current Status */}
                    <div className="mt-6 pt-4 border-t border-gray-100">
                      <div className="flex items-center space-x-2">
                        <div className="w-3 h-3 border border-gray-400 border-t-black rounded-full animate-spin"></div>
                        <div className="text-xs font-medium text-gray-900">
                          {planningResponse.current_phase.replace('_', ' ')}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  // Active workflow state
  return (
    <div className="h-screen bg-white">
      <div className="max-w-4xl mx-auto px-6 py-6">
        <div className="space-y-8">
          {/* Workflow Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 bg-black rounded-full animate-pulse"></div>
              <h1 className="text-lg font-medium">Active Workflow</h1>
            </div>
            <button 
              onClick={handleNewWorkflow}
              className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors duration-200"
            >
              <Plus className="w-4 h-4" />
              <span className="text-sm font-medium">New Workflow</span>
            </button>
          </div>

          {/* Current Prospect */}
          <div className="border border-gray-200 rounded-xl bg-white p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center">
                  <User className="h-6 w-6 text-gray-600" />
                </div>
                <div>
                  <h2 className="text-lg font-medium text-gray-900">{currentWorkflow.prospect.name}</h2>
                  <p className="text-sm text-gray-500">
                    {currentWorkflow.prospect.company} • {currentWorkflow.prospect.eventType}
                  </p>
                </div>
              </div>
              <div className="text-right text-sm text-gray-500">
                <div className="flex items-center space-x-2 mb-1">
                  <Mail className="h-4 w-4" />
                  <span>{currentWorkflow.prospect.email}</span>
                </div>
                <div className="text-gray-400">{currentWorkflow.prospect.location}</div>
              </div>
            </div>
          </div>

          {/* Workflow Progress */}
          <div className="border border-gray-200 rounded-xl bg-white transition-all duration-300 ease-out">
            <div className="p-6">
              <div className="space-y-6">
                {currentWorkflow.stages.map((stage, index) => (
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
                        ) : (
                          <div className="w-6 h-6 border-2 border-gray-300 rounded-full bg-white"></div>
                        )}
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <h3 className={`font-medium ${
                            stage.status === 'pending' ? 'text-gray-400' : 'text-black'
                          }`}>
                            {stage.name.charAt(0).toUpperCase() + stage.name.slice(1)} Agent
                          </h3>
                        </div>
                        
                        {stage.message && (
                          <div className="mt-2 text-sm text-gray-600">
                            {stage.message}
                          </div>
                        )}
                        
                        {stage.timestamp && (
                          <div className="text-xs text-gray-400 mt-2">{stage.timestamp}</div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}