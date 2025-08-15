// Event-related constants for Rainmaker

export const EVENT_TYPES = {
  WEDDING: 'wedding',
  CORPORATE_EVENT: 'corporate_event',
  BIRTHDAY: 'birthday',
  ANNIVERSARY: 'anniversary',
  GRADUATION: 'graduation',
  OTHER: 'other'
} as const;

export const EVENT_TYPE_LABELS = {
  [EVENT_TYPES.WEDDING]: 'Wedding',
  [EVENT_TYPES.CORPORATE_EVENT]: 'Corporate Event',
  [EVENT_TYPES.BIRTHDAY]: 'Birthday Party',
  [EVENT_TYPES.ANNIVERSARY]: 'Anniversary',
  [EVENT_TYPES.GRADUATION]: 'Graduation',
  [EVENT_TYPES.OTHER]: 'Other Event'
} as const;

export const VENUE_TYPES = [
  'banquet_hall',
  'hotel',
  'restaurant',
  'outdoor_venue',
  'church',
  'beach',
  'garden',
  'conference_center',
  'country_club',
  'historic_venue',
  'rooftop',
  'warehouse',
  'other'
] as const;

export const VENUE_TYPE_LABELS = {
  banquet_hall: 'Banquet Hall',
  hotel: 'Hotel',
  restaurant: 'Restaurant',
  outdoor_venue: 'Outdoor Venue',
  church: 'Church',
  beach: 'Beach',
  garden: 'Garden',
  conference_center: 'Conference Center',
  country_club: 'Country Club',
  historic_venue: 'Historic Venue',
  rooftop: 'Rooftop',
  warehouse: 'Warehouse',
  other: 'Other'
} as const;

export const GUEST_COUNT_RANGES = [
  { min: 1, max: 25, label: '1-25 guests' },
  { min: 26, max: 50, label: '26-50 guests' },
  { min: 51, max: 100, label: '51-100 guests' },
  { min: 101, max: 200, label: '101-200 guests' },
  { min: 201, max: 500, label: '201-500 guests' },
  { min: 501, max: 1000, label: '501-1000 guests' },
  { min: 1001, max: null, label: '1000+ guests' }
] as const;

export const BUDGET_RANGES = [
  { min: 0, max: 5000, label: 'Under $5,000' },
  { min: 5000, max: 15000, label: '$5,000 - $15,000' },
  { min: 15000, max: 30000, label: '$15,000 - $30,000' },
  { min: 30000, max: 50000, label: '$30,000 - $50,000' },
  { min: 50000, max: 100000, label: '$50,000 - $100,000' },
  { min: 100000, max: null, label: '$100,000+' }
] as const;