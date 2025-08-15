import { Target, Mail, Phone, MapPin, Star, User } from 'lucide-react'

// Mock prospect data
const prospects = [
  {
    id: 1,
    name: 'Sarah Johnson',
    company: 'Tech Corp',
    email: 'sarah.j@techcorp.com',
    phone: '+1 (555) 123-4567',
    location: 'San Francisco, CA',
    eventType: 'Corporate Event',
    leadScore: 85,
    status: 'enriched',
    source: 'LinkedIn',
    notes: 'Looking for Q4 team building event, budget $15k-25k'
  },
  {
    id: 2,
    name: 'Mike Chen',
    company: 'Startup Inc',
    email: 'mike@startup.inc',
    location: 'Austin, TX', 
    eventType: 'Product Launch',
    leadScore: 92,
    status: 'contacted',
    source: 'Web Search',
    notes: 'Product launch event for 200+ attendees'
  },
  {
    id: 3,
    name: 'Emily Rodriguez',
    company: 'Personal',
    email: 'emily.r.wedding@gmail.com',
    location: 'Miami, FL',
    eventType: 'Wedding',
    leadScore: 78,
    status: 'discovered',
    source: 'Social Media',
    notes: 'Beach wedding, 150 guests, summer 2024'
  },
]

export default function Prospects() {
  return (
    <div className="h-screen bg-white">
      <div className="max-w-4xl mx-auto px-6 py-6">
        <div className="space-y-8">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-black">Prospects</h1>
              <p className="mt-1 text-gray-500">
                AI-discovered prospects and their event requirements
              </p>
            </div>
            <button className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors duration-200">
              <Target className="h-4 w-4" />
              <span className="text-sm font-medium">Run Hunter Agent</span>
            </button>
          </div>

          {/* Prospects List */}
          <div className="space-y-4">
            {prospects.map((prospect) => (
              <div key={prospect.id} className="border border-gray-200 rounded-xl bg-white">
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center space-x-4">
                      <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center">
                        <User className="h-6 w-6 text-gray-600" />
                      </div>
                      <div>
                        <h3 className="font-medium text-black">{prospect.name}</h3>
                        <p className="text-sm text-gray-500">{prospect.company} • {prospect.eventType}</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <div className="flex items-center space-x-1">
                        <Star className="h-4 w-4 text-gray-400" />
                        <span className="text-sm font-medium">{prospect.leadScore}</span>
                      </div>
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        prospect.status === 'contacted' ? 'bg-black text-white' :
                        prospect.status === 'enriched' ? 'bg-gray-100 text-black' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {prospect.status}
                      </span>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-6 text-sm">
                    <div className="space-y-2">
                      {prospect.email && (
                        <div className="flex items-center space-x-2 text-gray-600">
                          <Mail className="h-4 w-4" />
                          <span>{prospect.email}</span>
                        </div>
                      )}
                      {prospect.phone && (
                        <div className="flex items-center space-x-2 text-gray-600">
                          <Phone className="h-4 w-4" />
                          <span>{prospect.phone}</span>
                        </div>
                      )}
                      <div className="flex items-center space-x-2 text-gray-600">
                        <MapPin className="h-4 w-4" />
                        <span>{prospect.location}</span>
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-500 text-xs mb-2">AI Notes:</div>
                      <div className="text-gray-600 mb-2">{prospect.notes}</div>
                      <div className="text-gray-400 text-xs">Source: {prospect.source}</div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Empty State */}
          {prospects.length === 0 && (
            <div className="text-center py-12">
              <Target className="h-12 w-12 mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-black mb-2">No prospects discovered yet</h3>
              <p className="text-gray-500 mb-6">
                Let the Hunter Agent find potential clients for you
              </p>
              <button className="flex items-center space-x-2 px-4 py-2 bg-black text-white hover:bg-gray-900 rounded-lg transition-colors duration-200 mx-auto">
                <Target className="h-4 w-4" />
                <span className="text-sm font-medium">Start Prospect Hunt</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}