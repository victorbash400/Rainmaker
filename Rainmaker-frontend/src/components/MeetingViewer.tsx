import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Calendar, 
  Clock, 
  CheckCircle, 
  Video, 
  Mail, 
  Search, 
  Loader2,
  AlertCircle,
  Users,
  MapPin,
  ExternalLink
} from 'lucide-react';

import { useAuthStore } from '@/store/authStore';

interface MeetingViewerProps {
  workflowId: string;
  onComplete?: () => void;
}

type MeetingStage = 
  | 'checking_response'
  | 'response_found'
  | 'scheduling'
  | 'meeting_scheduled'
  | 'awaiting_response'
  | 'error';

interface MeetingResponse {
  status: string;
  wants_meeting: boolean;
  meeting_preferences?: {
    preferred_dates?: string[];
    preferred_times?: string[];
    duration?: string;
    format?: string;
    availability_notes?: string;
  };
  response_analysis?: string;
  reason?: string;
}

interface MeetingDetails {
  meeting_id: number;
  title: string;
  scheduled_at: string;
  duration_minutes: number;
  google_meet_link: string;
  prospect_name: string;
  prospect_email: string;
  prospect_company: string;
}

const MeetingViewer: React.FC<MeetingViewerProps> = ({ workflowId, onComplete }) => {
  const [stage, setStage] = useState<MeetingStage>('awaiting_response');
  const [meetingResponse, setMeetingResponse] = useState<MeetingResponse | null>(null);
  const [meetingDetails, setMeetingDetails] = useState<MeetingDetails | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const token = useAuthStore((state) => state.token);

  const checkMeetingResponse = async () => {
    setLoading(true);
    setStage('checking_response');
    setError(null);

    try {
      const response = await fetch(`/api/v1/calendar/${workflowId}/check-meeting-response`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to check meeting response');
      }

      const result = await response.json();
      
      if (result.status === 'no_reply_found') {
        setStage('awaiting_response');
      } else if (result.status === 'meeting_accepted') {
        setMeetingResponse(result);
        setStage('response_found');
      } else if (result.status === 'meeting_declined') {
        setMeetingResponse(result);
        setError(`Meeting declined: ${result.reason || 'No reason provided'}`);
        setStage('error');
      } else {
        throw new Error('Unexpected response status');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check meeting response');
      setStage('error');
    } finally {
      setLoading(false);
    }
  };

  const scheduleMeeting = async () => {
    if (!meetingResponse) return;
    
    setLoading(true);
    setStage('scheduling');
    setError(null);

    try {
      const response = await fetch(`/api/v1/calendar/${workflowId}/schedule-meeting`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          meeting_preferences: meetingResponse.meeting_preferences
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to schedule meeting');
      }

      const result = await response.json();
      setMeetingDetails(result.meeting_details);
      setStage('meeting_scheduled');
      
      // Complete the workflow after successful scheduling
      setTimeout(() => {
        onComplete?.();
      }, 3000);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to schedule meeting');
      setStage('error');
    } finally {
      setLoading(false);
    }
  };

  const getStageIcon = () => {
    switch (stage) {
      case 'checking_response':
        return null;
      case 'response_found':
        return <Mail className="w-6 h-6 text-green-600" />;
      case 'scheduling':
        return <Calendar className="w-6 h-6 animate-pulse" />;
      case 'meeting_scheduled':
        return <CheckCircle className="w-6 h-6 text-green-600" />;
      case 'awaiting_response':
        return <Clock className="w-6 h-6" />;
      case 'error':
        return <AlertCircle className="w-6 h-6 text-red-500" />;
      default:
        return <Clock className="w-6 h-6" />;
    }
  };

  const getStageMessage = () => {
    switch (stage) {
      case 'checking_response':
        return 'Checking for meeting responses...';
      case 'response_found':
        return 'Meeting response received!';
      case 'scheduling':
        return 'Scheduling Google Meet...';
      case 'meeting_scheduled':
        return 'Meeting scheduled successfully!';
      case 'awaiting_response':
        return 'Waiting for client to respond to meeting request';
      case 'error':
        return error || 'An error occurred';
      default:
        return 'Processing...';
    }
  };

  const formatDateTime = (dateTime: string) => {
    const date = new Date(dateTime);
    return {
      date: date.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      }),
      time: date.toLocaleTimeString('en-US', { 
        hour: 'numeric', 
        minute: '2-digit',
        hour12: true 
      })
    };
  };

  return (
    <div className="flex-1 max-w-2xl">
      <div className="bg-white border border-gray-100 rounded-xl shadow-sm overflow-hidden">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-6">
            {stage !== 'checking_response' && (
              <motion.div 
                className="p-2 bg-gray-50 rounded-lg"
                animate={{ scale: [1, 1.05, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                {getStageIcon()}
              </motion.div>
            )}
            <div>
              <h3 className="text-lg font-medium text-gray-900">Meeting Scheduler</h3>
              <p className="text-sm text-gray-500">{getStageMessage()}</p>
            </div>
          </div>

          <AnimatePresence mode="wait">
            {/* Checking Response Stage */}
            {stage === 'checking_response' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="space-y-6"
              >
                <div className="flex justify-center">
                  <motion.div
                    className="relative"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  >
                    <div className="w-20 h-20 bg-white rounded-2xl shadow-sm border border-gray-200 flex items-center justify-center">
                      <img src="/reading-eyes.gif" alt="Reading emails..." className="w-16 h-16" />
                    </div>
                  </motion.div>
                </div>

                <div className="text-center space-y-3">
                  <motion.h4 
                    className="text-lg font-medium text-gray-900"
                    animate={{ opacity: [0.7, 1, 0.7] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    Scanning for Responses
                  </motion.h4>
                  
                  <p className="text-sm text-gray-500 max-w-sm mx-auto leading-relaxed">
                    AI is checking email threads for client responses to your meeting request.
                  </p>
                </div>

                <div className="bg-gray-100 h-2 rounded-full overflow-hidden max-w-md mx-auto">
                  <motion.div
                    className="bg-black h-full rounded-full w-8"
                    animate={{ x: ['-2rem', 'calc(100% + 2rem)'] }}
                    transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                  />
                </div>
              </motion.div>
            )}

            {/* Awaiting Response Stage */}
            {stage === 'awaiting_response' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="space-y-6"
              >
                <div className="flex justify-center">
                  <div className="w-20 h-20 bg-white rounded-2xl shadow-sm border border-gray-200 flex items-center justify-center">
                    <Clock className="w-8 h-8 text-gray-600" />
                  </div>
                </div>

                <div className="text-center space-y-4">
                  <h4 className="text-lg font-medium text-gray-900">
                    Waiting for Client Response
                  </h4>
                  
                  <p className="text-sm text-gray-500 max-w-sm mx-auto leading-relaxed">
                    No meeting response found yet. The client may still be reviewing your proposal and meeting request.
                  </p>

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <p className="text-sm text-blue-800">
                      <strong>What happens next:</strong><br/>
                      Once the client responds with their availability, the system will automatically detect it and proceed with scheduling.
                    </p>
                  </div>

                  <button
                    onClick={checkMeetingResponse}
                    disabled={loading}
                    className="bg-black hover:bg-gray-800 disabled:bg-gray-400 text-white px-6 py-3 rounded-xl font-medium flex items-center gap-2 mx-auto transition-all duration-200"
                  >
                    {loading ? (
                      <img src="/reading-eyes.gif" alt="Checking for responses..." className="w-4 h-4" />
                    ) : (
                      <Search className="w-4 h-4" />
                    )}
                    Check Again
                  </button>
                </div>
              </motion.div>
            )}

            {/* Response Found Stage */}
            {stage === 'response_found' && meetingResponse && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="space-y-6"
              >
                <div className="flex justify-center">
                  <motion.div
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ type: "spring", damping: 15, stiffness: 300 }}
                    className="relative"
                  >
                    <div className="w-20 h-20 bg-white rounded-2xl shadow-sm border border-gray-200 flex items-center justify-center">
                      <CheckCircle className="w-8 h-8 text-green-600" />
                    </div>
                  </motion.div>
                </div>

                <div className="text-center space-y-4">
                  <h4 className="text-lg font-medium text-gray-900">
                    Great! Client Wants to Meet
                  </h4>
                  
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="text-sm text-green-800">
                      <p className="font-medium mb-2">Response Analysis:</p>
                      <p>{meetingResponse.response_analysis}</p>
                    </div>
                  </div>

                  {meetingResponse.meeting_preferences && (
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                      <h5 className="font-medium text-gray-900 mb-3">Client Preferences:</h5>
                      <div className="space-y-2 text-sm text-gray-700">
                        {meetingResponse.meeting_preferences.preferred_dates && meetingResponse.meeting_preferences.preferred_dates.length > 0 && (
                          <div>
                            <span className="font-medium">Preferred Dates:</span>
                            <div className="flex flex-wrap gap-2 mt-1">
                              {meetingResponse.meeting_preferences.preferred_dates.map((date, i) => (
                                <span key={i} className="px-2 py-1 bg-white rounded-full text-xs border">
                                  {date}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {meetingResponse.meeting_preferences.preferred_times && meetingResponse.meeting_preferences.preferred_times.length > 0 && (
                          <div>
                            <span className="font-medium">Preferred Times:</span>
                            <div className="flex flex-wrap gap-2 mt-1">
                              {meetingResponse.meeting_preferences.preferred_times.map((time, i) => (
                                <span key={i} className="px-2 py-1 bg-white rounded-full text-xs border">
                                  {time}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {meetingResponse.meeting_preferences.duration && (
                          <div>
                            <span className="font-medium">Duration:</span> {meetingResponse.meeting_preferences.duration}
                          </div>
                        )}
                        {meetingResponse.meeting_preferences.format && (
                          <div>
                            <span className="font-medium">Format:</span> {meetingResponse.meeting_preferences.format}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  <button
                    onClick={scheduleMeeting}
                    disabled={loading}
                    className="bg-black hover:bg-gray-800 disabled:bg-gray-400 text-white px-6 py-3 rounded-xl font-medium flex items-center gap-2 mx-auto transition-all duration-200"
                  >
                    {loading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Calendar className="w-4 h-4" />
                    )}
                    Schedule Google Meet
                  </button>
                </div>
              </motion.div>
            )}

            {/* Scheduling Stage */}
            {stage === 'scheduling' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="space-y-6"
              >
                <div className="flex justify-center">
                  <motion.div
                    className="relative"
                    animate={{ rotate: [0, 5, -5, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                  >
                    <div className="w-20 h-20 bg-white rounded-2xl shadow-sm border border-gray-200 flex items-center justify-center">
                      <Calendar className="w-8 h-8 text-black" />
                    </div>
                  </motion.div>
                </div>

                <div className="text-center space-y-3">
                  <motion.h4 
                    className="text-lg font-medium text-gray-900"
                    animate={{ opacity: [0.7, 1, 0.7] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    Creating Your Meeting
                  </motion.h4>
                  
                  <p className="text-sm text-gray-500 max-w-sm mx-auto leading-relaxed">
                    Setting up Google Calendar event with Meet link and sending invitation to your client.
                  </p>
                </div>

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

            {/* Meeting Scheduled Stage */}
            {stage === 'meeting_scheduled' && meetingDetails && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="space-y-6"
              >
                <div className="flex justify-center">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", damping: 15, stiffness: 300, delay: 0.2 }}
                    className="relative"
                  >
                    <div className="w-20 h-20 bg-gradient-to-br from-green-400 to-green-600 rounded-2xl shadow-lg flex items-center justify-center">
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.5, type: "spring", damping: 10 }}
                      >
                        <CheckCircle className="w-8 h-8 text-white" />
                      </motion.div>
                    </div>
                  </motion.div>
                </div>

                <div className="text-center space-y-4">
                  <motion.h4 
                    className="text-xl font-semibold text-gray-900"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.8 }}
                  >
                    Meeting Scheduled Successfully! 🎉
                  </motion.h4>
                  
                  <motion.p 
                    className="text-sm text-gray-600"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1 }}
                  >
                    Your Google Meet with {meetingDetails.prospect_name} is all set up
                  </motion.p>
                </div>

                <motion.div 
                  className="bg-gray-50 rounded-xl p-6 space-y-4"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 1.2 }}
                >
                  <div className="flex items-center justify-between">
                    <h5 className="font-medium text-gray-900">Meeting Details</h5>
                    <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                      Confirmed
                    </span>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <Users className="w-4 h-4 text-gray-500" />
                      <div>
                        <p className="font-medium text-gray-900">{meetingDetails.title}</p>
                        <p className="text-sm text-gray-500">{meetingDetails.prospect_name} • {meetingDetails.prospect_company}</p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-3">
                      <Calendar className="w-4 h-4 text-gray-500" />
                      <div>
                        <p className="font-medium text-gray-900">{formatDateTime(meetingDetails.scheduled_at).date}</p>
                        <p className="text-sm text-gray-500">{formatDateTime(meetingDetails.scheduled_at).time}</p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-3">
                      <Clock className="w-4 h-4 text-gray-500" />
                      <p className="text-sm text-gray-700">{meetingDetails.duration_minutes} minutes</p>
                    </div>
                    
                    <div className="flex items-center gap-3">
                      <Video className="w-4 h-4 text-gray-500" />
                      <div className="flex-1">
                        <p className="text-sm text-gray-700">Google Meet</p>
                        <a 
                          href={meetingDetails.google_meet_link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
                        >
                          Join meeting <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    </div>
                  </div>
                </motion.div>

                <motion.div 
                  className="bg-blue-50 border border-blue-200 rounded-lg p-4"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 1.4 }}
                >
                  <h6 className="font-medium text-blue-900 mb-2">What happens next?</h6>
                  <ul className="text-sm text-blue-800 space-y-1">
                    <li>• Calendar invitation sent to {meetingDetails.prospect_email}</li>
                    <li>• Meeting added to your calendar</li>
                    <li>• Google Meet link is ready for the session</li>
                    <li>• You'll receive reminders before the meeting</li>
                  </ul>
                </motion.div>
              </motion.div>
            )}

            {/* Error Stage */}
            {stage === 'error' && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="bg-red-50 p-4 rounded-lg border border-red-200"
              >
                <div className="flex items-center gap-2 mb-2">
                  <AlertCircle className="w-5 h-5 text-red-600" />
                  <span className="font-medium text-red-800">Error</span>
                </div>
                <p className="text-sm text-red-700">{error}</p>
                <button
                  onClick={checkMeetingResponse}
                  className="mt-3 text-sm text-red-600 hover:text-red-700 underline"
                >
                  Try again
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default MeetingViewer;