import { Calendar, Clock, MapPin, User, Video, Plus, Loader2, AlertTriangle } from 'lucide-react'
import { useState, useEffect } from 'react'

interface Meeting {
  id: number;
  workflow_id?: string;
  title: string;
  prospect_name: string;
  prospect_email: string;
  prospect_company?: string;
  meeting_type: string;
  scheduled_at: string;
  duration_minutes: number;
  location?: string;
  google_meet_link?: string;
  status: string;
  description?: string;
  created_at: string;
}

export default function Meetings() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadMeetings();
  }, []);

  const loadMeetings = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/calendar/meetings', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to load meetings');
      }

      const data = await response.json();
      setMeetings(data.meetings || []);
      setError(null);
    } catch (err) {
      console.error('Failed to load meetings:', err);
      setError(err instanceof Error ? err.message : 'Failed to load meetings');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'scheduled':
      case 'confirmed':
        return 'bg-green-100 text-green-800';
      case 'cancelled':
        return 'bg-red-100 text-red-800';
      case 'completed':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  const isVideoMeeting = (meeting: Meeting) => {
    return meeting.google_meet_link || 
           (meeting.location && (meeting.location.includes('Meet') || meeting.location.includes('Zoom')));
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      weekday: 'short',
      month: 'short', 
      day: 'numeric',
      year: 'numeric'
    });
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  };

  if (loading) {
    return (
      <div className="h-screen bg-white">
        <div className="max-w-4xl mx-auto px-6 py-6">
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-semibold text-black">Meetings</h1>
                <p className="mt-1 text-gray-500">
                  AI-scheduled meetings and consultations
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
                <h1 className="text-2xl font-semibold text-black">Meetings</h1>
                <p className="mt-1 text-gray-500">
                  AI-scheduled meetings and consultations
                </p>
              </div>
            </div>
            <div className="text-center py-12">
              <AlertTriangle className="h-12 w-12 mx-auto text-red-400 mb-4" />
              <h3 className="text-lg font-medium text-red-900">Error loading meetings</h3>
              <p className="text-red-600 mb-4">{error}</p>
              <button 
                onClick={loadMeetings}
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
      <div className="max-w-4xl mx-auto px-6 py-6">
        <div className="space-y-8">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-black">Meetings</h1>
              <p className="mt-1 text-gray-500">
                AI-scheduled meetings and consultations
              </p>
            </div>
            <button 
              onClick={loadMeetings}
              className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors duration-200"
            >
              <Plus className="h-4 w-4" />
              <span className="text-sm font-medium">Refresh</span>
            </button>
          </div>

          {/* Meetings List */}
          <div className="space-y-4">
            {meetings.map((meeting) => (
              <div key={meeting.id} className="border border-gray-200 rounded-xl bg-white">
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center space-x-4">
                      <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center">
                        {isVideoMeeting(meeting) ? (
                          <Video className="h-6 w-6 text-gray-600" />
                        ) : (
                          <MapPin className="h-6 w-6 text-gray-600" />
                        )}
                      </div>
                      <div>
                        <h3 className="font-medium text-black">{meeting.title}</h3>
                        <p className="text-sm text-gray-500">
                          {meeting.prospect_name} • {meeting.prospect_company || 'Individual Client'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(meeting.status)}`}>
                        {meeting.status}
                      </span>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-6 text-sm mb-4">
                    <div className="flex items-center space-x-2 text-gray-600">
                      <Calendar className="h-4 w-4" />
                      <span>{formatDate(meeting.scheduled_at)}</span>
                    </div>
                    <div className="flex items-center space-x-2 text-gray-600">
                      <Clock className="h-4 w-4" />
                      <span>{formatTime(meeting.scheduled_at)} ({meeting.duration_minutes}m)</span>
                    </div>
                    <div className="flex items-center space-x-2 text-gray-600">
                      {isVideoMeeting(meeting) ? (
                        <Video className="h-4 w-4" />
                      ) : (
                        <MapPin className="h-4 w-4" />
                      )}
                      <span>{meeting.location || 'Google Meet'}</span>
                    </div>
                  </div>
                  
                  {meeting.description && (
                    <div className="text-sm text-gray-600 mb-4">
                      {meeting.description}
                    </div>
                  )}
                  
                  <div className="pt-4 border-t border-gray-100">
                    <div className="flex items-center justify-between">
                      <div className="text-xs text-gray-400">
                        {meeting.meeting_type.charAt(0).toUpperCase() + meeting.meeting_type.slice(1).replace('_', ' ')}
                        {meeting.workflow_id && (
                          <span className="ml-2 px-2 py-1 bg-blue-50 text-blue-700 rounded-full text-xs">
                            Workflow: {meeting.workflow_id.slice(0, 8)}
                          </span>
                        )}
                      </div>
                      <div className="flex space-x-2">
                        {meeting.google_meet_link && (
                          <a
                            href={meeting.google_meet_link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-blue-600 hover:text-blue-700 transition-colors"
                          >
                            Join Meeting
                          </a>
                        )}
                        <button className="text-sm text-gray-600 hover:text-black transition-colors">
                          Reschedule
                        </button>
                        <button className="text-sm text-gray-600 hover:text-black transition-colors">
                          Cancel
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Empty State */}
          {meetings.length === 0 && (
            <div className="text-center py-12">
              <Calendar className="h-12 w-12 mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-black mb-2">No meetings scheduled</h3>
              <p className="text-gray-500 mb-6">
                Meetings will appear here when scheduled through your workflows
              </p>
              <button 
                onClick={loadMeetings}
                className="flex items-center space-x-2 px-4 py-2 bg-black text-white hover:bg-gray-900 rounded-lg transition-colors duration-200 mx-auto"
              >
                <Plus className="h-4 w-4" />
                <span className="text-sm font-medium">Refresh Meetings</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}