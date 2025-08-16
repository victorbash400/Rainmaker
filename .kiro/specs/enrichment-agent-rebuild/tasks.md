# Implementation Plan

- [x] 1. Create new enrichment agent with LangGraph integration




  - Rebuild enrichment agent to integrate with existing LangGraph workflow
  - Use Sonar API for research and Gemini for analysis with real-time reasoning display
  - Implement no-fallback error handling that halts on critical failures
  - _Requirements: 1.1, 1.2, 4.1, 4.2_

- [x] 1.1 Rebuild EnrichmentAgent class



  - Rewrite `Rainmaker-backend/app/agents/enrichment.py` with simple structure
  - Implement `enrich_prospect` method that receives RainmakerState from workflow
  - Add WebSocket broadcasting for AI reasoning using existing orchestrator
  - Create basic error handling that uses StateManager.add_error (no fallbacks)
  - _Requirements: 1.1, 1.2, 6.1, 8.4_

- [x] 1.2 Update workflow integration


  - Modify `_enrichment_node` in `Rainmaker-backend/app/services/workflow.py`
  - Update `_route_from_enricher` to handle new enrichment agent responses
  - Test basic workflow: hunter → enricher → outreach handoff
  - _Requirements: 1.3, 7.1_

- [-] 2. Rebuild web search MCP for Sonar API



  - Replace existing web search with clean Sonar API integration
  - Remove all hardcoded patterns and mock data from current implementation
  - Add simple search methods for prospect research
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 2.1 Rewrite WebSearchMCP for Sonar


  - Completely rewrite `Rainmaker-backend/app/mcp/web_search.py`
  - Implement clean Sonar API integration with proper authentication
  - Add basic search methods: search_person, search_company, search_event_context
  - Remove all existing hardcoded search patterns and mock results
  - _Requirements: 3.1, 3.2_


- [ ] 2.2 Add event planning focused searches












  - Create search queries that find event planning context and preferences
  - Implement budget indicator searches and social presence analysis
  - Add simple result parsing that structures data for Gemini analysis
  - _Requirements: 3.2, 3.3_

- [ ] 3. Implement Gemini reasoning integration
  - Use existing Gemini service to analyze research data with step-by-step thinking
  - Broadcast AI reasoning to frontend in real-time
  - Create simple prompts for event planning context analysis
  - _Requirements: 4.1, 4.2, 4.3_

- [ ] 3.1 Add Gemini analysis with reasoning
  - Create analysis methods that use existing `gemini_service`
  - Implement step-by-step reasoning that explains AI decisions
  - Add WebSocket broadcasting of reasoning steps to frontend
  - Create simple prompts focused on event planning insights
  - _Requirements: 4.2, 4.3, 6.2_

- [ ] 3.2 Implement no-fallback error handling
  - Add strict error handling - halt immediately on Gemini or Sonar failures
  - Use StateManager.add_error to report failures to workflow
  - Remove any fallback logic or alternative approaches
  - _Requirements: 4.6, 8.4, 8.5_

- [ ] 4. Create simple enrichment data structure
  - Design basic data structure for enriched prospect information
  - Focus on event planning context, preferences, and basic insights
  - Remove complex confidence scoring and validation systems
  - _Requirements: 5.1, 5.2_

- [ ] 4.1 Implement basic EnrichmentData model
  - Create simple data structure in existing `app/core/state.py` or new file
  - Include basic fields: personal_info, company_info, event_context, ai_insights
  - Add simple serialization for database storage
  - Remove confidence scoring and complex validation
  - _Requirements: 5.1, 5.2_

- [ ] 5. Add mock data for testing
  - Create simple mock prospect data with real people/companies for testing
  - Test enrichment agent with mock data using real Sonar API calls
  - Validate that research produces useful event planning insights
  - _Requirements: 2.1, 2.2, 2.3_

- [ ] 5.1 Create mock prospect test data
  - Add 3-4 mock prospects with real names/companies for testing
  - Include different event types: wedding, corporate event, birthday party
  - Test enrichment process with mock data using real API calls
  - _Requirements: 2.1, 2.2_

- [ ] 6. Update frontend for enrichment reasoning display
  - Modify existing components to show enrichment AI reasoning
  - Add simple research progress display
  - Handle new WebSocket message types for enrichment updates
  - _Requirements: 6.1, 6.2, 6.3_

- [ ] 6.1 Update frontend components for enrichment
  - Modify existing AIThoughtProcess component to handle enrichment reasoning
  - Add simple research dashboard showing current search and findings
  - Update WebSocket handling for enrichment-specific messages
  - _Requirements: 6.1, 6.2, 6.4_

- [ ] 7. Basic testing and integration
  - Test complete enrichment flow with mock data
  - Verify WebSocket updates reach frontend correctly
  - Test error scenarios (API failures) and workflow handling
  - _Requirements: 2.4, 8.1_

- [ ] 7.1 Test enrichment agent integration
  - Test end-to-end: prospect data → Sonar research → Gemini analysis → enriched profile
  - Verify WebSocket reasoning updates display correctly in frontend
  - Test error handling: Sonar API failure and Gemini failure scenarios
  - _Requirements: 2.4, 8.1, 8.5_