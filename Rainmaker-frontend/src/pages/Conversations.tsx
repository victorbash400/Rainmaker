import { MessageSquare, Bot, User, Clock, TrendingUp } from 'lucide-react'

// Mock conversation data
const conversations = [
  {
    id: 1,
    prospect: 'Sarah Johnson',
    company: 'Tech Corp',
    lastMessage: 'That sounds perfect! Can you send me a detailed proposal?',
    timestamp: '2 minutes ago',
    status: 'active',
    messageCount: 8,
    sentiment: 'positive',
    qualification: 85,
    channel: 'email'
  },
  {
    id: 2,
    prospect: 'Mike Chen', 
    company: 'Startup Inc',
    lastMessage: 'AI Agent: I\'ve sent over some initial venue options...',
    timestamp: '1 hour ago',
    status: 'waiting',
    messageCount: 12,
    sentiment: 'neutral',
    qualification: 72,
    channel: 'linkedin'
  },
  {
    id: 3,
    prospect: 'Emily Rodriguez',
    company: 'Personal',
    lastMessage: 'What\'s your availability for a call next week?',
    timestamp: '3 hours ago',
    status: 'active',
    messageCount: 5,
    sentiment: 'positive',
    qualification: 90,
    channel: 'email'
  },
]

export default function Conversations() {
  return (
    <div className="h-screen bg-white">
      <div className="max-w-4xl mx-auto px-6 py-6">
        <div className="space-y-8">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-black">Conversations</h1>
              <p className="mt-1 text-gray-500">
                AI-powered prospect conversations and requirement extraction
              </p>
            </div>
            <button className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors duration-200">
              <Bot className="h-4 w-4" />
              <span className="text-sm font-medium">AI Overview</span>
            </button>
          </div>

          {/* Conversations List */}
          <div className="space-y-4">
            {conversations.map((conversation) => (
              <div key={conversation.id} className="border border-gray-200 rounded-xl bg-white p-6 hover:border-gray-300 transition-colors cursor-pointer">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-start space-x-4">
                    <div className={`w-3 h-3 rounded-full mt-2 ${
                      conversation.status === 'active' ? 'bg-black animate-pulse' : 'bg-gray-300'
                    }`}></div>
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <h3 className="font-medium text-black">{conversation.prospect}</h3>
                        <span className="text-sm text-gray-500">{conversation.company}</span>
                        <span className="text-xs text-gray-400">• {conversation.channel}</span>
                      </div>
                      <p className="text-sm text-gray-600 mb-3">{conversation.lastMessage}</p>
                      <div className="flex items-center space-x-4 text-xs text-gray-400">
                        <span className="flex items-center space-x-1">
                          <MessageSquare className="h-3 w-3" />
                          <span>{conversation.messageCount} messages</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <TrendingUp className="h-3 w-3" />
                          <span>{conversation.qualification}% qualified</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <Clock className="h-3 w-3" />
                          <span>{conversation.timestamp}</span>
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                      conversation.sentiment === 'positive' ? 'bg-gray-100 text-black' :
                      conversation.sentiment === 'negative' ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {conversation.sentiment}
                    </span>
                    {conversation.status === 'active' && <div className="w-4 h-4 border-2 border-gray-400 border-t-black rounded-full animate-spin"></div>}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* AI Summary Card */}
          <div className="border border-gray-200 rounded-xl bg-white p-6">
            <div className="flex items-start space-x-4">
              <Bot className="h-5 w-5 text-gray-400 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-medium text-black mb-3">AI Conversation Summary</h3>
                <div className="text-sm text-gray-600 space-y-1">
                  <p>• 3 active conversations with high engagement</p>
                  <p>• Average qualification score: 82%</p>
                  <p>• 2 prospects ready for proposal stage</p>
                  <p>• 1 conversation needs human review</p>
                </div>
              </div>
            </div>
          </div>

          {/* Empty State */}
          {conversations.length === 0 && (
            <div className="text-center py-12">
              <MessageSquare className="h-12 w-12 mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-black mb-2">No conversations yet</h3>
              <p className="text-gray-500 mb-6">
                Conversations start when prospects respond to outreach campaigns
              </p>
              <button className="flex items-center space-x-2 px-4 py-2 bg-black text-white hover:bg-gray-900 rounded-lg transition-colors duration-200 mx-auto">
                <Bot className="h-4 w-4" />
                <span className="text-sm font-medium">Start Outreach Campaign</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}