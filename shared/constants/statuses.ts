// Status-related constants for Rainmaker

export const PROSPECT_STATUSES = {
  DISCOVERED: 'discovered',
  ENRICHED: 'enriched',
  CONTACTED: 'contacted',
  INTERESTED: 'interested',
  QUALIFIED: 'qualified',
  CONVERTED: 'converted',
  LOST: 'lost'
} as const;

export const PROSPECT_STATUS_LABELS = {
  [PROSPECT_STATUSES.DISCOVERED]: 'Discovered',
  [PROSPECT_STATUSES.ENRICHED]: 'Enriched',
  [PROSPECT_STATUSES.CONTACTED]: 'Contacted',
  [PROSPECT_STATUSES.INTERESTED]: 'Interested',
  [PROSPECT_STATUSES.QUALIFIED]: 'Qualified',
  [PROSPECT_STATUSES.CONVERTED]: 'Converted',
  [PROSPECT_STATUSES.LOST]: 'Lost'
} as const;

export const PROSPECT_STATUS_COLORS = {
  [PROSPECT_STATUSES.DISCOVERED]: 'bg-gray-100 text-gray-800',
  [PROSPECT_STATUSES.ENRICHED]: 'bg-blue-100 text-blue-800',
  [PROSPECT_STATUSES.CONTACTED]: 'bg-yellow-100 text-yellow-800',
  [PROSPECT_STATUSES.INTERESTED]: 'bg-orange-100 text-orange-800',
  [PROSPECT_STATUSES.QUALIFIED]: 'bg-green-100 text-green-800',
  [PROSPECT_STATUSES.CONVERTED]: 'bg-emerald-100 text-emerald-800',
  [PROSPECT_STATUSES.LOST]: 'bg-red-100 text-red-800'
} as const;

export const CAMPAIGN_STATUSES = {
  DRAFT: 'draft',
  PENDING_APPROVAL: 'pending_approval',
  APPROVED: 'approved',
  SENT: 'sent',
  OPENED: 'opened',
  REPLIED: 'replied',
  BOUNCED: 'bounced',
  REJECTED: 'rejected'
} as const;

export const CAMPAIGN_STATUS_LABELS = {
  [CAMPAIGN_STATUSES.DRAFT]: 'Draft',
  [CAMPAIGN_STATUSES.PENDING_APPROVAL]: 'Pending Approval',
  [CAMPAIGN_STATUSES.APPROVED]: 'Approved',
  [CAMPAIGN_STATUSES.SENT]: 'Sent',
  [CAMPAIGN_STATUSES.OPENED]: 'Opened',
  [CAMPAIGN_STATUSES.REPLIED]: 'Replied',
  [CAMPAIGN_STATUSES.BOUNCED]: 'Bounced',
  [CAMPAIGN_STATUSES.REJECTED]: 'Rejected'
} as const;

export const PROPOSAL_STATUSES = {
  DRAFT: 'draft',
  PENDING_APPROVAL: 'pending_approval',
  SENT: 'sent',
  VIEWED: 'viewed',
  ACCEPTED: 'accepted',
  REJECTED: 'rejected',
  NEGOTIATING: 'negotiating',
  EXPIRED: 'expired'
} as const;

export const PROPOSAL_STATUS_LABELS = {
  [PROPOSAL_STATUSES.DRAFT]: 'Draft',
  [PROPOSAL_STATUSES.PENDING_APPROVAL]: 'Pending Approval',
  [PROPOSAL_STATUSES.SENT]: 'Sent',
  [PROPOSAL_STATUSES.VIEWED]: 'Viewed',
  [PROPOSAL_STATUSES.ACCEPTED]: 'Accepted',
  [PROPOSAL_STATUSES.REJECTED]: 'Rejected',
  [PROPOSAL_STATUSES.NEGOTIATING]: 'Negotiating',
  [PROPOSAL_STATUSES.EXPIRED]: 'Expired'
} as const;

export const MEETING_STATUSES = {
  SCHEDULED: 'scheduled',
  CONFIRMED: 'confirmed',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
  RESCHEDULED: 'rescheduled'
} as const;

export const MEETING_STATUS_LABELS = {
  [MEETING_STATUSES.SCHEDULED]: 'Scheduled',
  [MEETING_STATUSES.CONFIRMED]: 'Confirmed',
  [MEETING_STATUSES.COMPLETED]: 'Completed',
  [MEETING_STATUSES.CANCELLED]: 'Cancelled',
  [MEETING_STATUSES.RESCHEDULED]: 'Rescheduled'
} as const;

export const AGENT_NAMES = {
  PROSPECT_HUNTER: 'prospect_hunter',
  ENRICHMENT: 'enrichment',
  OUTREACH: 'outreach',
  CONVERSATION: 'conversation',
  PROPOSAL: 'proposal',
  MEETING: 'meeting'
} as const;

export const AGENT_LABELS = {
  [AGENT_NAMES.PROSPECT_HUNTER]: 'Prospect Hunter',
  [AGENT_NAMES.ENRICHMENT]: 'Enrichment Agent',
  [AGENT_NAMES.OUTREACH]: 'Outreach Agent',
  [AGENT_NAMES.CONVERSATION]: 'Conversation Agent',
  [AGENT_NAMES.PROPOSAL]: 'Proposal Agent',
  [AGENT_NAMES.MEETING]: 'Meeting Agent'
} as const;