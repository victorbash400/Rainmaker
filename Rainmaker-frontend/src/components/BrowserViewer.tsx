import { useState, useEffect, useRef } from 'react'

interface BrowserViewerProps {
  workflowId: string
  className?: string
  onStatusChange?: (status: {
    isConnected: boolean
    currentStep: string
    currentUrl: string
  }) => void
}

interface BrowserUpdate {
  workflow_id: string
  step: string
  details: string
  url: string
  title: string
  screenshot: string
  timestamp: string
  status: string
  reasoning?: string  // AI thought process
}

export default function BrowserViewer({ workflowId, className = "", onStatusChange }: BrowserViewerProps) {
  const [isConnected, setIsConnected] = useState(false)
  const [screenshot, setScreenshot] = useState<string | null>(null)
  const [currentStep, setCurrentStep] = useState('Initializing browser...')
  const [currentUrl, setCurrentUrl] = useState('')
  const [aiReasoning, setAiReasoning] = useState<string | null>(null)
  const [isLoginPause, setIsLoginPause] = useState(false)
  
  const websocketRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    connect()
    return () => cleanup()
  }, [workflowId])

  const connect = () => {
    if (websocketRef.current?.readyState === WebSocket.OPEN) return

    const wsUrl = `ws://localhost:8000/api/v1/browser-viewer/ws/${workflowId}`
    console.log('Connecting to:', wsUrl)
    
    try {
      websocketRef.current = new WebSocket(wsUrl)
      
      websocketRef.current.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        
        // Clear any reconnect timeout
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
          reconnectTimeoutRef.current = null
        }
      }
      
      websocketRef.current.onmessage = (event) => {
        try {
          console.log('Received WebSocket message:', event.data)
          const message = JSON.parse(event.data)
          
          // Handle ping/pong to keep connection alive
          if (message.type === 'ping') {
            websocketRef.current?.send(JSON.stringify({ type: 'pong' }))
            return
          }
          
          // Handle different message types
          if (message.type === 'browser_update' && message.data) {
            handleBrowserUpdate(message.data)
          } else if (message.workflow_id) {
            // Direct browser update
            handleBrowserUpdate(message)
          }
        } catch (error) {
          console.error('Failed to parse browser update:', error)
        }
      }
      
      websocketRef.current.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason)
        setIsConnected(false)
        
        // Only reconnect if not manually closed (code 1000)
        if (event.code !== 1000 && !reconnectTimeoutRef.current) {
          reconnectTimeoutRef.current = setTimeout(connect, 2000)
        }
      }
      
      websocketRef.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        setIsConnected(false)
      }
      
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
    }
  }

  const cleanup = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
      websocketRef.current.close(1000, 'Component unmounting')
      websocketRef.current = null
    }
    setIsConnected(false)
  }

  const handleBrowserUpdate = (data: BrowserUpdate) => {
    console.log('Processing browser update:', {
      step: data.step,
      url: data.url,
      hasScreenshot: !!data.screenshot,
      screenshotLength: data.screenshot?.length,
      hasReasoning: !!data.reasoning
    })
    
    if (data.step) setCurrentStep(data.step)
    if (data.url && data.url !== 'about:blank') setCurrentUrl(data.url)
    if (data.screenshot) {
      console.log('Setting screenshot, length:', data.screenshot.length)
      setScreenshot(data.screenshot)
    }
    
    // Check for login pause states
    const isLoginStep = data.step && (
      data.step.includes('Login Required') ||
      data.step.includes('Waiting for Login') ||
      data.step.includes('Login Successful')
    )
    
    setIsLoginPause(isLoginStep || false)
    
    // Update AI reasoning if provided - this replaces the previous thought
    if (data.reasoning) {
      setAiReasoning(data.reasoning)
    }

    // Notify parent of status changes
    onStatusChange?.({
      isConnected,
      currentStep: data.step || currentStep,
      currentUrl: data.url || currentUrl
    })
  }

  return (
    <div className={`bg-white border-2 ${isLoginPause ? 'border-blue-500' : 'border-black'} rounded-lg overflow-hidden ${className}`}>
      {/* Login pause indicator */}
      {isLoginPause && (
        <div className="bg-blue-50 border-b border-blue-200 px-3 py-2">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
            <span className="text-xs text-blue-700 font-medium">Manual Login Required</span>
          </div>
        </div>
      )}
      
      {/* Pure browser viewport - just the screenshot */}
      <div className="relative bg-white h-72">
        {screenshot ? (
          <img 
            src={`data:image/png;base64,${screenshot}`}
            alt="Browser automation"
            className="w-full h-full object-contain bg-gray-50"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gray-50">
            <div className="text-center">
              <div className="w-8 h-8 border-2 border-gray-300 border-t-black rounded-full animate-spin mx-auto mb-3"></div>
              <div className="text-sm text-gray-600">Loading browser...</div>
            </div>
          </div>
        )}
        
        {/* Login overlay when paused */}
        {isLoginPause && (
          <div className="absolute inset-0 bg-blue-500 bg-opacity-10 flex items-center justify-center">
            <div className="bg-white rounded-lg px-4 py-3 shadow-lg border border-blue-200">
              <div className="flex items-center space-x-2">
                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                <span className="text-sm font-medium text-blue-900">Login Required</span>
              </div>
              <p className="text-xs text-blue-700 mt-1">Complete login in browser to continue</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}