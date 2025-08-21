import { MessageSquare, Bot, User, Clock, TrendingUp, Mail, Loader2, AlertTriangle } from 'lucide-react'
import { useState, useEffect } from 'react'

interface EmailMessage {
  id: number;
  workflow_id: string;
  sender_email: string;
  recipient_email: string;
  subject: string;
  body: string;
  direction: 'sent' | 'received';
  message_type: 'outreach' | 'follow_up' | 'calendar_invite' | 'reply' | 'overview_request';
  timestamp: string;
}

interface Conversation {
  workflow_id: string;
  prospect_name?: string;
  prospect_email: string;
  prospect_company?: string;
  message_count: number;
  last_message: string;
  last_timestamp: string;
  status: 'active' | 'waiting' | 'completed';
  messages: EmailMessage[];
}

export default function Conversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/conversations/', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to load conversations');
      }

      const data = await response.json();
      setConversations(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load conversations:', err);
      setError(err instanceof Error ? err.message : 'Failed to load conversations');
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return 'now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const getMessageTypeIcon = (type: string, direction: string) => {
    if (direction === 'received') return <User className="h-3 w-3" />;
    
    switch (type) {
      case 'outreach':
        return <Mail className="h-3 w-3" />;
      case 'follow_up':
        return <MessageSquare className="h-3 w-3" />;
      case 'calendar_invite':
        return <Clock className="h-3 w-3" />;
      default:
        return <Bot className="h-3 w-3" />;
    }
  };

  if (loading) {
    return (
      <div className="h-screen bg-white">
        <div className="max-w-4xl mx-auto px-6 py-6">
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-semibold text-black">Conversations</h1>
                <p className="mt-1 text-gray-500">
                  AI-powered prospect conversations and email tracking
                </p>
              </div>
            </div>
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-gray-600" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen bg-white">
        <div className="max-w-4xl mx-auto px-6 py-6">
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-semibold text-black">Conversations</h1>
                <p className="mt-1 text-gray-500">
                  AI-powered prospect conversations and email tracking
                </p>
              </div>
            </div>
            <div className="text-center py-12">
              <AlertTriangle className="h-12 w-12 mx-auto text-red-400 mb-4" />
              <h3 className="text-lg font-medium text-red-900">Error loading conversations</h3>
              <p className="text-red-600 mb-4">{error}</p>
              <button 
                onClick={loadConversations}
                className="px-4 py-2 bg-black text-white hover:bg-gray-900 rounded-lg transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-white">
      <div className="max-w-6xl mx-auto px-6 py-6">
        <div className="space-y-8">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-black">Conversations</h1>
              <p className="mt-1 text-gray-500">
                Email conversations tracked per workflow
              </p>
            </div>
            <button 
              onClick={loadConversations}
              className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors duration-200"
            >
              <MessageSquare className="h-4 w-4" />
              <span className="text-sm font-medium">Refresh</span>
            </button>
          </div>

          {conversations.length === 0 ? (
            /* Empty State */
            <div className="text-center py-12">
              <MessageSquare className="h-12 w-12 mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-black mb-2">No conversations yet</h3>
              <p className="text-gray-500 mb-6">
                Email conversations will appear here once workflows start sending outreach
              </p>
              <button className="flex items-center space-x-2 px-4 py-2 bg-black text-white hover:bg-gray-900 rounded-lg transition-colors duration-200 mx-auto">
                <Bot className="h-4 w-4" />
                <span className="text-sm font-medium">Start New Workflow</span>
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Conversations List */}
              <div className="space-y-4">
                <h2 className="text-lg font-medium text-black">Active Conversations</h2>
                {conversations.map((conversation) => (
                  <div 
                    key={conversation.workflow_id} 
                    className={`border border-gray-200 rounded-xl bg-white p-4 hover:border-gray-300 transition-colors cursor-pointer ${
                      selectedConversation?.workflow_id === conversation.workflow_id ? 'border-black bg-gray-50' : ''
                    }`}
                    onClick={() => setSelectedConversation(conversation)}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-start space-x-3">
                        <div className={`w-3 h-3 rounded-full mt-1.5 ${
                          conversation.status === 'active' ? 'bg-green-400 animate-pulse' : 
                          conversation.status === 'completed' ? 'bg-gray-400' : 'bg-yellow-400'
                        }`}></div>
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-1">
                            <h3 className="font-medium text-black">
                              {conversation.prospect_name || conversation.prospect_email}
                            </h3>
                            {conversation.prospect_company && (
                              <span className="text-sm text-gray-500">• {conversation.prospect_company}</span>
                            )}
                          </div>
                          <p className="text-sm text-gray-600 mb-2 line-clamp-2">{conversation.last_message}</p>
                          <div className="flex items-center space-x-3 text-xs text-gray-400">
                            <span className="flex items-center space-x-1">
                              <MessageSquare className="h-3 w-3" />
                              <span>{conversation.message_count} messages</span>
                            </span>
                            <span className="flex items-center space-x-1">
                              <Clock className="h-3 w-3" />
                              <span>{formatTimestamp(conversation.last_timestamp)}</span>
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        conversation.status === 'active' ? 'bg-green-100 text-green-800' :
                        conversation.status === 'completed' ? 'bg-gray-100 text-gray-800' : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {conversation.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Conversation Detail */}
              <div className="border border-gray-200 rounded-xl bg-white">
                {selectedConversation ? (
                  <div className="p-6">
                    <div className="mb-6">
                      <h3 className="text-lg font-medium text-black mb-1">
                        {selectedConversation.prospect_name || selectedConversation.prospect_email}
                      </h3>
                      <p className="text-sm text-gray-500">
                        Workflow: {selectedConversation.workflow_id.slice(0, 12)}...
                      </p>
                    </div>

                    <div className="space-y-4 max-h-96 overflow-y-auto">
                      {selectedConversation.messages.map((message, index) => (
                        <div key={message.id} className={`flex ${message.direction === 'sent' ? 'justify-end' : 'justify-start'}`}>
                          <div className={`max-w-xs lg:max-w-md px-3 py-2 rounded-lg ${
                            message.direction === 'sent' 
                              ? 'bg-black text-white' 
                              : 'bg-gray-100 text-gray-900'
                          }`}>
                            <div className="flex items-center space-x-1 mb-1">
                              {getMessageTypeIcon(message.message_type, message.direction)}
                              <span className="text-xs opacity-75 capitalize">
                                {message.message_type}
                              </span>
                              <span className="text-xs opacity-75">•</span>
                              <span className="text-xs opacity-75">
                                {formatTimestamp(message.timestamp)}
                              </span>
                            </div>
                            <p className="text-sm font-medium mb-1">{message.subject}</p>
                            <p className="text-xs opacity-90 line-clamp-3">
                              {message.body.substring(0, 150)}
                              {message.body.length > 150 && '...'}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="p-6 text-center">
                    <MessageSquare className="h-12 w-12 mx-auto text-gray-300 mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Select a conversation</h3>
                    <p className="text-gray-500">
                      Choose a conversation from the list to view the email thread
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}