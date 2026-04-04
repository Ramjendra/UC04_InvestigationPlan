"""
UC-04 AI Investigation Plan Generator - Tool Definitions for VerseAPI & Azure Directory
Pure async functions + OpenAI-format tool schemas for tool calling.
"""

import json
import logging
from datetime import datetime
from simulated_data import (
    ATTORNEYS, EXISTING_CASES, KNOWLEDGE_BASE, ALLEGATION_TAXONOMY,
    SLA_RULES, CaseRecord
)

log = logging.getLogger("uc04.tools")

# ── Mock Enterprise Services ──────────────────────────────────────────────────

class VerseAPIMock:
    """Mock for Microsoft Dataverse (VerseAPI)."""
    @staticmethod
    def get_standard_stages(allegation_type: str):
        stages = ["Intake & Prep", "Evidence Collection", "Interviews", "Analysis", "Final Report"]
        if allegation_type in ["regulatory_compliance", "data_privacy"]:
            stages.insert(4, "Regulatory Disclosure Review")
        return stages

    @staticmethod
    def write_plan(case_id: str, plan_data: dict):
        return {
            "status": "SUCCESS — Written to Dataverse (VerseAPI)",
            "case_id": case_id,
            "plan_record_id": f"VERS-{case_id}-PLAN",
            "timestamp": datetime.now().isoformat(),
            "vault_path": f"/ucm/evidence/case-{case_id}/"
        }

class AzureSearchMock:
    """Mock for Azure AI Search (Azure Directory)."""
    @staticmethod
    def search_precedents(allegation_type: str):
        article = next((k for k in KNOWLEDGE_BASE if k.allegation_category == allegation_type), None)
        return article.precedents if article else []

# ── Tool Implementations ───────────────────────────────────────────────────────


# ── Tool Implementations ───────────────────────────────────────────────────────

async def identify_investigation_stages(allegation_type: str, severity: int) -> dict:
    """Step 1: Determine the standard investigation stages for this case type."""
    stages = VerseAPIMock.get_standard_stages(allegation_type)
    
    if severity >= 4:
        stages.insert(2, "Interim Measures Assessment")
    
    return {
        "stages": stages,
        "current_stage": "Investigation Planning",
        "estimated_duration": f"{severity * 5} days",
        "priority_level": "High" if severity >= 4 else "Normal",
        "source": "VerseAPI: CILA Investigation Framework"
    }


async def suggest_interview_questions(allegation_type: str, parties: dict) -> dict:
    """Step 2: Generate specific interview questions for involved parties."""
    complainant = parties.get("complainant", "Complainant")
    respondent = parties.get("respondent", "Respondent")
    
    # Generic questions as base
    questions = {
        complainant: [
            "Can you describe the incident in detail?",
            "When and where did this occur?",
            "Were there any witnesses?",
            "Do you have any supporting documentation (emails, logs)?"
        ],
        respondent: [
            "What is your response to the allegation?",
            "Can you provide a timeline of your activities on the day of the incident?",
            "Are you aware of the relevant company policies?"
        ]
    }
    
    # Allegation-specific questions
    if allegation_type == "harassment":
        questions[complainant].append("Did you report this to anyone else at the time?")
        questions[respondent].append("Have you had similar interactions with the complainant before?")
    elif allegation_type == "regulatory_compliance":
        questions[complainant].append("Which specific regulation do you believe was violated?")
        questions[respondent].append("Did you follow the standard operating procedure for this transaction?")

    return {
        "interviewees": list(questions.keys()),
        "questions_per_party": questions,
        "suggested_order": [complainant, "Witnesses", respondent],
        "source": "Azure OpenAI (AD): Interview Guide"
    }


async def identify_required_documents(allegation_type: str) -> dict:
    """Step 3: List documents that must be collected for this investigation."""
    article = next((k for k in KNOWLEDGE_BASE if k.allegation_category == allegation_type), None)
    docs = article.required_documents if article else ["General Correspondence", "System Logs"]
    
    if allegation_type == "data_privacy":
        docs.extend(["Data Processing Agreement", "Encryption Logs"])
    elif allegation_type == "harassment":
        docs.extend(["HR Personnel File", "Slack/Teams Chat Exports"])
        
    return {
        "required_documents": docs,
        "collection_priority": "Immediate" if allegation_type in ["data_privacy", "regulatory_compliance"] else "Standard",
        "handling_instructions": "Secure all documents in the UCM Evidence Vault.",
        "source": "UCM Evidence Requirements Matrix"
    }


