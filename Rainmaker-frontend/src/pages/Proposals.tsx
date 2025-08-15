import { FileText, DollarSign, Calendar, Users, Plus } from 'lucide-react'

// Mock proposals data
const proposals = [
  {
    id: 1,
    title: 'Corporate Team Building - Tech Corp',
    prospect: 'Sarah Johnson',
    company: 'Tech Corp',
    eventType: 'Corporate Event',
    totalPrice: 25000,
    guestCount: 150,
    eventDate: '2024-12-15',
    status: 'sent',
    createdAt: '2 days ago',
    validUntil: '2024-11-30'
  },
  {
    id: 2,
    title: 'Product Launch Celebration',
    prospect: 'Mike Chen',
    company: 'Startup Inc',
    eventType: 'Product Launch',
    totalPrice: 35000,
    guestCount: 200,
    eventDate: '2024-11-20',
    status: 'approved',
    createdAt: '1 week ago',
    validUntil: '2024-11-15'
  },
  {
    id: 3,
    title: 'Elegant Beach Wedding',
    prospect: 'Emily Rodriguez',
    company: 'Personal',
    eventType: 'Wedding',
    totalPrice: 45000,
    guestCount: 120,
    eventDate: '2025-06-14',
    status: 'draft',
    createdAt: '3 days ago',
    validUntil: '2024-12-01'
  },
]

export default function Proposals() {
  return (
    <div className="h-screen bg-white">
      <div className="max-w-4xl mx-auto px-6 py-6">
        <div className="space-y-8">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-black">Proposals</h1>
              <p className="mt-1 text-gray-500">
                AI-generated event proposals and pricing
              </p>
            </div>
            <button className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors duration-200">
              <Plus className="h-4 w-4" />
              <span className="text-sm font-medium">Create Proposal</span>
            </button>
          </div>

          {/* Proposals List */}
          <div className="space-y-4">
            {proposals.map((proposal) => (
              <div key={proposal.id} className="border border-gray-200 rounded-xl bg-white">
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center space-x-4">
                      <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center">
                        <FileText className="h-6 w-6 text-gray-600" />
                      </div>
                      <div>
                        <h3 className="font-medium text-black">{proposal.title}</h3>
                        <p className="text-sm text-gray-500">{proposal.prospect} • {proposal.company}</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className="text-lg font-semibold text-black">
                        ${proposal.totalPrice.toLocaleString()}
                      </span>
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        proposal.status === 'approved' ? 'bg-black text-white' :
                        proposal.status === 'sent' ? 'bg-gray-100 text-black' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {proposal.status}
                      </span>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-6 text-sm">
                    <div className="flex items-center space-x-2 text-gray-600">
                      <Users className="h-4 w-4" />
                      <span>{proposal.guestCount} guests</span>
                    </div>
                    <div className="flex items-center space-x-2 text-gray-600">
                      <Calendar className="h-4 w-4" />
                      <span>{new Date(proposal.eventDate).toLocaleDateString()}</span>
                    </div>
                    <div className="text-gray-500">
                      <span className="text-xs">Valid until: </span>
                      <span>{new Date(proposal.validUntil).toLocaleDateString()}</span>
                    </div>
                  </div>
                  
                  <div className="mt-4 pt-4 border-t border-gray-100">
                    <div className="flex items-center justify-between">
                      <div className="text-xs text-gray-400">
                        Created {proposal.createdAt} • {proposal.eventType}
                      </div>
                      <div className="flex space-x-2">
                        <button className="text-sm text-gray-600 hover:text-black transition-colors">
                          Edit
                        </button>
                        <button className="text-sm text-gray-600 hover:text-black transition-colors">
                          Download PDF
                        </button>
                        <button className="text-sm text-gray-600 hover:text-black transition-colors">
                          Send
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Empty State */}
          {proposals.length === 0 && (
            <div className="text-center py-12">
              <FileText className="h-12 w-12 mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-black mb-2">No proposals yet</h3>
              <p className="text-gray-500 mb-6">
                Create your first event proposal from qualified conversations
              </p>
              <button className="flex items-center space-x-2 px-4 py-2 bg-black text-white hover:bg-gray-900 rounded-lg transition-colors duration-200 mx-auto">
                <Plus className="h-4 w-4" />
                <span className="text-sm font-medium">Create Your First Proposal</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}