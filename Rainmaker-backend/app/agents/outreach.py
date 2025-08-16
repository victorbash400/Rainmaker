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

            # 3. Update state with campaign info
            campaign = OutreachCampaign(
                channel="email",
                campaign_type="initial_outreach",
                subject_line=draft["subject"],
                message_body=draft["body"],
                personalization_data=enrichment_data.ai_insights, # Log what drove the personalization
                status=CampaignStatus.SENT if result["status"] == "success" else CampaignStatus.FAILED
            )
            state["outreach_campaigns"] = state.get("outreach_campaigns", []) + [campaign]
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