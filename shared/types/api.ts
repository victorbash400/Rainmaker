// Shared API types for Rainmaker

export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  success: boolean;
}

export interface ApiError {
  error_code: string;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
  request_id: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface ProspectData {
  id: number;
  prospect_type: 'individual' | 'company';
  name: string;
  email?: string;
  phone?: string;
  company_name?: string;
  location?: string;
  source: string;
  status: ProspectStatus;
  lead_score: number;
  assigned_to?: string;
  created_at: string;
  updated_at: string;
}

export type ProspectStatus = 
  | 'discovered' 
  | 'enriched' 
  | 'contacted' 
  | 'interested' 
  | 'qualified' 
  | 'converted' 
  | 'lost';

export interface CampaignData {
  id: number;
  prospect_id: number;
  channel: 'email' | 'linkedin' | 'phone' | 'in_person';
  campaign_type: string;
  subject_line?: string;
  message_body: string;
  status: CampaignStatus;
  sent_at?: string;
  opened_at?: string;
  replied_at?: string;
  created_at: string;
}

export type CampaignStatus = 
  | 'draft' 
  | 'pending_approval' 
  | 'approved' 
  | 'sent' 
  | 'opened' 
  | 'replied' 
  | 'bounced' 
  | 'rejected';

export interface ConversationData {
  id: number;
  prospect_id: number;
  channel: 'email' | 'chat' | 'phone' | 'in_person';
  conversation_summary?: string;
  extracted_requirements?: Record<string, any>;
  sentiment_score?: number;
  qualification_score: number;
  next_action?: string;
  created_at: string;
  updated_at: string;
}

export interface MessageData {
  id: number;
  conversation_id: number;
  sender_type: 'prospect' | 'agent' | 'human';
  sender_name?: string;
  message_content: string;
  message_type: 'text' | 'email' | 'attachment' | 'system';
  metadata?: Record<string, any>;
  created_at: string;
}

export interface ProposalData {
  id: number;
  prospect_id: number;
  proposal_name: string;
  total_price: number;
  guest_count: number;
  event_date: string;
  venue_details?: Record<string, any>;
  package_details?: Record<string, any>;
  terms_conditions?: string;
  proposal_pdf_url?: string;
  mood_board_url?: string;
  status: ProposalStatus;
  valid_until: string;
  created_at: string;
  updated_at: string;
}

export type ProposalStatus = 
  | 'draft' 
  | 'pending_approval' 
  | 'sent' 
  | 'viewed' 
  | 'accepted' 
  | 'rejected' 
  | 'negotiating' 
  | 'expired';

export interface MeetingData {
  id: number;
  prospect_id: number;
  meeting_type: 'initial_call' | 'venue_visit' | 'planning_session' | 'final_walkthrough';
  title: string;
  description?: string;
  scheduled_at: string;
  duration_minutes: number;
  location?: string;
  meeting_url?: string;
  calendar_event_id?: string;
  attendees?: Record<string, any>;
  agenda?: string;
  notes?: string;
  status: MeetingStatus;
  created_at: string;
  updated_at: string;
}

export type MeetingStatus = 
  | 'scheduled' 
  | 'confirmed' 
  | 'completed' 
  | 'cancelled' 
  | 'rescheduled';