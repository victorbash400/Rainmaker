# Outreach Agent Implementation Plan

This document outlines the plan for designing, building, and testing the `OutreachAgent`. The agent's primary role is to automate email outreach to prospects and manage initial conversations, handing off qualified leads to the appropriate next step in the workflow.

## 1. Objective

The goal is to create an AI-powered agent that can:
1.  Consume enriched prospect data.
2.  Use a large language model (Gemini) to draft personalized, context-aware emails.
3.  Send these emails using a real email account.
4.  Receive and interpret replies to engage in basic conversation.
5.  Trigger subsequent agents (e.g., `ProposalAgent`) based on conversation outcomes.

## 2. Core Components

The following new files will be created within the `Rainmaker-backend` directory:

-   **Email Tool:** `app/mcp/email_mcp.py`
-   **The Agent:** `app/agents/outreach.py`
-   **Mock Data:** `app/test_data/mock_enrichment_data.py`
-   **Test Script:** `test_outreach_agent.py` (in the backend root)

## 3. Development Phases

Development will proceed in two distinct phases to ensure a stable, testable build.

### Phase 1: Core Agent & Email Drafting

This phase focuses on getting the agent to send its first email based on mock data.

1.  **`mock_enrichment_data.py`:**
    *   This file will define a list of sample `EnrichmentData` objects. Each object will contain realistic data (personal info, company details, AI insights) to simulate the output of the `EnrichmentAgent`.

2.  **`email_mcp.py`:**
    *   This tool will be built to connect to a standard email provider (e.g., Gmail) using Python's `smtplib` for sending and `imaplib` for receiving.
    *   **Security:** Credentials will be handled exclusively through environment variables. The code will read `EMAIL_ADDRESS`, `EMAIL_PASSWORD`, `SMTP_SERVER`, and `IMAP_SERVER` from the environment. **No credentials will be hardcoded.**
    *   **Functions:** It will expose two primary functions:
        *   `send_email(to: str, subject: str, body: str)`
        *   `check_for_replies(to_prospect_email: str)`

3.  **`outreach.py`:**
    *   The `OutreachAgent` class will be defined here.
    *   Its main method, `execute_outreach(state: RainmakerState)`, will:
        1.  Extract `enrichment_data` from the state.
        2.  Construct a detailed prompt for Gemini to draft a personalized email.
        3.  Call the `gemini_service` to generate the email copy.
        4.  Use the `EmailMCP` to send the generated email to a designated demo address.
        5.  Update the `RainmakerState` to log the outreach attempt.

### Phase 2: Conversation Handling & Integration

This phase focuses on making the agent interactive.

1.  **Reply Detection:**
    *   The main orchestrator loop will be responsible for periodically calling `EmailMCP.check_for_replies()` for active outreach campaigns.

2.  **Conversation Logic (`handle_prospect_reply`):**
    *   When a reply is detected, a new function within the `OutreachAgent` will be triggered.
    *   This function will use Gemini to perform **intent analysis** on the reply's content to classify it (e.g., `INTERESTED`, `NOT_INTERESTED`, `QUESTION`).

3.  **Workflow Handoff:**
    *   If the intent is `INTERESTED`, the agent will update the state to reflect this, and the main workflow will route the process to the `ProposalAgent`.
    *   If the intent is a `QUESTION`, the agent will use Gemini to draft a response and send it, continuing the conversation.

## 4. Testing Strategy

1.  **Independent Testing:**
    *   We will begin by creating and using `test_outreach_agent.py`.
    *   This script will run the `OutreachAgent` completely independently of the main LangGraph workflow. It will load the mock data and call the agent directly.
    *   This allows us to perfect the email drafting and sending logic in a controlled environment.

2.  **Integration Testing:**
    *   Once the agent is verified to work in isolation, we will integrate it as a new node in the `workflow.py` file.
    *   We will then conduct a full, end-to-end test of the flow from Enrichment to Outreach to a conversational reply.
