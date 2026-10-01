# AI Product Support Assistant — Implementation Plan

## Goal

Build a minimal but effective AI-based product support assistant using **Python Flask** as the web backend and **Microsoft Foundry APIs** for the language model.

The first version should:

- Answer product and troubleshooting questions from a trusted knowledge base.
- Maintain simple conversation context.
- Perform one controlled warranty/status lookup.
- Escalate when information is insufficient.

---

# 1. Recommended Architecture

```text
                FRONTEND
          HTML + CSS + JavaScript
                    │
                    ▼
              Python Flask
                    │
        ┌───────────┼────────────┐
        ▼           ▼            ▼
      RAG        SQLite       Session
   Knowledge     Product       History
      Base       /Warranty
        │           │
        └──────┬────┘
               ▼
       Microsoft Foundry
             LLM
               │
               ▼
        Grounded Response
```

### Responsibility of each component

| Component | Responsibility |
|---|---|
| HTML/CSS/JavaScript | User interface and chat |
| Flask | Application/API controller |
| RAG | Finds relevant product-support information |
| Microsoft Foundry | Understands context and generates answers |
| SQLite | Stores authoritative product/warranty information |
| Session history | Maintains recent conversation context |

### Important design principle

**Flask is the application server; Microsoft Foundry is the AI/model platform; the vector store is the retrieval layer; SQLite is the authoritative transactional database.**

Each component should have one clear responsibility.

---

# 2. MVP Scope

## Must Have

- Chat interface
- Product FAQ/manual/troubleshooting knowledge base
- Retrieval-Augmented Generation (RAG)
- Grounded answers with source references
- Short conversation history
- One database-backed warranty/status lookup
- Fallback/human escalation message
- Basic evaluation dataset and metrics

## Excluded from MVP

Do **not** implement these initially:

- Knowledge graph
- Multi-agent orchestration
- Multimodal input
- Autonomous multi-step actions
- Complex production monitoring
- Multiple specialized AI models

These can be considered future enhancements.

---

# 3. Suggested Technology Stack

```text
Frontend
HTML + CSS + JavaScript

Backend
Python + Flask

AI
Microsoft Foundry / Foundry Models API

RAG
Embeddings + ChromaDB or another lightweight vector store

Database
SQLite

Documents
PDF / DOCX / TXT

Configuration
Python-dotenv / environment variables
```

---

# 4. Complete Application Workflow

```text
User asks a question
        ↓
Flask receives request
        ↓
Determine request type
        ↓
 ┌───────────────┬────────────────┐
 │               │                │
 ▼               ▼                ▼
Knowledge      Warranty        Unsupported
Question       Request           Query
 │               │                │
 ▼               ▼                ▼
RAG search    SQLite query      Fallback
 │               │
 └───────┬───────┘
         ▼
Microsoft Foundry
         ↓
Generate grounded answer
         ↓
Return answer + sources
         ↓
Frontend displays response
```

---

# 5. Request Routing

For the minimal application, **do not create a separate AI intent-classification model**.

Use simple application-level routing.

### Example

```text
"What is the battery capacity?"
        ↓
Knowledge search → RAG

"How do I fix charging?"
        ↓
Knowledge search → RAG

"Is my product still under warranty?"
        ↓
Warranty lookup → SQLite

"Who won yesterday's football match?"
        ↓
Unsupported → fallback
```

This reduces complexity and makes the system easier to develop, debug, and explain during a project presentation.

---

# 6. Phase 1 — Requirements and Flask Project Skeleton

## Objective

Create the basic backend and define exactly what the application supports.

### Define the product domain

Choose a limited product category.

For example:

```text
Domain: Consumer Electronics

Products:
- Laptop A
- Laptop B
- Laptop C
```

Do not begin with thousands of products.

### Define supported questions

Initially support:

1. Product specifications
2. Product features
3. Troubleshooting
4. Product comparison
5. Warranty status
6. Follow-up questions

### Flask project structure

```text
project/
│
├── app/
│   ├── __init__.py
│   ├── routes.py
│   │
│   ├── services/
│   │   ├── foundry.py
│   │   ├── rag.py
│   │   └── warranty.py
│   │
│   ├── data/
│   │   ├── products.db
│   │   └── knowledge/
│   │
│   ├── templates/
│   │   └── index.html
│   │
│   └── static/
│       ├── style.css
│       └── script.js
│
├── run.py
├── .env
├── requirements.txt
└── README.md
```

---

# 7. Phase 2 — Product Knowledge Base

## Objective

Give the AI reliable information from which it can answer questions.

Use a small collection of trusted documents:

```text
knowledge/
│
├── product_manual.pdf
├── troubleshooting.pdf
├── faq.pdf
└── warranty_policy.pdf
```

## Processing workflow

