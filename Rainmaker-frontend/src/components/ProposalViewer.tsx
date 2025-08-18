import { useState, useEffect } from 'react'
import { CheckCircle, Clock, FileText, Send, Eye, Download, AlertTriangle, Calendar } from 'lucide-react'
import { motion } from 'framer-motion'

interface ProposalViewerProps {
  workflowId: string
  onComplete?: () => void
}

interface ProposalStatus {
  workflow_id: string
  current_stage: string
  has_proposal: boolean
  proposal_id?: string
  client_company?: string
  event_type?: string
  total_investment?: number
  pdf_file_path?: string
  generated_at?: string
  valid_until?: string
  status: 'not_generated' | 'generating' | 'generated' | 'sent'
  can_generate: boolean
  can_send: boolean
}

type ProposalStage = 
  | 'not_generated'
  | 'generating'
  | 'generated'
  | 'reviewing'
  | 'sending'
  | 'sent'
  | 'awaiting_meeting'

export default function ProposalViewer({ workflowId, onComplete }: ProposalViewerProps) {
  const [proposalStage, setProposalStage] = useState<ProposalStage>('not_generated')
  const [proposalStatus, setProposalStatus] = useState<ProposalStatus | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showReviewModal, setShowReviewModal] = useState(false)
  const [showSuccessModal, setShowSuccessModal] = useState(false)

  useEffect(() => {
    loadProposalStatus()
    const interval = setInterval(loadProposalStatus, 5000) // Check every 5 seconds
    return () => clearInterval(interval)
  }, [workflowId])

  const loadProposalStatus = async () => {
    try {
      const response = await fetch(`/api/v1/workflow-proposals/${workflowId}/status`)
      if (!response.ok) throw new Error('Failed to load proposal status')
      
      const data = await response.json()
      setProposalStatus(data)
      
      // Set stage based on status
      if (!data.has_proposal && data.can_generate) {
        setProposalStage('not_generated')
      } else if (data.has_proposal && data.status === 'generated') {
        setProposalStage('generated')
      } else if (data.has_proposal && data.status === 'sent') {
        setProposalStage('sent')
      }
    } catch (err) {
      console.error('Failed to load proposal status:', err)
      setError('Failed to load proposal status')
    }
  }

  const handleGenerateProposal = async () => {
    setIsLoading(true)
    setProposalStage('generating')
    setError(null)

    try {
      const response = await fetch(`/api/v1/workflow-proposals/${workflowId}/generate`, {
        method: 'POST'
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to generate proposal')
      }

      const result = await response.json()
      setProposalStage('generated')
      await loadProposalStatus() // Refresh status
      
      // Show success modal after generation
      setShowSuccessModal(true)
    } catch (err) {
      console.error('Failed to generate proposal:', err)
      setError(err instanceof Error ? err.message : 'Failed to generate proposal')
      setProposalStage('not_generated')
    } finally {
      setIsLoading(false)
    }
  }

  const handleReviewProposal = () => {
    setShowReviewModal(true)
  }

  const handleSendProposal = async () => {
    setIsLoading(true)
    setProposalStage('sending')
    setError(null)

    try {
      const response = await fetch(`/api/v1/workflow-proposals/${workflowId}/send`, {
        method: 'POST'
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to send proposal')
      }

      const result = await response.json()
      setProposalStage('sent')
      await loadProposalStatus() // Refresh status
      
      // Auto-advance to meeting response checking after a delay
      setTimeout(() => {
        setProposalStage('awaiting_meeting')
      }, 2000)
    } catch (err) {
      console.error('Failed to send proposal:', err)
      setError(err instanceof Error ? err.message : 'Failed to send proposal')
      setProposalStage('generated')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCheckMeetingResponse = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/v1/workflow-proposals/${workflowId}/check-meeting-response`, {
        method: 'POST'
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to check meeting response')
      }

      const result = await response.json()
      if (result.status === 'no_reply_found') {
        // No reply yet, keep checking
        setError(null)
      } else if (result.status === 'meeting_response_received') {
        if (result.wants_meeting) {
          // Success! Meeting requested
          if (onComplete) onComplete()
        } else {
          setError('Prospect declined meeting request')
        }
      }
    } catch (err) {
      console.error('Failed to check meeting response:', err)
      setError(err instanceof Error ? err.message : 'Failed to check meeting response')
    } finally {
      setIsLoading(false)
    }
  }

  const getStageIcon = (stage: ProposalStage) => {
    switch (stage) {
      case 'not_generated':
        return <FileText className="h-8 w-8 text-gray-400" />
      case 'generating':
        return <div className="w-8 h-8 border-2 border-gray-400 border-t-black rounded-full animate-spin" />
      case 'generated':
      case 'reviewing':
        return <FileText className="h-8 w-8 text-black" />
      case 'sending':
        return <div className="w-8 h-8 border-2 border-gray-400 border-t-black rounded-full animate-spin" />
      case 'sent':
        return <Send className="h-8 w-8 text-green-600" />
      case 'awaiting_meeting':
        return <Calendar className="h-8 w-8 text-blue-600" />
      default:
        return <FileText className="h-8 w-8 text-gray-400" />
    }
  }

  const getStageTitle = (stage: ProposalStage) => {
    switch (stage) {
      case 'not_generated':
        return 'Generate Proposal'
      case 'generating':
        return 'Generating Proposal...'
      case 'generated':
        return 'Proposal Ready'
      case 'reviewing':
        return 'Reviewing Proposal'
      case 'sending':
        return 'Sending Proposal...'
      case 'sent':
        return 'Proposal Sent'
      case 'awaiting_meeting':
        return 'Awaiting Meeting Response'
      default:
        return 'Proposal'
    }
  }

  const getStageDescription = (stage: ProposalStage) => {
    switch (stage) {
      case 'not_generated':
        return 'Ready to generate a customized proposal based on the event overview'
      case 'generating':
        return 'AI is creating a professional proposal with pricing and details...'
      case 'generated':
        return 'Proposal generated successfully. Review before sending to client.'
      case 'reviewing':
        return 'Reviewing the generated proposal document'
      case 'sending':
        return 'Sending proposal email with PDF attachment to the client...'
      case 'sent':
        return 'Proposal has been sent to the client with meeting request'
      case 'awaiting_meeting':
        return 'Waiting for client response to schedule a meeting'
      default:
        return ''
    }
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 min-h-[400px]">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="w-6 h-6 flex items-center justify-center">
            {getStageIcon(proposalStage)}
          </div>
          <span className="text-sm font-medium text-black">📊 AI Proposal Generation</span>
        </div>
      </div>

      <div className="space-y-6">
        {/* Stage Header */}
        <div className="text-center">
          <motion.div 
            className="mx-auto mb-4 w-16 h-16 flex items-center justify-center"
            animate={{ 
              scale: proposalStage === 'generating' || proposalStage === 'sending' ? [1, 1.1, 1] : 1 
            }}
            transition={{ 
              duration: 1.5, 
              repeat: proposalStage === 'generating' || proposalStage === 'sending' ? Infinity : 0,
              ease: "easeInOut" 
            }}
          >
            {getStageIcon(proposalStage)}
          </motion.div>
          <h3 className="text-xl font-semibold text-black mb-2">
            {getStageTitle(proposalStage)}
          </h3>
          <p className="text-gray-600 max-w-md mx-auto">
            {getStageDescription(proposalStage)}
          </p>
        </div>

        {/* Proposal Details */}
        {proposalStatus?.has_proposal && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gray-50 rounded-lg p-4 space-y-3"
          >
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Client:</span>
                <div className="font-medium">{proposalStatus.client_company}</div>
              </div>
              <div>
                <span className="text-gray-500">Event Type:</span>
                <div className="font-medium">{proposalStatus.event_type}</div>
              </div>
              <div>
                <span className="text-gray-500">Investment:</span>
                <div className="font-medium">${proposalStatus.total_investment?.toLocaleString()}</div>
              </div>
              <div>
                <span className="text-gray-500">Generated:</span>
                <div className="font-medium">
                  {proposalStatus.generated_at ? new Date(proposalStatus.generated_at).toLocaleDateString() : 'N/A'}
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Error Display */}
        {error && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-center space-x-2"
          >
            <AlertTriangle className="h-4 w-4 text-red-600" />
            <span className="text-sm text-red-700">{error}</span>
          </motion.div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-center space-x-3">
          {proposalStage === 'not_generated' && (
            <button
              onClick={handleGenerateProposal}
              disabled={isLoading || !proposalStatus?.can_generate}
              className="flex items-center space-x-2 px-6 py-3 bg-black hover:bg-gray-900 text-white rounded-lg transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <FileText className="h-4 w-4" />
              <span>Generate Proposal</span>
            </button>
          )}

          {proposalStage === 'generated' && (
            <>
              <button
                onClick={handleReviewProposal}
                className="flex items-center space-x-2 px-4 py-2 border border-gray-300 hover:bg-gray-50 rounded-lg transition-colors duration-200"
              >
                <Eye className="h-4 w-4" />
                <span>Review</span>
              </button>
              <button
                onClick={handleSendProposal}
                disabled={isLoading}
                className="flex items-center space-x-2 px-6 py-3 bg-black hover:bg-gray-900 text-white rounded-lg transition-colors duration-200 disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
                <span>Send to Client</span>
              </button>
            </>
          )}

          {proposalStage === 'awaiting_meeting' && (
            <button
              onClick={handleCheckMeetingResponse}
              disabled={isLoading}
              className="flex items-center space-x-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors duration-200 disabled:opacity-50"
            >
              <Calendar className="h-4 w-4" />
              <span>Check for Meeting Response</span>
            </button>
          )}
        </div>

        {/* Loading States */}
        {(proposalStage === 'generating' || proposalStage === 'sending') && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-4"
          >
            <div className="flex items-center justify-center space-x-2 text-sm text-gray-600">
              <div className="w-4 h-4 border-2 border-gray-400 border-t-black rounded-full animate-spin"></div>
              <span>
                {proposalStage === 'generating' ? 'AI is analyzing event details and creating your proposal...' : 'Sending proposal to client...'}
              </span>
            </div>
          </motion.div>
        )}
      </div>

      {/* Success Modal */}
      {showSuccessModal && (
        <SuccessModal
          proposalData={proposalStatus}
          onClose={() => setShowSuccessModal(false)}
          onReview={() => {
            setShowSuccessModal(false)
            setShowReviewModal(true)
          }}
          onSend={() => {
            setShowSuccessModal(false)
            handleSendProposal()
          }}
        />
      )}

      {/* Review Modal */}
      {showReviewModal && (
        <ReviewModal
          proposalData={proposalStatus}
          onClose={() => setShowReviewModal(false)}
          onSend={handleSendProposal}
        />
      )}
    </div>
  )
}

// Review Modal Component
function ReviewModal({ 
  proposalData, 
  onClose, 
  onSend 
}: { 
  proposalData: ProposalStatus | null
  onClose: () => void
  onSend: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center">
        {/* Backdrop */}
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
          onClick={onClose}
        />
        
        {/* Modal */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="relative bg-white rounded-xl shadow-xl max-w-4xl w-full mx-4 h-[85vh] flex flex-col"
        >
          <div className="bg-white px-6 pt-6 pb-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Review Proposal
              </h3>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>

            <div className="space-y-4 max-h-96 overflow-y-auto">
              {/* Proposal Summary */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-3">Proposal Summary</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Client Company:</span>
                    <div className="font-medium">{proposalData?.client_company}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">Event Type:</span>
                    <div className="font-medium">{proposalData?.event_type}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">Total Investment:</span>
                    <div className="font-medium">${proposalData?.total_investment?.toLocaleString()}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">Proposal ID:</span>
                    <div className="font-medium">{proposalData?.proposal_id}</div>
                  </div>
                </div>
              </div>

              {/* PDF Viewer */}
              <div className="border border-gray-200 rounded-lg overflow-hidden" style={{ height: '400px' }}>
                {proposalData?.pdf_file_path ? (
                  <iframe
                    src={`/api/proposals/view/${proposalData.proposal_id}`}
                    className="w-full h-full border-0"
                    title="Proposal PDF"
                  />
                ) : (
                  <div className="flex items-center justify-center h-full bg-gray-50">
                    <div className="text-center">
                      <FileText className="h-12 w-12 text-gray-400 mx-auto mb-2" />
                      <p className="text-gray-600">PDF not available for preview</p>
                      <a 
                        href={`/api/proposals/download/${proposalData?.proposal_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center space-x-2 text-blue-600 hover:text-blue-700 mt-2"
                      >
                        <Download className="h-4 w-4" />
                        <span>Download PDF</span>
                      </a>
                    </div>
                  </div>
                )}
              </div>

              {/* Next Steps */}
              <div className="bg-blue-50 rounded-lg p-4">
                <h4 className="font-medium text-blue-900 mb-2">What happens next?</h4>
                <ul className="text-sm text-blue-800 space-y-1">
                  <li>• Proposal PDF will be attached to the email</li>
                  <li>• Client will receive a professional cover email</li>
                  <li>• Meeting request will be included in the email</li>
                  <li>• You'll be notified when client responds</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="bg-gray-50 px-6 py-3 flex justify-end space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                onSend()
                onClose()
              }}
              className="px-6 py-2 bg-black text-white rounded-lg hover:bg-gray-900 transition-colors"
            >
              Send to Client
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

// Success Modal Component
function SuccessModal({ 
  proposalData, 
  onClose, 
  onReview,
  onSend 
}: { 
  proposalData: ProposalStatus | null
  onClose: () => void
  onReview: () => void
  onSend: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center">
        {/* Backdrop */}
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
          onClick={onClose}
        />
        
        {/* Modal */}
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="relative bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6"
        >
          {/* Success Animation */}
          <div className="text-center mb-6">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ 
                type: "spring", 
                damping: 15, 
                stiffness: 300,
                delay: 0.2 
              }}
              className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4"
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.4, type: "spring", damping: 10 }}
              >
                <CheckCircle className="w-8 h-8 text-gray-600" />
              </motion.div>
            </motion.div>
            
            <motion.h3 
              className="text-xl font-semibold text-gray-900 mb-2"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
            >
              Proposal Generated Successfully
            </motion.h3>
            
            <motion.p 
              className="text-gray-600"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8 }}
            >
              Your professional proposal is ready for {proposalData?.client_company}
            </motion.p>
          </div>

          {/* Proposal Summary */}
          {proposalData && (
            <motion.div 
              className="bg-gray-50 rounded-lg p-4 mb-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1 }}
            >
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-gray-500">Event:</span>
                  <div className="font-medium">{proposalData.event_type}</div>
                </div>
                <div>
                  <span className="text-gray-500">Investment:</span>
                  <div className="font-medium">${proposalData.total_investment?.toLocaleString()}</div>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-gray-200">
                <span className="text-gray-500 text-xs">Proposal ID:</span>
                <div className="font-mono text-xs text-gray-700">{proposalData.proposal_id}</div>
              </div>
            </motion.div>
          )}

          {/* Action Buttons */}
          <motion.div 
            className="flex space-x-3"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.2 }}
          >
            <button
              onClick={onReview}
              className="flex-1 flex items-center justify-center space-x-2 px-4 py-3 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <Eye className="h-4 w-4" />
              <span>Review</span>
            </button>
            <button
              onClick={onSend}
              className="flex-1 flex items-center justify-center space-x-2 px-4 py-3 bg-black text-white rounded-lg hover:bg-gray-900 transition-colors"
            >
              <Send className="h-4 w-4" />
              <span>Send Now</span>
            </button>
          </motion.div>

          {/* Close hint */}
          <motion.p 
            className="text-xs text-gray-400 text-center mt-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.4 }}
          >
            Click outside to close
          </motion.p>
        </motion.div>
      </div>
    </div>
  )
}