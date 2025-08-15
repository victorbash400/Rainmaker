import { Calendar, Clock, MapPin, User, Video, Plus } from 'lucide-react'

// Mock meetings data
const meetings = [
  {
    id: 1,
    title: 'Initial Consultation - Sarah Johnson',
    prospect: 'Sarah Johnson',
    company: 'Tech Corp',
    type: 'consultation',
    scheduledAt: '2024-11-15T14:00:00',
    duration: 60,
    location: 'Google Meet',
    status: 'confirmed',
    description: 'Discuss corporate event requirements and venue preferences'
  },
  {
    id: 2,
    title: 'Venue Walkthrough - Mike Chen',
    prospect: 'Mike Chen',
    company: 'Startup Inc',
    type: 'venue_visit',
    scheduledAt: '2024-11-16T10:30:00',
    duration: 90,
    location: 'Grand Ballroom, Downtown',
    status: 'confirmed',
    description: 'Tour potential venue for product launch event'
  },
  {
    id: 3,
    title: 'Planning Session - Emily Rodriguez',
    prospect: 'Emily Rodriguez',
    company: 'Personal',
    type: 'planning',
    scheduledAt: '2024-11-18T16:00:00',
    duration: 45,
    location: 'Zoom',
    status: 'pending',
    description: 'Finalize wedding details and vendor selections'
  },
]

export default function Meetings() {
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
            <button className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors duration-200">
              <Plus className="h-4 w-4" />
              <span className="text-sm font-medium">Schedule Meeting</span>
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
                        {meeting.location.includes('Meet') || meeting.location.includes('Zoom') ? (
                          <Video className="h-6 w-6 text-gray-600" />
                        ) : (
                          <MapPin className="h-6 w-6 text-gray-600" />
                        )}
                      </div>
                      <div>
                        <h3 className="font-medium text-black">{meeting.title}</h3>
                        <p className="text-sm text-gray-500">{meeting.prospect} • {meeting.company}</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        meeting.status === 'confirmed' ? 'bg-black text-white' :
                        meeting.status === 'pending' ? 'bg-gray-100 text-gray-600' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {meeting.status}
                      </span>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-6 text-sm mb-4">
                    <div className="flex items-center space-x-2 text-gray-600">
                      <Calendar className="h-4 w-4" />
                      <span>{new Date(meeting.scheduledAt).toLocaleDateString()}</span>
                    </div>
                    <div className="flex items-center space-x-2 text-gray-600">
                      <Clock className="h-4 w-4" />
                      <span>{new Date(meeting.scheduledAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} ({meeting.duration}m)</span>
                    </div>
                    <div className="flex items-center space-x-2 text-gray-600">
                      {meeting.location.includes('Meet') || meeting.location.includes('Zoom') ? (
                        <Video className="h-4 w-4" />
                      ) : (
                        <MapPin className="h-4 w-4" />
                      )}
                      <span>{meeting.location}</span>
                    </div>
                  </div>
                  
                  <div className="text-sm text-gray-600 mb-4">
                    {meeting.description}
                  </div>
                  
                  <div className="pt-4 border-t border-gray-100">
                    <div className="flex items-center justify-between">
                      <div className="text-xs text-gray-400">
                        {meeting.type.charAt(0).toUpperCase() + meeting.type.slice(1).replace('_', ' ')}
                      </div>
                      <div className="flex space-x-2">
                        <button className="text-sm text-gray-600 hover:text-black transition-colors">
                          Reschedule
                        </button>
                        <button className="text-sm text-gray-600 hover:text-black transition-colors">
                          Join Meeting
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
                Schedule meetings with prospects to discuss their event requirements
              </p>
              <button className="flex items-center space-x-2 px-4 py-2 bg-black text-white hover:bg-gray-900 rounded-lg transition-colors duration-200 mx-auto">
                <Plus className="h-4 w-4" />
                <span className="text-sm font-medium">Schedule Your First Meeting</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}