```text
PDF / DOCX / TXT
       ↓
Extract text
       ↓
Clean text
       ↓
Split into chunks
       ↓
Create embeddings
       ↓
Store vectors
       ↓
Store source metadata
```

### Why chunk documents?

Instead of sending an entire 100-page manual to the model, split it into smaller pieces.

For example:

```text
Chunk 1
Battery specifications

Chunk 2
Charging instructions

Chunk 3
Power troubleshooting

Chunk 4
Warranty conditions
```

When the user asks:

> "My laptop is not charging."

The system retrieves the relevant charging/troubleshooting chunks rather than the entire manual.

---

# 8. Phase 3 — Microsoft Foundry Integration

## Objective

Connect Flask to a Microsoft Foundry model and verify that a simple prompt works before adding RAG.

Microsoft's current Foundry Python SDK uses:

```text
azure-ai-projects >= 2.0.0
```

A Foundry project endpoint follows the general pattern:

```text
https://<resource-name>.services.ai.azure.com/api/projects/<project-name>
```

Microsoft documents using the Foundry project client and obtaining an OpenAI-compatible client for model/Responses API calls.

## Example Python connection

```python
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

project = AIProjectClient(
    endpoint=FOUNDRY_PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)

openai = project.get_openai_client()

response = openai.responses.create(
    model=FOUNDRY_MODEL_NAME,
    input="Hello",
)

print(response.output_text)
```

The exact model name and authentication configuration depend on the model deployment in your Foundry project.

## Environment variables

Keep credentials and configuration outside your source code.

Example:

```text
FOUNDRY_PROJECT_ENDPOINT=...
FOUNDRY_MODEL_NAME=...
```

Do not place API keys, passwords, or tokens directly inside Python files.

---

# 9. Phase 4 — Build the RAG Chat

## Core workflow

```text
User question
      ↓
Normalize question
      ↓
Search vector database
      ↓
Retrieve top relevant chunks
      ↓
Build grounded prompt
      ↓
Send prompt to Foundry
      ↓
Generate answer
      ↓
Return answer + sources
```

## Example

User asks:

> "How can I fix the charging problem?"

The retrieval system might return:

```text
Source: Laptop_Manual.pdf
Page: 42

"Ensure the AC adapter is securely connected.
If the charging indicator remains off, disconnect
the adapter for 30 seconds and reconnect it."
```

Flask then sends the retrieved information to Foundry.

### Grounding instruction

The model should receive a strong instruction such as:

```text
You are a product support assistant.

Answer the user's question using only the supplied
product-support context.

Do not invent product specifications, troubleshooting
steps, warranty conditions, or policies.

If the supplied context does not contain enough
information to answer reliably, say that you do not
have enough information and recommend contacting
support.

Keep answers clear and practical.
```

This is one of the most important parts of the project.

---

# 10. Phase 5 — Conversation Context

The assistant should understand follow-up questions.

Example:

```text
User:
What is the battery capacity of Laptop A?

Assistant:
Laptop A has a 70 Wh battery.

User:
How long does it take to charge?

Assistant:
Based on the available product information...
```

The second question depends on the previous conversation.

## Minimal implementation

Keep only the last few messages.

```text
Session
│
├── User question 1
├── Assistant answer 1
├── User question 2
└── Assistant answer 2
```

Do not build a complicated long-term memory system for the MVP.

---

# 11. Phase 6 — Warranty/Status Tool

This is the one controlled AI-agent-style function.

## SQLite database

Example:

```text
products
---------
product_id
product_name
serial_number
purchase_date
warranty_period
```

The AI should **not** generate warranty information itself.

Instead:

```text
User:
Is SN12345 still under warranty?

        ↓

Flask detects warranty request

        ↓

check_warranty("SN12345")

        ↓

SQLite

        ↓

Verified result

        ↓

Foundry explains result

        ↓

User
```

## Example Python function

```python
def check_warranty(serial_number):
    # Query SQLite
    # Calculate warranty status
    # Return verified result
    pass
```

This creates a clean separation:

```text
LLM
= understands and communicates

SQLite
= authoritative warranty data
```

---

# 12. Phase 7 — Fallback and Human Escalation

The assistant should not attempt to answer everything.

### Example

User:

> "Can I repair the motherboard myself?"

If the knowledge base doesn't contain an approved procedure:

```text
I don't have enough verified information in the
product support knowledge base to provide a reliable
answer to this question.

Please contact a support representative for further
assistance.
```

This is preferable to allowing the model to invent instructions.

## Fallback conditions

Trigger fallback when:

- Retrieval returns no relevant documents.
- Retrieved information is insufficient.
- The question is outside the product domain.
- The requested action is unsupported.
- The system cannot verify the requested information.

---

# 13. Phase 8 — Evaluation

