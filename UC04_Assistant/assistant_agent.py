"""
UC-04 BRI Agent — Assistant Agent
Dual-mode: 
  - Simulated Mock → uses bri_chat_engine.py (local mock data)
  - Live Azure     → uses Azure OpenAI "On Your Data" with Azure AI Search
"""

import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("uc04.agent")

# ═══════════════════════════════════════════════════════════════════════════════
# AZURE CONFIGURATION (from .env)
# ═══════════════════════════════════════════════════════════════════════════════

AZURE_OPENAI_ENDPOINT   = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_KEY        = os.getenv("AZURE_OPENAI_KEY", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
AZURE_OPENAI_API_VERSION = "2024-05-01-preview"

AZURE_SEARCH_ENDPOINT   = os.getenv("AZURE_SEARCH_ENDPOINT", "")
AZURE_SEARCH_KEY        = os.getenv("AZURE_SEARCH_KEY", "")
AZURE_SEARCH_INDEX      = os.getenv("AZURE_SEARCH_INDEX", "cela-knowledgebase")


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPTS — Visible & Configurable
# ═══════════════════════════════════════════════════════════════════════════════

BRI_SYSTEM_PROMPT = """You are the BRI (Business and Regulatory Investigations) AI Agent, 
an enterprise assistant deployed within Microsoft's CELA (Corporate, External, and Legal Affairs) department.

Your role is to assist attorneys and investigators with:
1. Case lookups — retrieving case details from Dataverse (via Azure AI Search)
2. Next steps — recommending investigation actions based on case status
3. Similar cases — finding related cases by issue type, discipline, contacts
4. Attorney profiles — showing assigned attorney details and workload
5. Investigation plans — showing stages, key questions, and required documents
6. Timelines — showing chronological case events
7. Policy guidance — retrieving internal policies (confidentiality, GDPR, expenses, discipline matrix)

IMPORTANT INSTRUCTIONS:
- Always cite your data source (Azure AI Search index, Dataverse, Knowledge Base)
- Use structured formatting with headers, bullet points, and key-value pairs
- For case lookups, include: Case Title, Area/Country, Assigned Attorney, Received Date, Status, Issue Type, Allegation Summary, CRM Link
- For similar cases, group by category and include: Representative Cases, Issue Type, Discipline
- For next steps, provide actionable items with references to the case ID
- Be concise but thorough. Reference relevant policies when applicable.
- If information is not found in the search results, state that clearly.

CONTEXT FROM AZURE AI SEARCH:
{context}
"""

CASE_LOOKUP_PROMPT = """Based on the search results from Azure AI Search, provide a detailed case summary for the requested case.
Include: Case Title, Area/Country, Assigned Attorney, Key Dates (Received Date), 
Case Details (Status, Case Resolution, Type, Issue Type), Allegation Summary, and CRM Link.
Format the response with clear sections and bullet points."""

NEXT_STEPS_PROMPT = """Based on the case data retrieved from Azure AI Search and Dataverse, 
recommend the next investigation steps for this case. Consider:
- Current case status and investigation stage
- Pending actions (evidence collection, interviews, document review)
- Regulatory requirements (GDPR timelines, compliance obligations)
- Escalation needs (attorney consultation, stakeholder notification)
Provide actionable, specific next steps."""

SIMILAR_CASES_PROMPT = """Search the Azure AI Search index for similar cases. Group results by:
1. Issue Type category
2. For each category, list: Representative Case IDs with titles, common Issue Type, typical Discipline outcomes
3. Highlight patterns in discipline and resolution across similar cases."""


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN FUNCTION — Dual-mode response
# ═══════════════════════════════════════════════════════════════════════════════

async def get_assistant_response(user_query: str, chat_history: list, ai_mode: str = "Simulated Mock"):
    """
    Process user query through the BRI agent pipeline.
    
    Simulated Mock mode → bri_chat_engine (local mock data, no API calls)
    Live Azure mode     → Azure OpenAI "On Your Data" + Azure AI Search
    """
    
    if ai_mode == "Simulated Mock":
        # ── MOCK MODE: Use local BRI chat engine ──
        from bri_chat_engine import process_query
        result = process_query(user_query)
        log.info("Mock mode: intent=%s", result.get("intent"))
        return result

    # ══════════════════════════════════════════════════════════════════════
    # LIVE MODE: Azure OpenAI "On Your Data" with Azure AI Search
    # ══════════════════════════════════════════════════════════════════════
    
    # Validate keys
    if not AZURE_OPENAI_KEY or "your-" in AZURE_OPENAI_KEY:
        log.warning("Azure OpenAI keys not configured — falling back to mock mode")
        from bri_chat_engine import process_query
        return process_query(user_query)

    try:
        from openai import AsyncAzureOpenAI
    except ImportError:
        log.error("openai package not installed — falling back to mock mode")
        from bri_chat_engine import process_query
        return process_query(user_query)

    client = AsyncAzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )

    # ── Build messages ──
    messages = [
        {"role": "system", "content": BRI_SYSTEM_PROMPT.format(context="Retrieved via Azure AI Search 'On Your Data'")}
    ]

    # Add chat history
    for m in chat_history[-10:]:  # Last 10 messages for context window
        messages.append({"role": m["role"], "content": m["content"]})

    messages.append({"role": "user", "content": user_query})

    # ── Azure OpenAI "On Your Data" — connects Azure AI Search as data source ──
    # This is the key integration: Azure OpenAI uses Azure AI Search as a grounding
    # data source, enabling RAG (Retrieval Augmented Generation) automatically.
    # Docs: https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/use-your-data

    extra_body = {}
    if AZURE_SEARCH_KEY and "your-" not in AZURE_SEARCH_KEY:
        extra_body = {
            "data_sources": [
                {
                    "type": "azure_search",
                    "parameters": {
                        "endpoint": AZURE_SEARCH_ENDPOINT,
                        "index_name": AZURE_SEARCH_INDEX,
                        "authentication": {
                            "type": "api_key",
                            "key": AZURE_SEARCH_KEY,
                        },
                        "query_type": "vector_semantic_hybrid",
                        "in_scope": True,
                        "top_n_documents": 5,
                        "strictness": 3,
                        "embedding_dependency": {
                            "type": "deployment_name",
                            "deployment_name": "text-embedding-ada-002",
                        },
                    },
                }
            ]
        }

    try:
        response = await client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
            extra_body=extra_body if extra_body else None,
        )

        answer = response.choices[0].message.content

        # Extract citations if present (Azure "On Your Data" includes them)
        citations = []
        if hasattr(response.choices[0].message, "context"):
            ctx = response.choices[0].message.context
            if isinstance(ctx, dict) and "citations" in ctx:
                citations = ctx["citations"]

        # Format response HTML
        citations_html = ""
        if citations:
            citations_html = '<br><br><b style="color: #0078d4;">📚 Sources (Azure AI Search):</b><ul>'
            for c in citations[:5]:
                title = c.get("title", c.get("filepath", "Document"))
                citations_html += f'<li style="font-size: 11px;">{title}</li>'
            citations_html += "</ul>"

        response_html = f"""<div style="font-family: 'Segoe UI', sans-serif; padding: 8px 0; font-size: 13px; color: #323130; line-height: 1.6;">
            {answer}
            {citations_html}
        </div>"""

        return {
            "response": response_html,
            "pipeline_stages": [
                {"stage": "Azure AI Search", "status": "Retrieved documents", "icon": "📚"},
                {"stage": "Azure OpenAI", "status": "Response generated", "icon": "🤖"},
            ],
            "intent": "live_azure",
        }

    except Exception as e:
        log.error("Azure OpenAI call failed: %s — falling back to mock", str(e))
        from bri_chat_engine import process_query
        return process_query(user_query)
