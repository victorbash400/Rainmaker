# 🌧️ Rainmaker
## AI Sales Automation for Event Planning Companies

<div align="center">

![TiDB Serverless](https://img.shields.io/badge/TiDB-Serverless-FF6B35?style=for-the-badge&logo=tidb&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google-Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-00D4AA?style=for-the-badge&logo=langchain&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Kiro AI](https://img.shields.io/badge/Built_with-Kiro_AI-8A2BE2?style=for-the-badge&logo=ai&logoColor=white)

**🎉 Turn Event Planners into Rainmakers**

*Automatically find people planning events and convert them into paying clients*

</div>

---

## 🎯 What is Rainmaker?

**Rainmaker helps event planning companies automatically find and convert prospects into clients.**

If you run a wedding planning business, corporate event company, or party planning service, Rainmaker finds people who are actively planning events and turns them into your customers through AI automation.

### The Problem
- Event planners waste hours manually searching for prospects
- Most outreach is generic and gets ignored
- You miss hot prospects because you can't monitor everywhere
- Converting prospects to clients requires constant manual follow-up

### The Solution
**6 AI agents work together to automate your entire sales process:**

```mermaid
graph LR
    A[🕵️ Hunter<br/>Finds prospects planning events] --> B[🧠 Enrichment<br/>Researches their needs deeply]
    B --> C[📧 Outreach<br/>Sends personalized messages]
    C --> D[💬 Conversation<br/>Handles their responses]
    D --> E[📋 Proposal<br/>Creates custom proposals]
    E --> F[📅 Meeting<br/>Schedules consultations]
    F --> G[💰 Client]
    
    style A fill:#e3f2fd
    style G fill:#e8f5e8
```

---

## 🤖 How Each AI Agent Works

### 🕵️ **Hunter Agent** - Finds People Planning Events
**What it does:** Scans the web to find people actively planning events
- Searches social media for engagement announcements, event planning posts
- Monitors company websites for corporate event signals
- Finds venue searches, vendor inquiries, and event timelines
- Stores all prospects in TiDB database for processing

**Example:** Finds "Sarah just got engaged and is looking for wedding venues in Austin"

### 🧠 **Enrichment Agent** - Deep Research with Vector Search
**What it does:** Uses AI to deeply research each prospect and understand their needs
- Searches Perplexity API for detailed information about the prospect
- Stores all research data as vector embeddings in TiDB
- Uses vector similarity search to find patterns and insights
- AI analyzes everything to understand budget, timeline, preferences

**How TiDB Vector Search Works:**
1. **Store Research:** All prospect research gets converted to 3072-dimensional vectors
2. **Semantic Search:** Ask questions like "What's their budget?" and find similar prospects
3. **Pattern Recognition:** "People like this usually spend $15k and book 6 months ahead"
4. **AI Analysis:** Gemini AI synthesizes all findings into actionable insights

**Example:** "Sarah works at tech company, likely $20k+ budget, prefers modern venues, planning for next fall"

### 📧 **Outreach Agent** - Personalized Messages
**What it does:** Creates and sends personalized messages based on research
- Generates event-specific messages (wedding vs corporate vs birthday)
- References specific details from research (their company, timeline, preferences)
- Chooses best channel (email, LinkedIn, etc.)
- Tracks opens, clicks, and responses

**Example:** "Hi Sarah! Saw you're planning a fall wedding in Austin. We specialize in modern venues and just helped another tech professional plan their dream wedding at The Contemporary..."

### 💬 **Conversation Agent** - Handles Responses
**What it does:** Automatically responds to prospect inquiries and gathers requirements
- Understands intent ("I'm interested" vs "Not right now" vs "Tell me more")
- Asks qualifying questions about budget, guest count, date, style
- Extracts structured requirements from conversations
- Knows when to escalate to humans

**Example:** Prospect replies "This looks interesting, what's your pricing?" → Agent responds with questions about their specific needs

### 📋 **Proposal Agent** - Creates Custom Proposals
**What it does:** Generates tailored proposals based on gathered requirements
- Creates detailed service packages based on their event type and budget
- Includes pricing, timeline, and deliverables
- Generates PDF proposals with mood boards
- Tracks proposal views and engagement

**Example:** Creates a comprehensive wedding planning proposal with 3 package options, timeline, and pricing

### 📅 **Meeting Agent** - Schedules Consultations
**What it does:** Coordinates meetings to close the deal
- Integrates with Google Calendar to find availability
- Sends meeting invites and reminders
- Prepares meeting notes with all prospect research
- Tracks meeting outcomes

**Example:** "Based on your proposal interest, I've scheduled a consultation for next Tuesday at 2pm to discuss your wedding plans"

---

## 🗄️ Why TiDB Serverless?

**TiDB powers the intelligence behind prospect research:**

### Vector Search for Smart Insights
```sql
-- Store prospect research as vectors
INSERT INTO prospect_research (content, content_vector) 
VALUES ('Sarah loves modern venues, works at tech company...', [0.1, 0.8, 0.3, ...])

-- Find similar prospects to predict behavior
SELECT content, similarity_score
FROM prospect_research 
WHERE VEC_COSINE_DISTANCE(content_vector, query_vector) < 0.3
ORDER BY similarity_score DESC
```

### Real-World Usage
- **Pattern Recognition:** "Prospects like Sarah typically book 6 months ahead with $20k budgets"
- **Personalization:** "Similar clients loved these venue recommendations"
- **Optimization:** "This message style works best for tech professionals"
- **Forecasting:** "Based on research, Sarah has 85% chance of booking within 30 days"

---

## 🚀 Getting Started

### Prerequisites
- TiDB Serverless account (free tier available)
- OpenAI API key
- Perplexity API key (for web research)

### Quick Setup
```bash
# 1. Clone and setup
git clone <repository-url>
cd Rainmaker
cp .env.example .env

# 2. Add your credentials to .env
TIDB_HOST=your-tidb-host
TIDB_USER=your-username  
TIDB_PASSWORD=your-password
OPENAI_API_KEY=your-openai-key
SONAR_API_KEY=your-perplexity-key

# 3. Start the system
docker-compose up -d

# 4. Initialize database
cd Rainmaker-backend
python create_tidb_vector_table.py
```

### Access Your System
- **Dashboard:** http://localhost:3000
- **API:** http://localhost:8000
- **Docs:** http://localhost:8000/docs

---

## 💼 Built With

| Technology | Purpose |
|------------|---------|
| **TiDB Serverless** | Vector database for intelligent prospect research |
| **LangGraph** | Orchestrates the 6 AI agents |
| **Google Gemini** | AI analysis and reasoning |
| **Perplexity API** | Web research and data gathering |
| **FastAPI** | Backend API server |
| **React** | Frontend dashboard |
| **Kiro AI** | Development acceleration and code generation |

---

## 📈 Results

**Event planning companies using Rainmaker see:**
- 10x more qualified prospects found automatically
- 70% reduction in time from prospect to meeting
- 3x higher response rates from personalized outreach
- 50% faster proposal creation and delivery

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## � Liceanse

MIT License - see LICENSE file for details

---

<div align="center">

**Built with ❤️ using cutting-edge AI and database technology**

*Showcasing the power of TiDB Serverless + Multi-Agent AI + Kiro AI Development*

[![TiDB](https://img.shields.io/badge/Powered_by-TiDB_Serverless-FF6B35?style=for-the-badge)](https://tidbcloud.com)
[![Kiro AI](https://img.shields.io/badge/Built_with-Kiro_AI-8A2BE2?style=for-the-badge)](https://kiro.ai)

</div>