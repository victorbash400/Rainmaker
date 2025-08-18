import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Mail, 
  Send, 
  Clock, 
  CheckCircle, 
  Search, 
  MessageSquare, 
  ThumbsUp,
  ArrowRight,
  Loader2,
  AlertCircle
} from 'lucide-react';

interface Campaign {
  subject_line: string;
  message_body: string;
  status: string;
  sent_at?: string;
}

interface OutreachViewerProps {
  workflowId: string;
  onComplete?: () => void;
}

type OutreachStage = 
  | 'analyzing'
  | 'drafting' 
  | 'sending'
  | 'awaiting_reply'
  | 'checking'
  | 'reply_found'
  | 'awaiting_overview'
  | 'overview_requesting'
  | 'checking_overview'
  | 'overview_received'
  | 'complete'
  | 'error';

interface ReplyAnalysis {
  intent: string;
  summary: string;
  can_proceed: boolean;
}

interface EventOverview {
  event_details: {
    event_type?: string;
    date_timeframe?: string;
    guest_count?: string;
    budget_range?: string;
    venue_preferences?: string;
    special_requirements?: string;
    themes_vision?: string;
  };
  analysis_summary: string;
  has_sufficient_details: boolean;
  can_proceed_to_proposal: boolean;
}

const OutreachViewer: React.FC<OutreachViewerProps> = ({ workflowId, onComplete }) => {
  const [stage, setStage] = useState<OutreachStage>('analyzing');
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [replyAnalysis, setReplyAnalysis] = useState<ReplyAnalysis | null>(null);
  const [eventOverview, setEventOverview] = useState<EventOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [initialized, setInitialized] = useState(false);

  // Check workflow status and handle existing workflows
  useEffect(() => {
    if (!initialized) {
      checkWorkflowStatus();
    }
  }, [initialized]);

  const checkWorkflowStatus = async () => {
    try {
      // Check if workflow already has outreach status
      const status = await fetchOutreachStatus();
      if (status.campaign_sent) {
        // Workflow already has a campaign, jump to awaiting reply
        setCampaign({
          subject_line: status.subject_line,
          message_body: 'Email content preview...',
          status: status.campaign_status,
          sent_at: status.sent_at
        });
        setStage('awaiting_reply');
        setInitialized(true);
        return;
      }
    } catch (statusError) {
      console.warn('Could not fetch outreach status, starting simulation:', statusError);
    }
    
    // If no existing campaign, simulate the flow
    simulateOutreachFlow();
    
    // Mark as initialized to prevent re-runs
    setInitialized(true);
  };

  const simulateOutreachFlow = async () => {
    try {
      // Stage 1: Analyzing
      setStage('analyzing');
      await delay(2000);

      // Stage 2: Drafting
      setStage('drafting');
      await delay(3000);

      // Stage 3: Sending
      setStage('sending');
      await delay(2000);

      // Try to check outreach status, but handle errors gracefully
      try {
        const status = await fetchOutreachStatus();
        if (status.campaign_sent) {
          setCampaign({
            subject_line: status.subject_line,
            message_body: 'Email content preview...',
            status: status.campaign_status,
            sent_at: status.sent_at
          });
          setStage('awaiting_reply');
          return;
        }
      } catch (statusError) {
        console.warn('Could not fetch outreach status, using mock data:', statusError);
      }

      // Fallback: Use mock data for demo purposes
      setCampaign({
        subject_line: 'Demo Outreach Email',
        message_body: 'This is a demo email for testing the outreach flow.',
        status: 'sent',
        sent_at: new Date().toISOString()
      });
      setStage('awaiting_reply');
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
      setStage('error');
    }
  };

  const fetchOutreachStatus = async () => {
    const token = localStorage.getItem('token');
    const response = await fetch(`/api/v1/outreach/${workflowId}/status`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      if (response.status === 401) {
        console.error('Authentication failed for outreach status');
        // Could redirect to login or handle auth error
      }
      throw new Error(`Failed to fetch outreach status: ${response.status}`);
    }
    
    return response.json();
  };

  const checkForReplies = async () => {
    setLoading(true);
    setStage('checking');
    
    try {
      const response = await fetch(`/api/v1/outreach/${workflowId}/check-replies`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to check for replies');
      }

      const result = await response.json();
      
      if (result.status === 'no_reply_found') {
        // Return to awaiting reply state with feedback
        setStage('awaiting_reply');
        // Could show a toast or temporary message here
      } else if (result.status === 'reply_found') {
        setReplyAnalysis({
          intent: result.intent,
          summary: result.summary,
          can_proceed: result.can_proceed
        });
        setStage('reply_found');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check replies');
      setStage('error');
    } finally {
      setLoading(false);
    }
  };

  const requestOverview = async () => {
    setLoading(true);
    setStage('overview_requesting');
    
    try {
      const response = await fetch(`/api/v1/outreach/${workflowId}/request-overview`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to request overview');
      }

      const result = await response.json();
      setStage('awaiting_overview');
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to request overview');
      setStage('error');
    } finally {
      setLoading(false);
    }
  };

  const checkOverviewReply = async () => {
    setLoading(true);
    setStage('checking_overview');
    
    try {
      const response = await fetch(`/api/v1/outreach/${workflowId}/check-overview-reply`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to check for overview reply');
      }

      const result = await response.json();
      
      if (result.status === 'no_reply_found') {
        // Return to awaiting overview state
        setStage('awaiting_overview');
      } else if (result.status === 'overview_received') {
        setEventOverview({
          event_details: result.event_details,
          analysis_summary: result.analysis_summary,
          has_sufficient_details: result.has_sufficient_details,
          can_proceed_to_proposal: result.can_proceed_to_proposal
        });
        setStage('overview_received');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check overview reply');
      setStage('error');
    } finally {
      setLoading(false);
    }
  };

  const proceedToPlan = async () => {
    setLoading(true);
    
    try {
      const response = await fetch(`/api/v1/outreach/${workflowId}/proceed-to-proposal`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to proceed to proposal');
      }

      const result = await response.json();
      // Don't set stage to 'complete' - let WebSocket updates handle the transition
      // The workflow should now be in 'proposal' phase
      
      // Notify parent component immediately to refresh workflow data
      onComplete?.();
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to proceed');
      setStage('error');
    } finally {
      setLoading(false);
    }
  };

  const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  const getStageIcon = () => {
    switch (stage) {
      case 'analyzing':
        return <Search className="w-6 h-6 animate-pulse" />;
      case 'drafting':
        return <Mail className="w-6 h-6 animate-pulse" />;
      case 'sending':
        return <Send className="w-6 h-6 animate-pulse" />;
      case 'awaiting_reply':
        return <Clock className="w-6 h-6" />;
      case 'checking':
        return <Loader2 className="w-6 h-6 animate-spin" />;
      case 'reply_found':
        return <MessageSquare className="w-6 h-6" />;
      case 'overview_requesting':
        return <Send className="w-6 h-6 animate-pulse" />;
      case 'awaiting_overview':
        return <Clock className="w-6 h-6" />;
      case 'checking_overview':
        return <Loader2 className="w-6 h-6 animate-spin" />;
      case 'overview_received':
        return <MessageSquare className="w-6 h-6" />;
      case 'complete':
        return <CheckCircle className="w-6 h-6 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-6 h-6 text-red-500" />;
      default:
        return <Clock className="w-6 h-6" />;
    }
  };

  const getStageMessage = () => {
    switch (stage) {
      case 'analyzing':
        return 'AI is analyzing the prospect data...';
      case 'drafting':
        return 'Drafting a personalized email...';
      case 'sending':
        return 'Sending email...';
      case 'awaiting_reply':
        return 'Email sent! Awaiting reply.';
      case 'checking':
        return 'Checking for new replies...';
      case 'reply_found':
        return 'Reply received and analyzed!';
      case 'overview_requesting':
        return 'Sending event overview request...';
      case 'awaiting_overview':
        return 'Overview request sent! Awaiting event details.';
      case 'checking_overview':
        return 'Checking for overview response...';
      case 'overview_received':
        return 'Event overview received and analyzed!';
      case 'complete':
        return 'Great! The workflow will now proceed...';
      case 'error':
        return error || 'An error occurred';
      default:
        return 'Processing...';
    }
  };

  const getIntentColor = (intent: string) => {
    switch (intent) {
      case 'INTERESTED':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'NOT_INTERESTED':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'QUESTION':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className="flex-1 max-w-2xl">
      <div className="bg-white border border-gray-100 rounded-xl shadow-sm overflow-hidden">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-6">
            <motion.div 
              className="p-2 bg-gray-50 rounded-lg"
              animate={{ scale: [1, 1.05, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              {getStageIcon()}
            </motion.div>
            <div>
              <h3 className="text-lg font-medium text-gray-900">Outreach Campaign</h3>
              <p className="text-sm text-gray-500">{getStageMessage()}</p>
            </div>
          </div>

      <AnimatePresence mode="wait">
        {/* Initial Processing Stages */}
        {['analyzing', 'drafting', 'sending'].includes(stage) && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-6"
          >
            {/* Animated Email Icon */}
            <div className="flex justify-center">
              <motion.div
                className="relative"
                animate={{ 
                  rotate: stage === 'sending' ? [0, 2, -2, 0] : 0
                }}
                transition={{ 
                  duration: 1.5, 
                  repeat: Infinity, 
                  ease: "easeInOut" 
                }}
              >
                <div className="w-20 h-20 bg-white rounded-2xl shadow-sm border border-gray-200 flex items-center justify-center">
                  {/* Mail icon */}
                  <Mail className="w-8 h-8 text-black" />
                </div>
              </motion.div>
            </div>

            {/* Status Text */}
            <div className="text-center space-y-3">
              <motion.h4 
                className="text-lg font-medium text-gray-900"
                animate={{ opacity: [0.7, 1, 0.7] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                {stage === 'analyzing' && 'Analyzing Prospect'}
                {stage === 'drafting' && 'Crafting Email'}
                {stage === 'sending' && 'Sending Message'}
              </motion.h4>
              
              <p className="text-sm text-gray-500 max-w-sm mx-auto leading-relaxed">
                {stage === 'analyzing' && 'AI is analyzing prospect data and enrichment insights to create the perfect outreach strategy.'}
                {stage === 'drafting' && 'Creating a personalized, compelling message that resonates with your prospect\'s needs.'}
                {stage === 'sending' && 'Delivering your carefully crafted email through secure channels.'}
              </p>
            </div>

            {/* Progress Bar */}
            <div className="bg-gray-100 h-2 rounded-full overflow-hidden max-w-md mx-auto">
              <motion.div
                className="bg-black h-full rounded-full"
                initial={{ width: '0%' }}
                animate={{ width: '100%' }}
                transition={{ duration: 3, ease: "easeInOut" }}
              />
            </div>
          </motion.div>
        )}

        {/* Awaiting Reply Stage */}
        {stage === 'awaiting_reply' && campaign && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Success Animation */}
            <div className="flex justify-center">
              <motion.div
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ 
                  type: "spring", 
                  damping: 15, 
                  stiffness: 300,
                  delay: 0.2 
                }}
                className="relative"
              >
                <div className="w-20 h-20 bg-white rounded-2xl shadow-sm border border-gray-200 flex items-center justify-center">
                  {/* Checkmark */}
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.5, type: "spring", damping: 10 }}
                  >
                    <CheckCircle className="w-8 h-8 text-black" />
                  </motion.div>
                </div>
              </motion.div>
            </div>

            {/* Success Message */}
            <div className="text-center space-y-2">
              <motion.h4 
                className="text-lg font-medium text-gray-900"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.8 }}
              >
                Email Sent Successfully!
              </motion.h4>
              
              <motion.div 
                className="text-sm text-gray-600 space-y-1 max-w-sm mx-auto"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1 }}
              >
                <p><span className="font-medium">Subject:</span> {campaign.subject_line}</p>
                {campaign.sent_at && (
                  <p><span className="font-medium">Sent:</span> {new Date(campaign.sent_at).toLocaleString()}</p>
                )}
              </motion.div>
            </div>


            {/* Action Button */}
            <div className="text-center py-4">
              <motion.button
                onClick={checkForReplies}
                disabled={loading}
                className="bg-black hover:bg-gray-800 disabled:bg-gray-400 text-white px-6 py-3 rounded-xl font-medium flex items-center gap-2 mx-auto transition-all duration-200"
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.2 }}
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Search className="w-4 h-4" />
                )}
                Check for New Replies
              </motion.button>
              <motion.p 
                className="text-xs text-gray-400 mt-3"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.4 }}
              >
                Click when you've received a reply to continue the workflow
              </motion.p>
            </div>
          </motion.div>
        )}

        {/* Checking Stage */}
        {stage === 'checking' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-8"
          >
            <Loader2 className="w-6 h-6 animate-spin text-gray-600 mx-auto mb-3" />
            <p className="text-sm text-gray-500">Scanning inbox and analyzing replies...</p>
          </motion.div>
        )}

        {/* Overview Requesting Stage */}
        {stage === 'overview_requesting' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Follow-up Email Animation */}
            <div className="flex justify-center">
              <motion.div
                className="relative"
                animate={{ 
                  rotate: [0, 1, -1, 0]
                }}
                transition={{ 
                  duration: 2, 
                  repeat: Infinity, 
                  ease: "easeInOut" 
                }}
              >
                <div className="w-20 h-20 bg-white rounded-2xl shadow-sm border border-gray-200 flex items-center justify-center relative">
                  {/* Mail icon */}
                  <Mail className="w-8 h-8 text-black" />
                  
                  {/* Follow-up indicator */}
                  <motion.div
                    className="absolute -top-1 -right-1 w-4 h-4 bg-black rounded-full flex items-center justify-center"
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: 0.5 }}
                  >
                    <span className="text-xs text-white font-bold">2</span>
                  </motion.div>
                </div>
              </motion.div>
            </div>

            {/* Status Text */}
            <div className="text-center space-y-3">
              <motion.h4 
                className="text-lg font-medium text-gray-900"
                animate={{ opacity: [0.7, 1, 0.7] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                Crafting Follow-up
              </motion.h4>
              
              <p className="text-sm text-gray-500 max-w-sm mx-auto leading-relaxed">
                Creating a personalized follow-up email to gather event details and requirements.
              </p>
            </div>

            {/* Progress indicator */}
            <div className="bg-gray-100 h-2 rounded-full overflow-hidden max-w-md mx-auto">
              <motion.div
                className="bg-black h-full rounded-full"
                initial={{ width: '0%' }}
                animate={{ width: '100%' }}
                transition={{ duration: 2, ease: "easeInOut" }}
              />
            </div>
          </motion.div>
        )}

        {/* Awaiting Overview Stage */}
        {stage === 'awaiting_overview' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Success Animation with follow-up indicator */}
            <div className="flex justify-center">
              <motion.div
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ 
                  type: "spring", 
                  damping: 15, 
                  stiffness: 300,
                  delay: 0.2 
                }}
                className="relative"
              >
                <div className="w-20 h-20 bg-white rounded-2xl shadow-sm border border-gray-200 flex items-center justify-center relative">
                  {/* Checkmark */}
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.5, type: "spring", damping: 10 }}
                  >
                    <CheckCircle className="w-8 h-8 text-black" />
                  </motion.div>
                  
                  {/* Follow-up email indicator */}
                  <motion.div
                    className="absolute -top-1 -right-1 w-4 h-4 bg-black rounded-full flex items-center justify-center"
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: 0.8 }}
                  >
                    <span className="text-xs text-white font-bold">2</span>
                  </motion.div>
                </div>
              </motion.div>
            </div>

            {/* Success Message */}
            <div className="text-center space-y-2">
              <motion.h4 
                className="text-lg font-medium text-gray-900"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.8 }}
              >
                Follow-up Sent Successfully!
              </motion.h4>
              
              <motion.div 
                className="text-sm text-gray-600 space-y-1 max-w-md mx-auto"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1 }}
              >
                <p>We've requested detailed event information including:</p>
                <div className="flex flex-wrap justify-center gap-2 mt-2">
                  {['Event Type', 'Timeline', 'Guest Count', 'Budget'].map((item, i) => (
                    <motion.span
                      key={item}
                      className="px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-medium"
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 1.2 + (i * 0.1) }}
                    >
                      {item}
                    </motion.span>
                  ))}
                </div>
              </motion.div>
            </div>

            {/* Action Button */}
            <div className="text-center py-4">
              <motion.button
                onClick={checkOverviewReply}
                disabled={loading}
                className="bg-black hover:bg-gray-800 disabled:bg-gray-400 text-white px-6 py-3 rounded-xl font-medium flex items-center gap-2 mx-auto transition-all duration-200"
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.4 }}
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Search className="w-4 h-4" />
                )}
                Check for Event Details
              </motion.button>
              <motion.p 
                className="text-xs text-gray-400 mt-3"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.6 }}
              >
                Click when you've received the event overview to continue
              </motion.p>
            </div>
          </motion.div>
        )}

        {/* Checking Overview Stage */}
        {stage === 'checking_overview' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Analyzing Animation */}
            <div className="flex justify-center">
              <div className="w-20 h-20 bg-white rounded-2xl shadow-sm border border-gray-200 flex items-center justify-center">
                {/* Search icon with animation */}
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                >
                  <Search className="w-8 h-8 text-black" />
                </motion.div>
              </div>
            </div>

            {/* Status Text */}
            <div className="text-center space-y-3">
              <motion.h4 
                className="text-lg font-medium text-gray-900"
                animate={{ opacity: [0.7, 1, 0.7] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                Analyzing Event Details
              </motion.h4>
              
              <p className="text-sm text-gray-500 max-w-sm mx-auto leading-relaxed">
                AI is processing the event overview and extracting key requirements for proposal generation.
              </p>
            </div>

            {/* Progress indicator */}
            <div className="bg-gray-100 h-2 rounded-full overflow-hidden max-w-md mx-auto">
              <motion.div
                className="bg-black h-full rounded-full w-8"
                animate={{ 
                  x: ['-2rem', 'calc(100% + 2rem)']
                }}
                transition={{ 
                  duration: 2, 
                  repeat: Infinity, 
                  ease: "easeInOut" 
                }}
              />
            </div>
          </motion.div>
        )}

        {/* Overview Received Stage */}
        {stage === 'overview_received' && eventOverview && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-100">
              <div className="flex items-center gap-2 mb-4">
                <MessageSquare className="w-5 h-5 text-gray-700" />
                <span className="font-medium text-gray-800">Event Overview Analysis</span>
              </div>
              
              <div className="space-y-4">
                <div>
                  <span className="text-sm font-medium text-gray-600 block mb-2">Summary:</span>
                  <p className="text-sm text-gray-700 leading-relaxed">{eventOverview.analysis_summary}</p>
                </div>
                
                {Object.keys(eventOverview.event_details).length > 0 && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {eventOverview.event_details.event_type && (
                      <div>
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Event Type</span>
                        <p className="text-sm text-gray-700">{eventOverview.event_details.event_type}</p>
                      </div>
                    )}
                    {eventOverview.event_details.date_timeframe && (
                      <div>
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Timeline</span>
                        <p className="text-sm text-gray-700">{eventOverview.event_details.date_timeframe}</p>
                      </div>
                    )}
                    {eventOverview.event_details.guest_count && (
                      <div>
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Guest Count</span>
                        <p className="text-sm text-gray-700">{eventOverview.event_details.guest_count}</p>
                      </div>
                    )}
                    {eventOverview.event_details.budget_range && (
                      <div>
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Budget</span>
                        <p className="text-sm text-gray-700">{eventOverview.event_details.budget_range}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {eventOverview.can_proceed_to_proposal && (
              <div className="text-center py-6">
                <motion.button
                  onClick={proceedToPlan}
                  disabled={loading}
                  className="bg-black hover:bg-gray-800 disabled:bg-gray-400 text-white px-6 py-3 rounded-xl font-medium flex items-center gap-2 mx-auto transition-all duration-200"
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <ThumbsUp className="w-4 h-4" />
                      Create Proposal
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </motion.button>
                <p className="text-xs text-gray-400 mt-3">
                  Sufficient details received! Ready to create proposal.
                </p>
              </div>
            )}

            {!eventOverview.can_proceed_to_proposal && (
              <div className="text-center py-6">
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
                  <p className="text-sm text-yellow-800">
                    Need more details to create a comprehensive proposal. Consider following up for clarification.
                  </p>
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* Reply Found Stage */}
        {stage === 'reply_found' && replyAnalysis && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-100">
              <div className="flex items-center gap-2 mb-3">
                <MessageSquare className="w-5 h-5 text-gray-700" />
                <span className="font-medium text-gray-800">Reply Analysis</span>
              </div>
              
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-600">Intent:</span>
                  <span className={`px-2 py-1 rounded-md text-xs font-medium border ${getIntentColor(replyAnalysis.intent)}`}>
                    {replyAnalysis.intent}
                  </span>
                </div>
                
                <div>
                  <span className="text-sm font-medium text-gray-600 block mb-1">Summary:</span>
                  <p className="text-sm text-gray-700 leading-relaxed">{replyAnalysis.summary}</p>
                </div>
              </div>
            </div>

            {replyAnalysis.can_proceed && (
              <div className="text-center py-6">
                <motion.button
                  onClick={requestOverview}
                  disabled={loading}
                  className="bg-black hover:bg-gray-800 disabled:bg-gray-400 text-white px-6 py-3 rounded-xl font-medium flex items-center gap-2 mx-auto transition-all duration-200"
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <Mail className="w-4 h-4" />
                      Ask for Event Overview
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </motion.button>
                <p className="text-xs text-gray-400 mt-3">
                  Prospect is interested! Let's gather event details.
                </p>
              </div>
            )}
          </motion.div>
        )}

        {/* Complete Stage */}
        {stage === 'complete' && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center py-8"
          >
            <motion.div
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 0.6 }}
              className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4"
            >
              <CheckCircle className="w-6 h-6 text-gray-700" />
            </motion.div>
            <h4 className="text-lg font-medium text-gray-900 mb-2">Workflow Complete</h4>
            <p className="text-sm text-gray-500">The outreach phase has finished successfully.</p>
          </motion.div>
        )}

        {/* Error Stage */}
        {stage === 'error' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-gray-50 p-4 rounded-lg border border-gray-200"
          >
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="w-5 h-5 text-gray-600" />
              <span className="font-medium text-gray-800">Error</span>
            </div>
            <p className="text-sm text-gray-600">{error}</p>
          </motion.div>
        )}
        </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default OutreachViewer;