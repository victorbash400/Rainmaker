import structlog
from typing import Dict, Any

from app.core.state import RainmakerState, OutreachCampaign
from app.services.gemini_service import gemini_service
from app.mcp.email_mcp import email_mcp
from app.db.models import CampaignStatus

logger = structlog.get_logger(__name__)

class OutreachAgent:
    """An agent to draft and send personalized outreach emails."""

    def _format_enrichment_data(self, enrichment) -> str:
        """Format enrichment data for use in the email prompt."""
        if not enrichment or not hasattr(enrichment, 'ai_insights') or not enrichment.ai_insights:
            return "No specific enrichment data available."
        
        ai_insights = enrichment.ai_insights
        formatted_data = []
        
        # Add company information
        if 'company' in ai_insights:
            company_info = ai_insights['company']
            if isinstance(company_info, dict):
                if 'name' in company_info:
                    formatted_data.append(f"Company: {company_info['name']}")
                if 'industry' in company_info:
                    formatted_data.append(f"Industry: {company_info['industry']}")
                if 'size' in company_info:
                    formatted_data.append(f"Company Size: {company_info['size']}")
        
        # Add event indicators
        if 'event_indicators' in ai_insights:
            event_info = ai_insights['event_indicators']
            if isinstance(event_info, dict):
                if 'event_types' in event_info and event_info['event_types']:
                    formatted_data.append(f"Event Types: {', '.join(event_info['event_types'])}")
                if 'event_frequency' in event_info:
                    formatted_data.append(f"Event Frequency: {event_info['event_frequency']}")
                if 'budget_indicators' in event_info:
                    formatted_data.append(f"Budget Indicators: {event_info['budget_indicators']}")
        
        # Add key insights
        if 'key_insights' in ai_insights:
            insights = ai_insights['key_insights']
            if isinstance(insights, list) and insights:
                formatted_data.append("Key Insights:")
                for insight in insights[:3]:  # Limit to top 3 insights
                    if isinstance(insight, str):
                        formatted_data.append(f"  - {insight}")
                    elif isinstance(insight, dict):
                        formatted_data.append(f"  - {insight.get('description', insight.get('summary', str(insight)))}")
        
        # Add recent news or activities
        if 'recent_news' in ai_insights:
            news = ai_insights['recent_news']
            if isinstance(news, list) and news:
                formatted_data.append("Recent News:")
                for item in news[:2]:  # Limit to 2 recent items
                    if isinstance(item, dict):
                        title = item.get('title', 'Untitled')
                        formatted_data.append(f"  - {title}")
        
        return "\n".join(formatted_data) if formatted_data else "No specific enrichment data available."

    async def execute_outreach(self, state: RainmakerState) -> RainmakerState:
        """Executes the outreach process for a given prospect."""
        workflow_id = state.get("workflow_id")
        prospect_name = state.get("prospect_data", {}).name if state.get("prospect_data") else "Unknown"
        
        print(f"🚀 OUTREACH AGENT: Starting outreach execution for {prospect_name}")
        print(f"   Workflow ID: {workflow_id}")
        print(f"   Call stack info: This is the REAL outreach agent, not UI simulation")
        
        logger.info("Starting outreach execution", workflow_id=workflow_id, prospect_name=prospect_name)

        enrichment_data = state.get("enrichment_data")
        prospect_data = state.get("prospect_data")

        if not enrichment_data or not prospect_data:
            logger.warning("Missing enrichment or prospect data. Skipping outreach.")
            return state

        try:
            # Update stage to composing for UI feedback
            from app.core.state import StateManager, WorkflowStage
            state = StateManager.update_stage(state, WorkflowStage.OUTREACH)
            
            # Save state to make stage update available to frontend
            from app.core.persistence import persistence_manager
            persistence_manager.save_state(workflow_id, state)
            
            # 1. Draft email using Gemini
            draft = await self._draft_email_with_gemini(prospect_data, enrichment_data)

            # 2. Send the email via EmailMCP
            # For the demo, we'll send to the prospect's real email address.
            # Ensure your .env is configured to send from one address and receive at another.
            print(f"📧 REAL EMAIL SENDING: To {prospect_data.email}")
            print(f"   Subject: {draft['subject']}")
            print(f"   This is NOT a UI simulation - actual email will be sent!")
            
            logger.info(f"Sending email to {prospect_data.email}...")
            result = email_mcp.send_email(
                to=prospect_data.email,
                subject=draft["subject"],
                body=draft["body"]
            )
            
            print(f"✅ REAL EMAIL SENT: Result = {result}")
            logger.info(f"Email sent successfully to {prospect_data.email}")

            # 3. Update state with campaign info as dict for better serialization
            from datetime import datetime
            campaign_dict = {
                "channel": "email",
                "campaign_type": "initial_outreach",
                "subject_line": draft["subject"],
                "message_body": draft["body"],
                "personalization_data": enrichment_data.ai_insights if enrichment_data else {},
                "status": "sent" if result["status"] == "success" else "failed",
                "sent_at": datetime.now().isoformat() if result["status"] == "success" else None,
                "thread_id": f"thread_{prospect_data.email}_{state.get('workflow_id')}",
                "message_id": result.get("message_id")
            }
            state["outreach_campaigns"] = state.get("outreach_campaigns", []) + [campaign_dict]
            logger.info("Successfully logged outreach campaign to state.")

        except Exception as e:
            logger.error("Outreach agent failed", error=str(e), workflow_id=state.get("workflow_id"))
            # Optionally add error to state

        return state

    async def handle_prospect_reply(self, state: RainmakerState, reply: Dict[str, Any]) -> RainmakerState:
        """Analyzes a prospect's reply and updates the state accordingly."""
        logger.info("Handling prospect reply", workflow_id=state.get("workflow_id"))
        reply_body = reply.get("body", "")

        system_prompt = (
            "You are a sales assistant responsible for analyzing incoming email replies from prospects. "
            "Your goal is to determine the prospect's intent and extract key information. "
            "Classify the intent into one of the following categories: [INTERESTED, NOT_INTERESTED, QUESTION, OUT_OF_OFFICE, REQUEST_CALLBACK]."
        )

        user_message = f"""
        Analyze the following email reply and classify the sender's intent. Provide a brief summary of their message.

        **Email Reply:**
        {reply_body}

        **Instructions:**
        Return ONLY a valid JSON object with two keys: "intent" and "summary".

        Example Response:
        {{
            "intent": "INTERESTED",
            "summary": "The prospect is asking for pricing information and our portfolio."
        }}
        """

        try:
            analysis = await gemini_service.generate_json_response(
                system_prompt=system_prompt,
                user_message=user_message
            )
            logger.info("Successfully analyzed reply", intent=analysis.get("intent"))

            # Here, we would update the state based on the intent.
            # For now, we'll just log it to the conversation summary for review.
            # This logic will be integrated into the main orchestrator later.
            state["conversation_summary"] = {
                "last_reply_body": reply_body,
                "last_reply_intent": analysis.get("intent"),
                "last_reply_summary": analysis.get("summary")
            }

        except Exception as e:
            logger.error("Failed to handle prospect reply", error=str(e))

        return state

    async def _draft_email_with_gemini(self, prospect, enrichment) -> Dict[str, str]:
        """Constructs a prompt and uses Gemini to draft a personalized email.""" 

        logger.info(f"Drafting email for {prospect.name}")  
        
        # Check if we have real enrichment data
        has_real_enrichment = enrichment and hasattr(enrichment, 'ai_insights') and enrichment.ai_insights
        
        if has_real_enrichment:
            logger.info(
                "Using real enrichment data for outreach",
                prospect_name=prospect.name,
                enrichment_received=True
            )
        else:
            logger.info(
                "No enrichment data available, using basic prospect info",
                prospect_name=prospect.name,
                enrichment_received=False
            )

        system_prompt = (
            "You are an expert sales development representative for Rainmaker, an elite event planning company. "
            "Your task is to write a personalized, concise, and compelling cold outreach email to a prospect. "
            "The tone should be professional yet approachable. The goal is to introduce Rainmaker's services "
            "and start a conversation about their event planning needs. "
            "Create a well-formatted email without markdown or special characters like asterisks. "
            "Use proper email formatting with clear paragraphs. "
            "End with a clear, low-friction call to action."
        )

        # Use real enrichment data if available, otherwise use basic prospect info
        if has_real_enrichment:
            user_message = f"""
            Please draft a cold outreach email for Rainmaker Event Planning services.

            **Prospect Information:**
            - Name: {prospect.name}
            - Company: {prospect.company_name or 'Unknown Company'}
            - Email: {prospect.email}

            **Enrichment Insights:**
            {self._format_enrichment_data(enrichment)}

            **Instructions:**
            Create a professional outreach email that:
            1. References relevant information from the enrichment insights to show you've done your research
            2. Briefly introduces Rainmaker as an event planning company
            3. Mentions how you can help with their specific event needs
            4. Keeps it concise (3-4 short paragraphs maximum)
            5. Uses a friendly but professional tone
            6. Ends with a clear call to action (asking to connect or discuss their upcoming events)
            7. Does NOT use markdown, asterisks, or special formatting characters
            8. Ensures all newlines are properly escaped as \n in the JSON response

            Return ONLY a valid JSON object with two keys: "subject" and "body".
            Make sure the JSON is properly formatted with escaped newlines.
            Do not include any other text, greetings, or explanations outside of the JSON.

            Example Response:
            {{
                "subject": "Event Planning Services for {prospect.company_name or 'Your Upcoming Events'}",
                "body": "Hi {prospect.name},\n\nI noticed that...\n\nBest regards,\n[Your Name]"
            }}
            """
        else:
            # Fallback to basic prospect info
            user_message = f"""
            Please draft a cold outreach email for Rainmaker Event Planning services.

            **Prospect Information:**
            - Name: {prospect.name}
            - Company: {prospect.company_name or 'Unknown Company'}
            - Email: {prospect.email}

            **Instructions:**
            Create a professional outreach email that:
            1. Briefly introduces Rainmaker as an event planning company
            2. Mentions how you can help with corporate events, networking events, or client appreciation events
            3. Keeps it concise (3-4 short paragraphs maximum)
            4. Uses a friendly but professional tone
            5. Ends with a clear call to action (asking to connect or discuss their event needs)
            6. Does NOT use markdown, asterisks, or special formatting characters
            7. Ensures all newlines are properly escaped as \n in the JSON response

            Return ONLY a valid JSON object with two keys: "subject" and "body".
            Make sure the JSON is properly formatted with escaped newlines.
            Do not include any other text, greetings, or explanations outside of the JSON.

            Example Response:
            {{
                "subject": "Professional Event Planning Services for {prospect.company_name or 'Your Team'}",
                "body": "Hi {prospect.name},

I'm reaching out from Rainmaker...

Best regards,
[Your Name]"
            }}
            """

        response_json = await gemini_service.generate_json_response(
            system_prompt=system_prompt,
            user_message=user_message
        )

        if not response_json or "subject" not in response_json or "body" not in response_json:
            logger.error("Failed to get valid email draft from Gemini.")
            raise ValueError("Invalid response from Gemini service.")

        logger.info(f"Successfully drafted email for {prospect.name}")
        return response_json

    async def draft_overview_request_email(self, prospect, original_campaign) -> Dict[str, str]:
        """Drafts a follow-up email asking for event overview after positive initial response."""
        
        logger.info(f"Drafting overview request email for {prospect.name}")
        
        system_prompt = (
            "You are an expert event planning sales representative following up after receiving a positive initial response. "
            "Your task is to write a professional follow-up email asking for event overview details. "
            "The tone should be enthusiastic yet professional. You want to gather key event information "
            "to create a customized proposal. Keep it concise and focused. "
            "Reference the previous conversation naturally. "
            "Create a well-formatted email without markdown or special characters like asterisks. "
            "Use proper email formatting with clear paragraphs."
        )

        # Extract information from the original campaign
        original_subject = original_campaign.get("subject_line", "our previous conversation") if isinstance(original_campaign, dict) else "our previous conversation"
        original_body_preview = original_campaign.get("message_body", "")[:100] if isinstance(original_campaign, dict) else ""

        user_message = f"""
        Please draft a follow-up email requesting event overview details.

        **Prospect Information:**
        - Name: {prospect.name}
        - Company: {prospect.company_name or 'Unknown Company'}
        - Email: {prospect.email}

        **Previous Conversation Context:**
        - Original Subject: {original_subject}
        - We've already established contact and the prospect is interested in our services
        
        **Email Purpose:**
        Ask for an overview of their event needs including:
        - Event type and purpose
        - Approximate date and timeline
        - Expected guest count
        - Budget range (if comfortable sharing)
        - Any specific requirements or vision

        **Instructions:**
        Create a professional follow-up email that:
        1. References the previous conversation naturally (don't explicitly mention "as per our previous email")
        2. Thanks them for their positive response and interest
        3. Expresses enthusiasm about working together on their event
        4. Asks for key event details in a non-overwhelming way
        5. Suggests a brief call or detailed email response
        6. Maintains a relationship-building tone
        7. Does NOT use markdown, asterisks, or special formatting characters
        8. Keeps it concise (3-4 short paragraphs maximum)
        9. Ensures all newlines are properly escaped as \n in the JSON response

        Return ONLY a valid JSON object with two keys: "subject" and "body".
        Make sure the JSON is properly formatted with escaped newlines.
        Use "Re: " prefix in subject to maintain email thread.

        Example Response:
        {{
            "subject": "Re: Event Planning Partnership - Next Steps",
            "body": "Hi {prospect.name},\n\nThank you for your interest in Rainmaker...\n\nBest regards,\n[Your Name]"
        }}
        """

        response_json = await gemini_service.generate_json_response(
            system_prompt=system_prompt,
            user_message=user_message
        )

        if not response_json or "subject" not in response_json or "body" not in response_json:
            logger.error("Failed to get valid overview request email from Gemini.")
            raise ValueError("Invalid response from Gemini service.")

        logger.info(f"Successfully drafted overview request email for {prospect.name}")
        return response_json

    async def send_overview_request(self, state: RainmakerState) -> RainmakerState:
        """Sends follow-up email requesting event overview details."""
        logger.info("Sending overview request email", workflow_id=state.get("workflow_id"))
        
        prospect_data = state.get("prospect_data")
        original_campaigns = state.get("outreach_campaigns", [])
        
        if not prospect_data or not original_campaigns:
            logger.warning("Missing prospect data or original campaign. Cannot send overview request.")
            return state
            
        try:
            # Get the most recent campaign to maintain thread
            original_campaign = original_campaigns[-1]
            
            # Draft overview request email
            draft = await self.draft_overview_request_email(prospect_data, original_campaign)
            
            # Send the follow-up email with thread tracking
            thread_id = f"thread_{prospect_data.email}_{state.get('workflow_id')}"
            logger.info(f"Sending overview request email to {prospect_data.email}...")
            result = email_mcp.send_email(
                to=prospect_data.email,
                subject=draft["subject"],
                body=draft["body"],
                thread_id=thread_id
            )
            
            # Create new campaign record for the follow-up as dict
            from datetime import datetime
            follow_up_campaign_dict = {
                "channel": "email",
                "campaign_type": "overview_request",
                "subject_line": draft["subject"],
                "message_body": draft["body"],
                "personalization_data": {"original_campaign_type": original_campaign.get("campaign_type") if isinstance(original_campaign, dict) else "initial_outreach"},
                "status": "sent" if result["status"] == "success" else "failed",
                "sent_at": datetime.now().isoformat() if result["status"] == "success" else None,
                "thread_id": result.get("thread_id", thread_id),
                "message_id": result.get("message_id"),
                "parent_campaign_type": original_campaign.get("campaign_type") if isinstance(original_campaign, dict) else "initial_outreach"
            }
            
            # Add to campaigns list
            state["outreach_campaigns"] = original_campaigns + [follow_up_campaign_dict]
            logger.info("Successfully sent overview request email and logged to state.")
            
        except Exception as e:
            logger.error("Failed to send overview request", error=str(e), workflow_id=state.get("workflow_id"))
            # Add error to state for debugging
            state["last_error"] = f"Overview request failed: {str(e)}"
            
        return state

    async def send_proposal_email(self, state: RainmakerState, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """Sends proposal email with PDF attachment and meeting request."""
        logger.info("Starting proposal email send", workflow_id=state.get("workflow_id"))
        
        prospect_data = state.get("prospect_data")
        logger.info("Prospect data check", has_prospect_data=bool(prospect_data), prospect_data_type=type(prospect_data).__name__ if prospect_data else None)
        
        if not prospect_data:
            logger.warning("Missing prospect data. Cannot send proposal email.")
            raise ValueError("Missing prospect data")
            
        try:
            # Draft proposal email
            logger.info("Drafting proposal email...")
            draft = await self._draft_proposal_email(prospect_data, proposal)
            logger.info("Email draft completed", subject=draft.get("subject", "")[:50] if draft else "No draft")
            
            # Send the proposal email with PDF attachment
            prospect_email = getattr(prospect_data, 'email', '')
            logger.info("Extracted prospect email", prospect_email=prospect_email, has_email=bool(prospect_email))
            
            thread_id = f"thread_{prospect_email}_{state.get('workflow_id')}"
            logger.info(f"Sending proposal email to {prospect_email}...", thread_id=thread_id)
            
            # Prepare attachment info
            pdf_path = proposal.get("pdf_file_path")
            logger.info("PDF attachment info", pdf_path=pdf_path, pdf_exists=bool(pdf_path))
            
            attachment = None
            if pdf_path:
                import os
                pdf_exists_on_disk = os.path.exists(pdf_path)
                logger.info("PDF file check", pdf_path=pdf_path, exists_on_disk=pdf_exists_on_disk)
                
                attachment = {
                    "filename": f"{proposal.get('proposal_id', 'proposal')}.pdf",
                    "path": pdf_path,
                    "content_type": "application/pdf"
                }
                logger.info("Attachment prepared", attachment_filename=attachment["filename"])
            else:
                logger.warning("No PDF path found in proposal data")
            
            logger.info("Calling email_mcp.send_email", to=prospect_email, has_attachment=bool(attachment))
            result = email_mcp.send_email(
                to=prospect_email,
                subject=draft["subject"],
                body=draft["body"],
                thread_id=thread_id,
                attachment_path=attachment["path"] if attachment else None,
                attachment_filename=attachment["filename"] if attachment else None
            )
            logger.info("Email send result", result_status=result.get("status"), result_keys=list(result.keys()) if result else None)
            
            # Return result with email details
            from datetime import datetime
            return {
                "status": "success" if result["status"] == "success" else "failed",
                "sent_at": datetime.now().isoformat() if result["status"] == "success" else None,
                "subject_line": draft["subject"],
                "message_id": result.get("message_id"),
                "thread_id": result.get("thread_id", thread_id)
            }
            
        except Exception as e:
            logger.error("Failed to send proposal email", error=str(e), error_type=type(e).__name__, workflow_id=state.get("workflow_id"))
            import traceback
            logger.error("Full traceback for proposal email failure", traceback=traceback.format_exc())
            raise

    async def _draft_proposal_email(self, prospect, proposal: Dict[str, Any]) -> Dict[str, str]:
        """Drafts a professional proposal email with meeting request."""
        
        logger.info(f"Drafting proposal email for {prospect.name}")
        
        system_prompt = (
            "You are an expert event planning sales representative sending a customized proposal. "
            "Your task is to write a professional email that accompanies a PDF proposal attachment. "
            "The tone should be confident, professional, and enthusiastic. You want to schedule a meeting "
            "to discuss the proposal in detail. Include a clear call-to-action for scheduling a meeting. "
            "Do not use markdown formatting, asterisks, or special characters in your response."
        )

        user_message = f"""
        Please draft a proposal email with PDF attachment.

        Prospect Information:
        - Name: {prospect.name}
        - Company: {prospect.company_name or proposal.get('client_company', 'Your Company')}
        - Email: {prospect.email}

        Proposal Details:
        - Event Type: {proposal.get('event_type', 'Corporate Event')}
        - Total Investment: ${proposal.get('total_investment', 25000):,}
        - Proposal ID: {proposal.get('proposal_id', 'PROP_001')}

        Email Purpose:
        1. Introduce the attached customized proposal
        2. Highlight key benefits and value proposition
        3. Express enthusiasm about working together
        4. Request a meeting to discuss the proposal in detail
        5. Provide clear next steps

        Instructions:
        Create a professional proposal email that:
        1. Thanks them for providing event details
        2. Introduces the attached proposal with excitement
        3. Briefly highlights 2-3 key benefits/value points
        4. Requests a meeting to go through the proposal together
        5. Provides your contact information for scheduling
        6. Maintains a confident yet approachable tone

        Return ONLY a valid JSON object with two keys: "subject" and "body".
        Use "Re: " prefix in subject to maintain email thread.
        Mention the PDF attachment in the email body.
        Do not use markdown formatting, asterisks, or special characters in your response.

        Example Response:
        {{
            "subject": "Re: Your Event Proposal - Let's Schedule a Call",
            "body": "Hi {prospect.name}, I'm excited to share your customized event proposal..."
        }}
        """

        response_json = await gemini_service.generate_json_response(
            system_prompt=system_prompt,
            user_message=user_message
        )

        if not response_json or "subject" not in response_json or "body" not in response_json:
            logger.error("Failed to get valid proposal email from Gemini.")
            raise ValueError("Invalid response from Gemini service.")

        logger.info(f"Successfully drafted proposal email for {prospect.name}")
        return response_json