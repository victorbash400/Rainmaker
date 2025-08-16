import asyncio
import os
from dotenv import load_dotenv

from app.core.state import RainmakerState, StateManager
from app.agents.outreach import OutreachAgent
from app.test_data.mock_enrichment_data import mock_data

# Load environment variables from .env file
# Make sure you have a .env file in the Rainmaker-backend directory with your
# EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_SERVER, and IMAP_SERVER
load_dotenv()

async def main():
    """Main function to run the independent test."""
    print("--- Starting Independent Outreach Agent Test ---")

    # 1. Select mock data to use
    # We'll use the first mock prospect: Jane Doe, the Marketing Director
    prospect, enrichment = mock_data[0]
    print(f"Selected Prospect: {prospect.name} at {prospect.company_name}")

    # Ensure the test email address is set in your environment
    test_recipient_email = os.getenv("TEST_RECIPIENT_EMAIL")
    if not test_recipient_email:
        print("\nERROR: Please set TEST_RECIPIENT_EMAIL in your .env file.")
        print("This should be the email address where you want to receive the test email.")
        return
    
    # Override the prospect's email to send to our test address
    prospect.email = test_recipient_email
    print(f"Redirecting email to test recipient: {prospect.email}")

    # 2. Create an initial state object
    initial_state = StateManager.create_initial_state(prospect_data=prospect)
    initial_state["enrichment_data"] = enrichment
    print("Initial state created.")

    # 3. Initialize and run the OutreachAgent
    outreach_agent = OutreachAgent()
    print("\n--- Step 1: Sending Initial Email ---")
    final_state = await outreach_agent.execute_outreach(initial_state)
    print("Outreach Agent execution finished.")

    # 4. Print the results
    print("\n--- Test Results ---")
    campaigns = final_state.get("outreach_campaigns", [])
    
    if campaigns:
        sent_campaign = campaigns[0]
        print(f"Campaign Status: {sent_campaign.status.value}")
        print(f"Subject: {sent_campaign.subject_line}")
        print("\n--- Email Body ---")
        print(sent_campaign.message_body)
        print("--------------------")
    else:
        print("No campaign was added to the state.")

    # 5. Monitor for replies (optional step)
    print("\n--- Step 2: Monitoring for Replies ---")
    print("The email has been sent! Please reply to it from your Outlook account.")
    print("Press ENTER when you're ready to check for replies...")
    input()  # Wait for user input
    print("Checking for replies...")
    
    from app.mcp.email_mcp import email_mcp
    replies = email_mcp.check_for_replies(prospect.email)
    
    if replies:
        print(f"\n--- Found {len(replies)} replies! ---")
        for i, reply in enumerate(replies, 1):
            print(f"\nReply {i}:")
            print(f"From: {reply['from']}")
            print(f"Subject: {reply['subject']}")
            print(f"Body: {reply['body'][:200]}...")  # Show first 200 chars
            
            # Process the reply with the outreach agent
            final_state = await outreach_agent.handle_prospect_reply(final_state, reply)
            
        # Show updated conversation state
        conv_summary = final_state.get("conversation_summary", {})
        if conv_summary:
            print(f"\n--- Conversation Analysis ---")
            print(f"Intent: {conv_summary.get('last_reply_intent')}")
            print(f"Summary: {conv_summary.get('last_reply_summary')}")
    else:
        print("No replies found. You can manually reply to the email and run this test again.")

    print("\nTest finished. Check your inbox for the email!")

if __name__ == "__main__":
    asyncio.run(main())
