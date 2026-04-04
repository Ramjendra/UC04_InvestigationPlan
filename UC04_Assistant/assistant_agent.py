import os
import json
from openai import AsyncAzureOpenAI
from azure_search_client import AzureSearchClient
from dataverse_client import DataverseClient
from plan_agent import run_plan_agent

search_client = AzureSearchClient()
dv_client = DataverseClient()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

SYSTEM_PROMPT = """You are the CELA UCM AI Assistant. 
You help legal teams with investigation planning (UC-04).
You have access to:
1. Azure AI Search for knowledge base retrieval.
2. Dataverse for case and attorney data.

If the user wants to generate an investigation plan, collect the case ID and trigger the 'run_plan_agent' functionality.
Otherwise, use the retrieved context to answer questions about cases, SLAs, and investigation procedures.

CONTEXT:
{context}"""

async def get_assistant_response(user_query: str, chat_history: list, ai_mode: str = "Simulated Mock"):
    from foundry_client import FoundryClient
    is_mock = (ai_mode == "Simulated Mock")
    foundry = FoundryClient(force_mock=is_mock)
    
    if is_mock:
        client = foundry.get_chat_completions_client()
        response = client.complete(messages=[{"role": "user", "content": user_query}])
        return response.choices[0].message.content

    client = AsyncAzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
        api_version="2024-02-15-preview"
    )

    # 1. RAG: Search Knowledge Base
    search_hits = search_client.search_knowledge_base(user_query)
    kb_context = "\n".join([f"KB [{h['title']}]: {h['content'][:200]}" for h in search_hits])

    # 2. Trigger Planning Agent if requested
    if "generate plan" in user_query.lower() or "start planning" in user_query.lower():
        # For demo, we'll assume the user is asking about the first case if no ID provided
        # In real life, we'd extract the case_id
        return await run_plan_agent({"case_id": "UCM-2024-105", "allegation_type": "harassment", "severity": 4, "parties": {"complainant": "Alex"}, "summary": "Sample Case"})

    # 3. General Chat
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=kb_context)},
    ] + chat_history + [{"role": "user", "content": user_query}]

    response = await client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=messages,
        temperature=0.7
    )

    return response.choices[0].message.content
