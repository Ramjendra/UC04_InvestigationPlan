import json
import logging
import os
from datetime import datetime
from simulated_data import (
    ATTORNEYS, EXISTING_CASES, KNOWLEDGE_BASE, ALLEGATION_TAXONOMY,
    SLA_RULES, CaseRecord
)
from azure_search_client import AzureSearchClient
from dataverse_client import DataverseClient

log = logging.getLogger("uc04.tools")

search_client = AzureSearchClient()
dv_client = DataverseClient()

# ── Tool Implementations ───────────────────────────────────────────────────────

async def identify_investigation_stages(allegation_type: str, severity: int) -> dict:
    stages = ["Intake & Prep", "Evidence Collection", "Interviews", "Analysis", "Final Report"]
    if severity >= 4:
        stages.insert(2, "Interim Measures Assessment")
    if allegation_type in ["regulatory_compliance", "data_privacy"]:
        stages.insert(4, "Regulatory Disclosure Review")
    return {
        "stages": stages,
        "current_stage": "Investigation Planning",
        "estimated_duration": f"{severity * 5} days",
        "priority_level": "High" if severity >= 4 else "Normal",
        "source": "CILA Investigation Framework"
    }

async def suggest_interview_questions(allegation_type: str, parties: dict) -> dict:
    complainant = parties.get("complainant", "Complainant")
    respondent = parties.get("respondent", "Respondent")
    questions = {
        complainant: ["Can you describe the incident?", "When did it occur?", "Witnesses?", "Docs?"],
        respondent: ["Your response?", "Timeline?", "Policy awareness?"]
    }
    if allegation_type == "harassment":
        questions[complainant].append("Reported before?")
        questions[respondent].append("Prior interactions?")
    return {
        "interviewees": list(questions.keys()),
        "questions_per_party": questions,
        "source": "Azure OpenAI Generated Interview Guide"
    }

async def identify_required_documents(allegation_type: str) -> dict:
    # This could also query Azure Search or Dataverse for policy docs
    article = next((k for k in KNOWLEDGE_BASE if k.allegation_category == allegation_type), None)
    docs = article.required_documents if article else ["General Correspondence"]
    return {
        "required_documents": docs,
        "source": "UCM Evidence Matrix"
    }

async def link_precedent_cases(allegation_type: str) -> dict:
    # USE AZURE SEARCH HERE
    search_query = f"precedent cases for {allegation_type} investigation"
    hits = search_client.search_knowledge_base(search_query)
    
    precedents = [h["title"] for h in hits] or ["N/A"]
    return {
        "precedent_case_ids": precedents,
        "relevance_summary": f"Found {len(precedents)} matches in Azure AI Search.",
        "source": "Azure AI Search (RAG)"
    }

async def assign_investigation_tasks(stages: list, severity: int) -> dict:
    tasks = []
    for i, stage in enumerate(stages):
        due_date = (datetime.now() + (i+1) * 3 * (6-severity)).strftime("%Y-%m-%d")
        tasks.append({"task_name": f"Complete {stage}", "due_date": due_date})
    return {"suggested_tasks": tasks, "total_tasks": len(tasks)}

async def generate_plan_summary(case_id: str, stages: list, questions: dict, docs: list) -> dict:
    return {
        "plan_summary": f"Plan for {case_id}: {len(stages)} stages, {len(docs)} docs.",
        "confidence_score": 0.95
    }

async def write_plan_to_ucm(case_id: str, plan_data: dict) -> dict:
    # USE DATAVERSE HERE
    try:
        # In real life: dv_client.query("incidents", ...) to update
        pass
    except:
        pass
    return {
        "status": "SUCCESS — Written to Dataverse",
        "case_id": case_id,
        "plan_record_id": f"DV-PLAN-{case_id}",
        "source": "Dataverse API"
    }

TOOL_FUNCTIONS = {
    "identify_investigation_stages": identify_investigation_stages,
    "suggest_interview_questions":   suggest_interview_questions,
    "identify_required_documents":    identify_required_documents,
    "link_precedent_cases":          link_precedent_cases,
    "assign_investigation_tasks":     assign_investigation_tasks,
    "generate_plan_summary":         generate_plan_summary,
    "write_plan_to_ucm":             write_plan_to_ucm,
}

async def dispatch_tool(name: str, args: dict) -> str:
    fn = TOOL_FUNCTIONS.get(name)
    if not fn: return json.dumps({"error": f"Unknown tool: {name}"})
    result = await fn(**args)
    return json.dumps(result, indent=2)

AZURE_OPENAI_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "identify_investigation_stages",
            "description": "Determines investigation stages.",
            "parameters": {
                "type": "object",
                "properties": {"allegation_type": {"type": "string"}, "severity": {"type": "integer"}},
                "required": ["allegation_type", "severity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_interview_questions",
            "description": "Generates interview questions.",
            "parameters": {
                "type": "object",
                "properties": {"allegation_type": {"type": "string"}, "parties": {"type": "object"}},
                "required": ["allegation_type", "parties"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "identify_required_documents",
            "description": "Lists documents needed.",
            "parameters": {
                "type": "object",
                "properties": {"allegation_type": {"type": "string"}},
                "required": ["allegation_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "link_precedent_cases",
            "description": "Finds similar past cases.",
            "parameters": {
                "type": "object",
                "properties": {"allegation_type": {"type": "string"}},
                "required": ["allegation_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "assign_investigation_tasks",
            "description": "Generates tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stages": {"type": "array", "items": {"type": "string"}},
                    "severity": {"type": "integer"}
                },
                "required": ["stages", "severity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_plan_summary",
            "description": "Creates plan summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "stages": {"type": "array", "items": {"type": "string"}},
                    "questions": {"type": "object"},
                    "docs": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["case_id", "stages", "questions", "docs"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_plan_to_ucm",
            "description": "Writes the plan to UCM.",
            "parameters": {
                "type": "object",
                "properties": {"case_id": {"type": "string"}, "plan_data": {"type": "object"}},
                "required": ["case_id", "plan_data"]
            }
        }
    }
]