async def link_precedent_cases(allegation_type: str) -> dict:
    """Step 4: Search for similar past cases via Azure AI Search."""
    precedents = AzureSearchMock.search_precedents(allegation_type)
    
    return {
        "precedent_case_ids": precedents,
        "relevance_summary": f"Azure AI Search found {len(precedents)} historical cases.",
        "learning_points": "Review disciplinary actions in precedents for consistency.",
        "source": "Azure Directory Index: CELA Case History"
    }


async def assign_investigation_tasks(stages: list, severity: int) -> dict:
    """Step 5: Generate tasks for the UCM Task Board."""
    tasks = []
    for i, stage in enumerate(stages):
        due_date = (datetime.now() + (i+1) * 3 * (6-severity)).strftime("%Y-%m-%d")
        tasks.append({
            "task_name": f"Complete {stage}",
            "due_date": due_date,
            "status": "Pending",
            "owner": "Assigned Attorney"
        })
        
    return {
        "suggested_tasks": tasks,
        "total_tasks": len(tasks),
        "milestones": [stages[0], stages[-1]],
        "source": "Auto-Task Generator"
    }


async def generate_plan_summary(case_id: str, stages: list, questions: dict, docs: list) -> dict:
    """Step 6: Synthesize all information into a plan summary."""
    summary = f"Investigation Plan for {case_id}\n"
    summary += f"1. Stages: {', '.join(stages)}\n"
    summary += f"2. Interviews Planned for: {', '.join(questions.keys())}\n"
    summary += f"3. Key Documents: {', '.join(docs[:3])}..."
    
    return {
        "plan_summary": summary,
        "confidence_score": 0.88,
        "review_required": True,
        "reviewer": "Senior Attorney",
        "source": "Planning Orchestrator"
    }


async def write_plan_to_ucm(case_id: str, plan_data: dict) -> dict:
    """Step 7: Finalize and write the plan to Dataverse via VerseAPI."""
    result = VerseAPIMock.write_plan(case_id, plan_data)
    result["ui_update"] = "Investigation Tab populated with Draft Plan"
    return result


# ── Tool Dispatcher ────────────────────────────────────────────────────────────

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
    if not fn:
        log.error("Unknown tool called: %s", name)
        return json.dumps({"error": f"Unknown tool: {name}"})
    result = await fn(**args)
    return json.dumps(result, indent=2)


# ── Enterprise-Format Tool Schemas (VerseAPI & Azure Directory) ────────────────

ENTERPRISE_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "identify_investigation_stages",
            "description": "Determines the investigation stages via VerseAPI.",
            "parameters": {
                "type": "object",
                "properties": {
                    "allegation_type": {"type": "string"},
                    "severity": {"type": "integer"}
                },
                "required": ["allegation_type", "severity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_interview_questions",
            "description": "Generates interview questions via Azure OpenAI (AD).",
            "parameters": {
                "type": "object",
                "properties": {
                    "allegation_type": {"type": "string"},
                    "parties": {"type": "object"}
                },
                "required": ["allegation_type", "parties"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "identify_required_documents",
            "description": "Lists documents needed (UCM/VerseAPI index).",
            "parameters": {
                "type": "object",
                "properties": {
                    "allegation_type": {"type": "string"}
                },
                "required": ["allegation_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "link_precedent_cases",
            "description": "Finds similar past cases via Azure AI Search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "allegation_type": {"type": "string"}
                },
                "required": ["allegation_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "assign_investigation_tasks",
            "description": "Generates tasks for the VerseAPI Task Board.",
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
            "description": "Creates a structured summary via Azure OpenAI.",
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
            "description": "Writes the finished plan to Dataverse (VerseAPI).",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "plan_data": {"type": "object"}
                },
                "required": ["case_id", "plan_data"]
            }
        }
    }
]
