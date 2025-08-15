import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { PlanningResponse } from '@/services/campaignPlanningService'

interface PlanningMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  clarifications_needed?: string[]
  suggested_responses?: string[]
}

interface ChatState {
  // Planning conversation state
  messages: PlanningMessage[]
  conversationId: string | null
  planningResponse: PlanningResponse | null
  hasWorkflow: boolean
  wsConnection: WebSocket | null
  
  // Actions
  setMessages: (messages: PlanningMessage[]) => void
  addMessage: (message: PlanningMessage) => void
  setConversationId: (id: string | null) => void
  setPlanningResponse: (response: PlanningResponse | null) => void
  setHasWorkflow: (hasWorkflow: boolean) => void
  setWsConnection: (connection: WebSocket | null) => void
  clearChat: () => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      // Initial state
      messages: [],
      conversationId: null,
      planningResponse: null,
      hasWorkflow: false,
      wsConnection: null,
      
      // Actions
      setMessages: (messages) => set({ messages }),
      
      addMessage: (message) => set((state) => ({
        messages: [...state.messages, message]
      })),
      
      setConversationId: (conversationId) => set({ conversationId }),
      
      setPlanningResponse: (planningResponse) => set({ planningResponse }),
      
      setHasWorkflow: (hasWorkflow) => set({ hasWorkflow }),
      
      setWsConnection: (wsConnection) => {
        // Don't persist WebSocket connections
        set({ wsConnection })
      },
      
      clearChat: () => set({
        messages: [],
        conversationId: null,
        planningResponse: null,
        hasWorkflow: false,
        wsConnection: null
      })
    }),
    {
      name: 'chat-storage',
      // Don't persist WebSocket connection
      partialize: (state) => ({
        messages: state.messages,
        conversationId: state.conversationId,
        planningResponse: state.planningResponse,
        hasWorkflow: state.hasWorkflow
      })
    }
  )
)