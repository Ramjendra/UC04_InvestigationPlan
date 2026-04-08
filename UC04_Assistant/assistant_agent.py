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
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01")

AZURE_SEARCH_ENDPOINT   = os.getenv("AZURE_SEARCH_ENDPOINT", "")
AZURE_SEARCH_KEY        = os.getenv("AZURE_SEARCH_KEY", "")
AZURE_SEARCH_INDEX      = os.getenv("AZURE_SEARCH_INDEX", "INSSGSGSG")


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPTS — Visible & Configurable
# ═══════════════════════════════════════════════════════════════════════════════

BRI_SYSTEM_PROMPT = """You are the BRI (Business and Regulatory Investigations) AI Agent.
    
Your primary role is to serve as an expert interface for the BRI Case Management system, powered by Azure OpenAI and Azure AI Search.

ALL data—including case details, allegations, next steps, attorney assignments, and CELA policies—is retrieved exclusively from the Azure AI Search index. You do not have a separate Dataverse API connection.

INSTRUCTIONS:
1. Always perform a search against the attached data source (Azure AI Search) for every query.
2. If the user asks for a Case ID (e.g., BRI-26-08314), find its entry in the index and present a structured summary (Title, Attorney, Status, Summary).
3. For "Next Steps", derive logical investigation actions based on the current case context found in the search results.
4. For "Similar Cases", surface other case records in the index that share the same issue types or jurisdictions.
5. Use professional HTML formatting (badges, bullet points, headers) in your responses to match the Dynamics 365 dashboard aesthetic.
6. If the search returns no information for a specific Case ID, clearly state that the record is not found in the current Search Index.

DATA SOURCE: Azure AI Search (Vectorized Index)
"""

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN FUNCTION — Pure Azure Search Flow
# ═══════════════════════════════════════════════════════════════════════════════

async def get_assistant_response(user_query: str, chat_history: list, ai_mode: str = "Live Azure Foundry"):
    """
    Primary orchestrator for the BRI Agent.
    Prioritizes Azure OpenAI + Azure Search ('On Your Data') flow.
    """
    
    # Check if we should use Mock (only if selected OR keys are missing)
    if ai_mode == "Simulated Mock":
        from bri_chat_engine import process_query
        return process_query(user_query)

    # ══════════════════════════════════════════════════════════════════════
    # LIVE AZURE FLOW (Vector Search + RAG)
    # ══════════════════════════════════════════════════════════════════════
    
    # Check for keys (using default values from .env)
    if not AZURE_OPENAI_KEY or "your-" in AZURE_OPENAI_KEY:
        if ai_mode == "Live Azure Foundry":
            log.warning("Azure OpenAI keys not found — using simulated mode for demo safety")
        from bri_chat_engine import process_query
        return process_query(user_query)

    try:
        from openai import AsyncAzureOpenAI
        client = AsyncAzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
        )

        messages = [
            {"role": "system", "content": BRI_SYSTEM_PROMPT}
        ]
        for m in chat_history[-6:]:
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": user_query})

        # Configuration for Vector/Semantic Search
        data_source_params = {
            "type": "azure_search",
            "parameters": {
                "endpoint": AZURE_SEARCH_ENDPOINT,
                "index_name": AZURE_SEARCH_INDEX,
                "authentication": {
                    "type": "api_key",
                    "key": AZURE_SEARCH_KEY,
                },
                "query_type": "vector_semantic_hybrid", # Modern hybrid search
                "in_scope": True,
                "top_n_documents": 5,
                "strictness": 2,
                "embedding_dependency": {
                    "type": "deployment_name",
                    "deployment_name": "text-embedding-ada-002", # Required for vectorized data
                },
            },
        }

        response = await client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            temperature=0, # Better accuracy for retrieval
            extra_body={"data_sources": [data_source_params]},
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
