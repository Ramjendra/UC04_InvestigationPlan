"""
UC-04 AI Investigation Plan Generator Agent — Enterprise Implementation
Uses: VerseAPI (Dataverse) and Azure Directory (Azure AI Search)
Mocked for local demonstration.
"""

import json
import asyncio
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from plan_tools import ENTERPRISE_TOOL_SCHEMAS, dispatch_tool

# ── Logging Setup ──────────────────────────────────────────────────────────────

LOG_FILE = os.path.join(os.path.dirname(__file__), "planning.log")

def setup_logging():
    logger = logging.getLogger("uc04")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

log = setup_logging()

PLANNING_SYSTEM_PROMPT = """You are the CELA Investigation Planning Assistant (UC-04).
You utilize VerseAPI (Microsoft Dataverse) and Azure Directory (Azure AI Search).

MANDATORY PIPELINE — call ALL tools in this order:
1. identify_investigation_stages    → VerseAPI: Determine stages
2. suggest_interview_questions     → Azure OpenAI (AD): Generate questions
3. identify_required_documents     → VerseAPI: List required evidence
4. link_precedent_cases            → Azure AI Search: RAG for similar cases
5. assign_investigation_tasks      → VerseAPI: Generate task board
6. generate_plan_summary           → Azure OpenAI (AD): Synthesize plan
7. write_plan_to_ucm               → VerseAPI: Finalize to Dataverse

After all tools complete, output the ENTERPRISE INVESTIGATION PLAN REPORT."""

# ── Mock Azure OpenAI Client ──────────────────────────────────────────────────

class MockAzureOpenAIMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls

class MockAzureOpenAIChoice:
    def __init__(self, message, finish_reason="stop"):
        self.message = message
        self.finish_reason = finish_reason

class MockAzureOpenAIResponse:
    def __init__(self, choices):
        self.choices = choices

class MockAzureOpenAI:
    """Simulates Azure OpenAI tool calling for UC-04 pipeline."""
    def __init__(self):
        self.step_index = 0
        self.tool_sequence = [
            "identify_investigation_stages",
            "suggest_interview_questions",
            "identify_required_documents",
            "link_precedent_cases",
            "assign_investigation_tasks",
            "generate_plan_summary",
            "write_plan_to_ucm"
        ]

    async def create_completion(self, messages, tools, case_input):
        if self.step_index < len(self.tool_sequence):
            tool_name = self.tool_sequence[self.step_index]
            self.step_index += 1
            
            # Generate arguments based on tool name and case input
            args = {}
            if tool_name == "identify_investigation_stages":
                args = {"allegation_type": case_input.get("allegation_type"), "severity": case_input.get("severity")}
            elif tool_name == "suggest_interview_questions":
                args = {"allegation_type": case_input.get("allegation_type"), "parties": case_input.get("parties")}
            elif tool_name == "identify_required_documents":
                args = {"allegation_type": case_input.get("allegation_type")}
            elif tool_name == "link_precedent_cases":
                args = {"allegation_type": case_input.get("allegation_type")}
            elif tool_name == "assign_investigation_tasks":
                args = {"stages": ["Intake", "Evidence", "Interviews", "Final Report"], "severity": case_input.get("severity")}
            elif tool_name == "generate_plan_summary":
                args = {"case_id": case_input.get("case_id"), "stages": ["Mock Stages"], "questions": {"Mock": []}, "docs": ["Mock Docs"]}
            elif tool_name == "write_plan_to_ucm":
                args = {"case_id": case_input.get("case_id"), "plan_data": {"summary": "Mock Plan Summary"}}

            tool_call = type('obj', (object,), {
                "id": f"call_{self.step_index}",
                "function": type('obj', (object,), {"name": tool_name, "arguments": json.dumps(args)})
            })
            return MockAzureOpenAIResponse([MockAzureOpenAIChoice(MockAzureOpenAIMessage(tool_calls=[tool_call]), "tool_calls")])
        else:
            final_report = f"UC-04 INVESTIGATION PLAN REPORT (VerseAPI & Azure Directory)\n"
            final_report += f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            final_report += f"Case ID: {case_input.get('case_id')}\n"
            final_report += "Status: DRAFT CREATED IN DATAVERSE\n\n"
            final_report += "Enterprise-grade investigation plan synthesized via Azure OpenAI and VerseAPI index."
            return MockAzureOpenAIResponse([MockAzureOpenAIChoice(MockAzureOpenAIMessage(content=final_report), "stop")])

async def run_plan_agent(case_input: dict, verbose: bool = True, step_callback=None) -> str:
    """Run Investigation Planning pipeline using Mocked Azure OpenAI client."""
    case_id = case_input.get("case_id", "UCM-NEW")
    log.info("━━━ ENTERPRISE PLANNING START ━━━  case_id=%s", case_id)
    
    client = MockAzureOpenAI()
    messages = [{"role": "system", "content": PLANNING_SYSTEM_PROMPT}]
    final_text = ""

    for _ in range(10):
        response = await client.create_completion(messages, ENTERPRISE_TOOL_SCHEMAS, case_input)
        msg = response.choices[0].message
        
        if msg.content:
            final_text = msg.content
        
        if not msg.tool_calls or response.choices[0].finish_reason == "stop":
            break

        for tc in msg.tool_calls:
            tool_name = tc.function.name
            tool_args = json.loads(tc.function.arguments)
            log.info("STEP %-40s  args=%s", f"[{tool_name}]", json.dumps(tool_args))
            
            result_str = await dispatch_tool(tool_name, tool_args)
            result = json.loads(result_str)
            
            if step_callback:
                step_callback(tool_name, result)
            
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_str})

    log.info("━━━ ENTERPRISE PLANNING END ━━━  case_id=%s", case_id)
    return final_text

if __name__ == "__main__":
    sample_case = {
        "case_id": "UCM-ENTERPRISE-101",
        "allegation_type": "regulatory_compliance",
        "severity": 5,
        "parties": {"complainant": "Internal Auditor", "respondent": "Fin Ops Team"},
        "summary": "Potential violation of Digital Markets Act regarding data interoperability."
    }
    print("\n" + "═" * 60)
    print("UC-04 INVESTIGATION PLANNING — VerseAPI & Azure Directory Mock")
    print("═" * 60 + "\n")
    report = asyncio.run(run_plan_agent(sample_case))
    print(report)
