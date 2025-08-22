import { useState, useEffect, useRef } from 'react'

interface EnrichmentViewerProps {
  workflowId: string
  className?: string
  onStatusChange?: (status: {
    isConnected: boolean
    currentStep: string
    reasoning: string
  }) => void
}

interface EnrichmentUpdate {
  type: string
  workflow_id: string
  step: string
  reasoning: string
  status: string
  timestamp: string
  data?: any
}

export default function EnrichmentViewer({ workflowId, className = "", onStatusChange }: EnrichmentViewerProps) {
  const [isConnected, setIsConnected] = useState(false)
  const [currentStep, setCurrentStep] = useState('Initializing enrichment...')
  const [aiReasoning, setAiReasoning] = useState<string>('Preparing to analyze prospect data...')
  const [status, setStatus] = useState<string>('connecting')
  const [enrichmentData, setEnrichmentData] = useState<any>(null)
  
  const websocketRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    console.log('EnrichmentViewer mounting for workflow:', workflowId)
    // Start connecting with a small delay to allow backend to be ready
    const connectTimeout = setTimeout(() => {
      connect()
    }, 100) // Small delay to ensure component is ready
    
    return () => {
      clearTimeout(connectTimeout)
      cleanup()
    }
  }, [workflowId])

  // Retry connection with exponential backoff
  useEffect(() => {
    if (!isConnected) {
      const retryTimeout = setTimeout(() => {
        console.log('EnrichmentViewer not connected, attempting connection...')
        connect()
      }, 1000)
      
      return () => clearTimeout(retryTimeout)
    }
  }, [isConnected])

  const connect = () => {
    console.log('🚀 EnrichmentViewer connect() called for workflow:', workflowId)
    
    if (websocketRef.current?.readyState === WebSocket.OPEN) {
      console.log('⚠️ WebSocket already open, skipping connection')
      return
    }

    const wsUrl = `ws://localhost:8000/api/v1/enrichment-viewer/ws/${workflowId}`
    console.log('🔗 Connecting to enrichment viewer:', wsUrl, 'at', new Date().toLocaleTimeString())
    
    try {
      // Close any existing connection first
      if (websocketRef.current) {
        websocketRef.current.close()
      }
      
      websocketRef.current = new WebSocket(wsUrl)
      
      websocketRef.current.onopen = () => {
        console.log('✅ Enrichment viewer WebSocket connected successfully')
        setIsConnected(true)
        setStatus('connected')
        
        // Clear any reconnection timeout
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
          reconnectTimeoutRef.current = null
        }
        
        // Notify parent component
        onStatusChange?.({
          isConnected: true,
          currentStep,
          reasoning: aiReasoning
        })
      }
      
      websocketRef.current.onmessage = (event) => {
        try {
          const update: EnrichmentUpdate = JSON.parse(event.data)
          console.log('Enrichment update received:', update)
          
          // Handle ping/pong to keep connection alive
          if (update.type === 'ping') {
            websocketRef.current?.send(JSON.stringify({ type: 'pong' }))
            return
          }
          
          if (update.type === 'enrichment_update') {
            setCurrentStep(update.step)
            setAiReasoning(update.reasoning)
            setStatus(update.status)
            
            if (update.data) {
              setEnrichmentData(update.data)
            }
            
            // Notify parent component
            onStatusChange?.({
              isConnected: true,
              currentStep: update.step,
              reasoning: update.reasoning
            })
          }
        } catch (error) {
          console.error('Failed to parse enrichment update:', error)
        }
      }
      
      websocketRef.current.onclose = (event) => {
        console.log('Enrichment viewer disconnected:', event.code, event.reason)
        setIsConnected(false)
        setStatus('disconnected')
        
        // Notify parent component
        onStatusChange?.({
          isConnected: false,
          currentStep: 'Disconnected',
          reasoning: 'Connection lost'
        })
        
        // Attempt to reconnect quickly if not manually closed
        if (event.code !== 1000) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting to reconnect enrichment viewer...')
            connect()
          }, 1000) // Reduced from 3000ms to 1000ms for faster reconnection
        }
      }
      
      websocketRef.current.onerror = (error) => {
        console.error('❌ Enrichment viewer WebSocket error:', error)
        console.error('❌ Failed WebSocket URL was:', wsUrl)
        setStatus('error')
      }
      
    } catch (error) {
      console.error('❌ Failed to create enrichment viewer WebSocket:', error)
      console.error('❌ URL that failed:', wsUrl)
      setStatus('error')
    }
  }

  const cleanup = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    
    if (websocketRef.current) {
      websocketRef.current.close(1000, 'Component unmounting')
      websocketRef.current = null
    }
  }

  return (
    <div className={`bg-white border-2 border-black rounded-lg overflow-hidden ${className}`}>
      {/* Main content area matching BrowserViewer height */}
      <div className="relative bg-white h-72 p-4">
        {/* AI Reasoning Display */}
        <div className="space-y-2">
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">AI Analysis</div>
          <div className="text-sm text-black min-h-[3rem] transition-opacity duration-300 relative overflow-hidden">
            <div className="relative z-0 whitespace-pre-wrap">
              {aiReasoning}
            </div>
            
            {/* Shimmer effect when active - matching BrowserViewer */}
            {status === 'active' && (
              <div className="absolute inset-0 pointer-events-none z-10">
                <div className="absolute inset-0 w-24 h-full shimmer-animation" 
                     style={{
                       background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.1) 20%, rgba(255,255,255,0.8) 50%, rgba(255,255,255,0.1) 80%, transparent 100%)',
                       boxShadow: '0 0 10px rgba(255,255,255,0.3)'
                     }}>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Clean insights and sources */}
        {enrichmentData && (
          <div className="mt-4 space-y-3">
            {/* Key insights in a clean grid */}
            <div className="grid grid-cols-2 gap-3 text-sm">
              {enrichmentData.profile_summary && enrichmentData.profile_summary.role && (
                <div>
                  <div className="text-xs text-gray-400 mb-1">Role</div>
                  <div className="text-black font-medium">{enrichmentData.profile_summary.role}</div>
                </div>
              )}
              {enrichmentData.profile_summary && enrichmentData.profile_summary.industry && (
                <div>
                  <div className="text-xs text-gray-400 mb-1">Industry</div>
                  <div className="text-black font-medium">{enrichmentData.profile_summary.industry}</div>
                </div>
              )}
              {enrichmentData.profile_summary && enrichmentData.profile_summary.event_type && (
                <div>
                  <div className="text-xs text-gray-400 mb-1">Events</div>
                  <div className="text-black font-medium">{enrichmentData.profile_summary.event_type}</div>
                </div>
              )}
              {enrichmentData.profile_summary && enrichmentData.profile_summary.budget_indicators && (
                <div>
                  <div className="text-xs text-gray-400 mb-1">Budget</div>
                  <div className="text-black font-medium">{enrichmentData.profile_summary.budget_indicators.substring(0, 40)}...</div>
                </div>
              )}
            </div>
            
            {/* Clean citations - no scrollbar, just show top sources */}
            {enrichmentData.citations && enrichmentData.citations.length > 0 && (
              <div className="pt-2 border-t border-gray-100">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs text-gray-400">Sources ({enrichmentData.citations.length})</span>
                </div>
                <div className="space-y-2">
                  {enrichmentData.citations.slice(0, 2).map((citation: any, index: number) => (
                    <a key={index} 
                       href={citation.url} 
                       target="_blank" 
                       rel="noopener noreferrer" 
                       className="block p-2 rounded-md bg-gray-50 hover:bg-gray-100 transition-colors group">
                      <div className="text-xs font-medium text-black group-hover:text-blue-600 truncate">
                        {citation.title || 'Research Source'}
                      </div>
                      <div className="text-xs text-gray-500 mt-1 truncate">
                        {new URL(citation.url).hostname}
                      </div>
                    </a>
                  ))}
                  {enrichmentData.citations.length > 2 && (
                    <div className="text-center">
                      <span className="text-xs text-gray-400">
                        +{enrichmentData.citations.length - 2} more sources
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Progress indicator - minimal design */}
        {status === 'active' && (
          <div className="absolute bottom-4 left-4 flex items-center space-x-2">
            <div className="w-4 h-4 border-2 border-gray-400 border-t-black rounded-full animate-spin"></div>
            <span className="text-xs text-gray-600">Processing...</span>
          </div>
        )}

        {/* Completion indicator */}
        {status === 'complete' && (
          <div className="absolute bottom-4 left-4 flex items-center space-x-2">
            <div className="w-4 h-4 bg-black rounded-full flex items-center justify-center">
              <svg className="w-2 h-2 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <span className="text-xs text-black font-medium">Complete</span>
          </div>
        )}
      </div>
    </div>
  )
}