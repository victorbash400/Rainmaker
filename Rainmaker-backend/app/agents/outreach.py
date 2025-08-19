import structlog
from typing import Dict, Any

from app.core.state import RainmakerState, OutreachCampaign
from app.services.gemini_service import gemini_service
from app.mcp.email_mcp import email_mcp
from app.db.models import CampaignStatus

logger = structlog.get_logger(__name__)

class OutreachAgent:
    """An agent to draft and send personalized outreach emails."""

    async def execute_outreach(self, state: RainmakerState) -> RainmakerState:
        """Executes the outreach process for a given prospect."""
        logger.info("Starting outreach execution", workflow_id=state.get("workflow_id"))

        enrichment_data = state.get("enrichment_data")
        prospect_data = state.get("prospect_data")

        if not enrichment_data or not prospect_data:
            logger.warning("Missing enrichment or prospect data. Skipping outreach.")
            return state

        try:
            # 1. Draft email using Gemini
            draft = await self._draft_email_with_gemini(prospect_data, enrichment_data)

            # 2. Send the email via EmailMCP
            # For the demo, we'll send to the prospect's real email address.
            # Ensure your .env is configured to send from one address and receive at another.
            logger.info(f"Sending email to {prospect_data.email}...")
            result = email_mcp.send_email(
                to=prospect_data.email,
                subject=draft["subject"],
                body=draft["body"]
            )

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
        
        # Log that enrichment data is being received but ignored for demo
        logger.info(
            "Received enrichment data but using demo/test data for outreach",
            prospect_name=prospect.name,
            enrichment_received=bool(enrichment),
            using_demo_mode=True
        )

        # Use demo/test data for email generation instead of enrichment
        system_prompt = (
            "You are an expert sales development representative for an elite event planning company. "
            "Your task is to write a personalized, concise, and compelling cold outreach email to a prospect. "
            "Use the provided demo information to create a professional outreach email. "
            "The tone should be professional yet approachable. The goal is to start a conversation, not to close a deal. "
            "End with a clear, low-friction call to action, like asking a simple question."
        )

        # Use internal demo data instead of enrichment data
        user_message = f"""
        Please draft a cold outreach email for our demo/test scenario.

        **Prospect Information:**
        - Name: {prospect.name}
        - Company: {prospect.company_name or 'Demo Company'}
        - Email: {prospect.email}

        **Demo Scenario (Internal Test Data):**
        - Role: Business Executive/Event Coordinator
        - Company Industry: Real Estate / Professional Services
        - Event Type: Corporate networking events and client appreciation events
        - Event Timeline: Quarterly events planned 2-3 months in advance
        - Budget Indicators: Mid-market budget ($10K-50K range)
        - Recommended Angle: Focus on ROI and professional networking value
        - Key Points: Emphasize quality, reliability, and seamless execution

        **Instructions:**
        Create a professional outreach email using this demo scenario. 
        Return ONLY a valid JSON object with two keys: "subject" and "body".
        Do not include any other text, greetings, or explanations outside of the JSON.

        Example Response:
        {{
            "subject": "A Question About Your Upcoming Event",
            "body": "Hi {prospect.name}, ..."
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
            "to create a customized proposal. Keep it concise and focused."
        )

        user_message = f"""
        Please draft a follow-up email requesting event overview details.

        **Prospect Information:**
        - Name: {prospect.name}
        - Company: {prospect.company_name or 'Demo Company'}
        - Email: {prospect.email}

        **Context:**
        - We sent an initial outreach email about event planning services
        - The prospect has responded positively showing interest
        - Now we need to gather event details to create a customized proposal

        **Email Purpose:**
        Ask for an overview of their event needs including:
        - Event type and purpose
        - Approximate date and timeline
        - Expected guest count
        - Budget range (if comfortable sharing)
        - Any specific requirements or vision

        **Instructions:**
        Create a professional follow-up email that:
        1. Thanks them for their positive response
        2. Expresses enthusiasm about working together
        3. Asks for key event details in a non-overwhelming way
        4. Suggests a brief call or detailed email response
        5. Maintains the relationship-building tone

        Return ONLY a valid JSON object with two keys: "subject" and "body".
        Use "Re: " prefix in subject to maintain email thread.

        Example Response:
        {{
            "subject": "Re: Event Planning Partnership - Next Steps",
            "body": "Hi {prospect.name}, Thank you for your positive response..."
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
            "to discuss the proposal in detail. Include a clear call-to-action for scheduling a meeting."
        )

        user_message = f"""
        Please draft a proposal email with PDF attachment.

        **Prospect Information:**
        - Name: {prospect.name}
        - Company: {prospect.company_name or proposal.get('client_company', 'Your Company')}
        - Email: {prospect.email}

        **Proposal Details:**
        - Event Type: {proposal.get('event_type', 'Corporate Event')}
        - Total Investment: ${proposal.get('total_investment', 25000):,}
        - Proposal ID: {proposal.get('proposal_id', 'PROP_001')}

        **Email Purpose:**
        1. Introduce the attached customized proposal
        2. Highlight key benefits and value proposition
        3. Express enthusiasm about working together
        4. Request a meeting to discuss the proposal in detail
        5. Provide clear next steps

        **Instructions:**
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