Do not simply demonstrate that the chatbot works.

Create a small evaluation dataset.

## Recommended size

```text
30–50 questions
```

Divide them into:

### Product questions

```text
What is the battery capacity?
What processor does Product A use?
Does Product B support Wi-Fi 6?
```

### Troubleshooting

```text
My device is not charging.
The screen is not turning on.
The device is overheating.
```

### Follow-up questions

```text
What is its battery capacity?
How long does it last?
Does it support fast charging?
```

### Warranty

```text
Is SN1001 under warranty?
When does the warranty expire?
```

### Ambiguous questions

```text
What about the newer model?
How much does it cost?
```

### Unsupported questions

```text
Who won yesterday's cricket match?
Tell me about another company's product.
```

---

# 14. Evaluation Metrics

Measure:

## 1. Retrieval relevance

Did the system retrieve the correct document/chunk?

```text
Relevant retrieved chunks
-------------------------
Total retrieved chunks
```

## 2. Grounded answer rate

Did the answer remain supported by retrieved information?

```text
Grounded responses
------------------
Total evaluated responses
```

## 3. Unsupported-answer rate

How often did the system make unsupported claims?

This should be as low as possible.

## 4. Warranty accuracy

Compare the AI's displayed warranty result with the SQLite ground truth.

## 5. Task success

For example:

```text
Correctly answered:
42 / 50

Task success = 84%
```

## 6. Latency

Measure:

```text
User request
     ↓
Retrieval
     ↓
Foundry
     ↓
Response
```

Record the approximate response time.

---

# 15. Minimal API

Only create these endpoints initially:

```text
POST /api/chat
```

Main conversational endpoint.

```text
POST /api/warranty/check
```

Warranty/status lookup.

```text
GET /api/health
```

Checks whether Flask is running.

Avoid creating unnecessary endpoints.

---

# 16. Example `/api/chat` Workflow

```text
POST /api/chat

{
    "message": "My laptop is not charging",
    "session_id": "abc123"
}
```

Flask:

```text
Receive request
      ↓
Validate input
      ↓
Check conversation context
      ↓
Search RAG database
      ↓
Retrieve relevant passages
      ↓
Construct grounded prompt
      ↓
Call Microsoft Foundry
      ↓
Validate response
      ↓
Return JSON
```

Example response:

```json
{
    "answer": "Please first check that the charger is...",
    "sources": [
        {
            "document": "troubleshooting.pdf",
            "page": 12
        }
    ]
}
```

---

# 17. Frontend Workflow

The frontend can remain very simple.

```text
┌───────────────────────────────────┐
│     AI Product Support Assistant  │
├───────────────────────────────────┤
│                                   │
│ User: My laptop isn't charging    │
│                                   │
│ AI: Please check the charger...   │
│                                   │
│                                   │
├───────────────────────────────────┤
│ Ask about your product...     [➤]│
└───────────────────────────────────┘
```

The JavaScript sends:

```javascript
fetch("/api/chat", {
    method: "POST",
    headers: {
        "Content-Type": "application/json"
    },
    body: JSON.stringify({
        message: userMessage,
        session_id: sessionId
    })
});
```

Flask returns the answer.

---

# 18. Recommended Development Order

Do not build everything simultaneously.

## Step 1

Make Flask work.

```text
GET /api/health
```

Expected:

```json
{
    "status": "ok"
}
```

## Step 2

Connect Flask to Microsoft Foundry.

Test:

```text
User → Flask → Foundry → Flask → User
```

Do not add RAG yet.

## Step 3

Build document ingestion.

```text
PDF
 ↓
Text
 ↓
Chunks
 ↓
Embeddings
 ↓
Vector database
```

## Step 4

Test retrieval independently.

Ask:

```text
"My device isn't charging"
```

Check whether the correct troubleshooting chunk is returned.

## Step 5

Combine RAG + Foundry.

```text
Question
 ↓
Retrieval
 ↓
Context
 ↓
Foundry
 ↓
Answer
```

## Step 6

Add conversation history.

## Step 7

Add SQLite warranty lookup.

## Step 8

Add fallback.

## Step 9

Build evaluation dataset.

## Step 10

Improve UI and prepare documentation.

---

# 19. What NOT to Build Initially

Avoid:

```text
❌ Knowledge graph
❌ Multiple agents
❌ Autonomous agent loops
❌ Voice assistant
❌ Image understanding
❌ Complex authentication
❌ Large-scale cloud database
❌ Real-time monitoring
❌ Multiple external APIs
❌ Fine-tuning an LLM
```

These features can make the project impressive on paper but significantly harder to implement, debug, evaluate, and explain.

---

# 20. Final MVP

The completed first version should effectively be:

