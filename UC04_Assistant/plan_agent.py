import json
import asyncio
import os
import logging
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

load_dotenv()

from plan_tools import AZURE_OPENAI_TOOL_SCHEMAS, dispatch_tool

# ── Logging Setup ──────────────────────────────────────────────────────────────
LOG_FILE = os.path.join(os.path.dirname(__file__), "planning.log")

def setup_logging():
    logger = logging.getLogger("uc04")
    if logger.handlers: return logger
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(name)s  %(message)s")
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger

log = setup_logging()

# Azure OpenAI Config
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

PLANNING_SYSTEM_PROMPT = """You are the CELA Investigation Planning Agent (UC-04).
MANDATORY PIPELINE:
1. identify_investigation_stages
2. suggest_interview_questions
3. identify_required_documents
4. link_precedent_cases (Queries Azure AI Search)
5. assign_investigation_tasks
6. generate_plan_summary
7. write_plan_to_ucm (Writes to Dataverse)"""

async def run_plan_agent(case_input: dict, verbose: bool = True) -> str:
    client = AsyncAzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
        api_version="2024-02-15-preview"
    )

    messages = [
        {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
        {"role": "user", "content": f"Generate a plan for:\n{json.dumps(case_input)}"}
    ]

    final_text = ""
    for _ in range(15):
        response = await client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            tools=AZURE_OPENAI_TOOL_SCHEMAS,
            tool_choice="auto",
        )
        msg = response.choices[0].message
        if msg.content: final_text = msg.content
        if not msg.tool_calls or response.choices[0].finish_reason == "stop": break

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]
        })

        for tc in msg.tool_calls:
            res = await dispatch_tool(tc.function.name, json.loads(tc.function.arguments))
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": res})

    return final_text
