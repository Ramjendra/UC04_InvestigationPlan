"""
UC-04 Investigation Plan — Interactive Assistant (Ollama)
Answers questions about investigation plans, stages, interview questions, and required evidence.
Triggers the planning agent when a new plan is requested.
"""

import json
import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

from simulated_data import (
    ATTORNEYS, EXISTING_CASES, KNOWLEDGE_BASE, ALLEGATION_TAXONOMY,
    SLA_RULES, get_all_cases_summary, get_attorney_workload_summary
)
from plan_agent import run_plan_agent

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3.1")


def get_client() -> AsyncOpenAI:
    return AsyncOpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")


# ── Build live context from simulated data ─────────────────────────────────────

def build_context() -> str:
    cases_text = "\n".join([
        f"  [{c.sla_flag}] {c.case_id} | {c.allegation_type} | Severity {c.severity}/5 | "
        f"Queue#{c.queue_position} | Attorney: {ATTORNEYS.get(c.assigned_attorney, type('x',(),{'name':'Unassigned'})()).name} | {c.status}"
        for c in sorted(EXISTING_CASES, key=lambda x: x.queue_position)
    ])
    attorneys_text = "\n".join([
        f"  {a.name} ({a.seniority}) — {a.active_cases}/{a.max_cases} cases [{a.availability}] — {', '.join(a.specializations[:2])}"
        for a in ATTORNEYS.values()
    ])
    sla_text = "\n".join([
        f"  Severity {k}: {v['flag']} — respond in {v['response_hours']}h, resolve in {v['resolution_days']} days"
        for k, v in SLA_RULES.items()
    ])
    return f"""=== UCM LIVE DATA ===

CASE QUEUE:
{cases_text}

ATTORNEY ROSTER (Dataverse):
{attorneys_text}

SLA RULES:
{sla_text}

ALLEGATION TYPES: {', '.join(ALLEGATION_TAXONOMY.keys())}
KB CATEGORIES: {', '.join(kb.allegation_category for kb in KNOWLEDGE_BASE)}"""


SYSTEM_PROMPT = """You are the UC-04 Investigation Planning Assistant for the CELA legal team.

You have live access to the UCM case queue, attorney workloads, SLA rules, and the CELA knowledgebase.

You help with:
1. Investigation plans, stages, and durations
2. Interview questions and document collection lists
3. Linking precedent cases (RAG)
4. Generating investigation tasks for UCM
5. Submitting a case for planning

When a user wants to GENERATE A PLAN, collect case_id and details, then output EXACTLY this on one line:
PLAN_REQUEST: {"case_id":"...","allegation_type":"...","severity":3,"parties":{"complainant":"...","respondent":"..."},"summary":"..."}

Be concise, professional, and always reference actual case IDs and attorney names from the live data.

{context}"""


# ── Streaming response ─────────────────────────────────────────────────────────

async def stream_response(client: AsyncOpenAI, messages: list, context: str) -> str:
    system = SYSTEM_PROMPT.format(context=context)
    full_text = ""

    stream = await client.chat.completions.create(
        model=OLLAMA_MODEL,
        messages=[{"role": "system", "content": system}] + messages,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        print(delta, end="", flush=True)
        full_text += delta

    return full_text


# ── Parse triage trigger ───────────────────────────────────────────────────────

def extract_triage_request(text: str):
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("PLAN_REQUEST:"):
            raw = line[len("PLAN_REQUEST:"):].strip()
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
    return None


# ── Main Chatbot Loop ──────────────────────────────────────────────────────────

async def run_chatbot():
    client = get_client()
    messages = []
    context = build_context()

    print("\n" + "═" * 65)
    print("  UC-04 INVESTIGATION PLANNING — Interactive Assistant")
    print(f"  Powered by Ollama ({OLLAMA_MODEL})")
    print("═" * 65)
    print("\nAsk me about:")
    print("  • Investigation plans, stages, and strategy")
    print("  • Interview questions and evidence lists")
    print("  • Precedent cases and historical patterns")
    print("  • How the planning pipeline works")
    print("  • Generate a plan for an existing case")
    print("\nShortcuts: 'queue' | 'attorneys' | 'exit'\n")

    while True:
        try:
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("You: ")
            )
            user_input = user_input.strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nSession ended.")
            break

        if not user_input:
            continue
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        if user_input.lower() == "queue":
            print("\n" + get_all_cases_summary() + "\n")
            continue
        if user_input.lower() == "attorneys":
            print("\n" + get_attorney_workload_summary() + "\n")
            continue

        messages.append({"role": "user", "content": user_input})

        print("\nAssistant: ", end="", flush=True)
        response_text = await stream_response(client, messages, context)
        print("\n")

        # Trigger planning agent if needed
        plan_data = extract_triage_request(response_text)
        if plan_data:
            print("\n" + "─" * 65)
            print("TRIGGERING INVESTIGATION PLANNING AGENT (UC-04) via Ollama...")
            print("─" * 65 + "\n")
            plan_report = await run_plan_agent(plan_data, verbose=True)
            print("\n" + "─" * 65 + "\n")

            context = build_context()  # refresh with new data

            messages.append({"role": "assistant", "content": response_text})
            messages.append({
                "role": "user",
                "content": f"Planning complete. Result:\n{plan_report}\n\nSummarize the generated plan."
            })

            print("Assistant: ", end="", flush=True)
            followup = await stream_response(client, messages, context)
            print("\n")
            messages.append({"role": "assistant", "content": followup})
        else:
            messages.append({"role": "assistant", "content": response_text})

        if len(messages) > 40:
            messages = messages[-30:]


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(run_chatbot())