```text
                 USER
                   │
                   ▼
          ┌─────────────────┐
          │   Flask Chat    │
          └────────┬────────┘
                   │
             ┌─────┴─────┐
             │           │
             ▼           ▼
          RAG Search   Warranty
             │          SQLite
             │           │
             └─────┬─────┘
                   ▼
          Microsoft Foundry
                   │
                   ▼
          Grounded Response
                   │
                   ▼
             USER ANSWER
```

This is small enough to finish while still demonstrating:

- Python
- Flask
- REST API
- LLM integration
- Microsoft Foundry
- RAG
- Embeddings
- Vector database
- SQLite
- Conversational context
- Tool/function calling
- Grounded generation
- Evaluation

---

# 21. Recommended Project Statement

> **An AI-Based Product Support Assistant Using Retrieval-Augmented Generation and Conversational Context**

### Short description

The system provides conversational product support by retrieving relevant information from product manuals, FAQs, troubleshooting documents, and support policies before generating responses using a large language model hosted through Microsoft Foundry. Structured product and warranty information is maintained separately in a database, allowing the assistant to provide verified information while reducing unsupported responses.

---

# 22. Research Direction

The project can be evaluated around these questions:

### Research Question 1

Does retrieval-augmented generation improve the reliability of product-support responses compared with direct LLM responses?

### Research Question 2

Can a lightweight RAG architecture provide useful product support without requiring a complex multi-agent system?

### Research Question 3

How accurately can the assistant handle multi-turn product-support conversations?

### Research Question 4

Can deterministic database tools reduce errors when answering warranty/status questions?

---

# 23. Current Foundry Implementation Guidance

Use the current Microsoft Foundry project SDK for a new Foundry project.

Microsoft documents the current Python package as:

```text
azure-ai-projects>=2.0.0
```

The project endpoint generally follows:

```text
https://<resource-name>.services.ai.azure.com/api/projects/<project-name>
```

The Foundry project client can provide an OpenAI-compatible client for model/Responses API calls.

For the MVP, **do not start with a hosted multi-agent architecture**.

Keep:

```text
Flask
  ↓
RAG
  ↓
Foundry model
```

and add the warranty database around it.

This gives you a simpler architecture that is easier to demonstrate, test, and debug.

---

# 24. Current Foundry Connection Pattern

Example:

```python
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

project = AIProjectClient(
    endpoint=FOUNDRY_PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)

openai = project.get_openai_client()

response = openai.responses.create(
    model=FOUNDRY_MODEL_NAME,
    input="Hello",
)

print(response.output_text)
```

The exact model name and authentication configuration depend on the model deployment in your Microsoft Foundry project.

Microsoft also documents API-key authentication for supported OpenAI-compatible endpoints. For a new project, choose one authentication approach appropriate to your Azure setup and keep credentials in environment variables.

---

# 25. Environment Variables

Example:

```text
FOUNDRY_PROJECT_ENDPOINT=...
FOUNDRY_MODEL_NAME=...
```

Never put:

```text
API keys
passwords
tokens
secrets
```

directly into Python source code.

Use `.env` locally and Azure's appropriate secret/configuration mechanism when deploying.

---

# 26. Notion Implementation Plan

The Notion project should be used as the central project-management document.

Suggested structure:

```text
AI Product Support Assistant
│
├── 01. Project Overview
├── 02. Research
├── 03. Requirements
├── 04. Architecture
├── 05. Database Design
├── 06. RAG Design
├── 07. Foundry Integration
├── 08. Flask API
├── 09. Frontend
├── 10. Testing
├── 11. Evaluation
├── 12. Progress
└── 13. Final Documentation
```

Each development phase can then become a task with:

```text
Task
 ├── Objective
 ├── Implementation
 ├── Dependencies
 ├── Acceptance criteria
 └── Status
```

---

# 27. Final Development Roadmap

```text
PHASE 1
Requirements + Flask
        ↓
PHASE 2
Product knowledge base
        ↓
PHASE 3
Microsoft Foundry connection
        ↓
PHASE 4
RAG chatbot
        ↓
PHASE 5
Conversation context
        ↓
PHASE 6
Warranty/status tool
        ↓
PHASE 7
Fallback + validation
        ↓
PHASE 8
Evaluation
        ↓
FINAL MVP
```

## MVP Completion Criteria

The project is considered complete when:

1. Flask successfully communicates with Microsoft Foundry.
2. The assistant can answer questions using approved product documents.
3. Responses contain or reference their supporting source.
4. The assistant refuses to invent unsupported information.
5. Follow-up questions work within a conversation session.
6. Warranty information is obtained from SQLite rather than generated by the LLM.
7. Unsupported queries trigger an appropriate fallback.
8. A 30–50 question evaluation set has been tested.
9. Results and limitations are documented.
10. The complete architecture can be explained clearly during the project presentation.
