"""
BRI Agent Chat Engine — Azure OpenAI "On Your Data" Simulation
Simulates the RAG pipeline: Dataverse → Embeddings → Azure AI Search → Chatbot
Handles: case lookup, next steps, similar cases, attorney info, investigation plan,
         case timeline, allegation breakdown, discipline policy, contacts, documents
"""

import re
import logging
from logger_config import logger

# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATED DATAVERSE — BRI CASES DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

BRI_CASES_DB = {
    "BRI-26-08314": {
        "case_id": "BRI-26-08314",
        "case_title": "Cummins (Confidentiality Breach) - U.S.",
        "area_country": "United States",
        "assigned_attorney": "Alicia Cullen",
        "received_date": "21-Aug-2025",
        "status": "Active",
        "case_resolution": "Information Not Provided",
        "type": "Investigation",
        "issue_type": "Confidential Information - Misuse of Confidential Information or Data",
        "allegation_summary": (
            "In August 2025, a confidentiality breach occurred involving the release of an internal Microsoft document "
            "addressing a Cummins generator quality issue. The document, which detailed a manufacturing defect in "
            "exhaust valves produced between April 2023 and May 2025, was distributed externally without Cummins' "
            "permission. The issue involves out-of-tolerance valve stems that can lead to catastrophic engine failure "
            "and engine replacement. Microsoft is conducting an internal review and expects formal notification from "
            "Cummins regarding the breach. Immediate safety protocols are being reviewed to address the matter."
        ),
        "crm_link": "View CRM Details",
        "next_steps": [
            "The retrieved case details for [BRI-26-08314] indicate that Microsoft is conducting an internal review "
            "and expects formal notification from Cummins regarding the breach. Immediate safety protocols are being "
            "reviewed to address the matter for affected generators. However, specific next steps beyond these actions "
            "are not provided in the available case data.",
            "If you need further information on next steps, you may want to consult the assigned attorney, Alicia Cullen, "
            "or check for updates in the CRM link provided."
        ],
        "discipline": "Ranges from written warnings, termination, administrative closure, or referral to management depending on substantiation.",
        "contacts": ["Internal Audit Team", "Cummins Legal", "Microsoft Compliance", "CELA BRI Team"],
        "timeline": [
            {"date": "21-Aug-2025", "event": "Case received via NAVEX hotline reporting channel"},
            {"date": "22-Aug-2025", "event": "Initial intake review completed by BRI Intake Manager"},
            {"date": "25-Aug-2025", "event": "Assigned to Alicia Cullen (Aligned Attorney)"},
            {"date": "28-Aug-2025", "event": "Preliminary document review initiated — internal Microsoft docs flagged"},
            {"date": "02-Sep-2025", "event": "Cross-reference with Cummins contract terms initiated"},
            {"date": "10-Sep-2025", "event": "Internal review underway — IT security logs requested"},
            {"date": "15-Sep-2025", "event": "Awaiting formal notification from Cummins"},
        ],
        "investigation_plan": {
            "stages": ["Intake & Prep", "Evidence Collection", "Interim Measures Assessment", "Witness Interviews", "Analysis & Review", "Regulatory Disclosure Review", "Final Report"],
            "status": "Evidence Collection",
            "questions": [
                "Who authorized the external distribution of the Cummins document?",
                "What was the full distribution chain — internal and external recipients?",
                "Were there any prior incidents of confidential information sharing with Cummins?",
                "What access controls were in place for the document repository?",
                "Was the document classified under Microsoft's Data Handling Standard (DHS)?",
                "Are there contractual confidentiality obligations with Cummins that were breached?",
                "What remediation steps have been taken to prevent future breaches?",
                "Who are the key witnesses with knowledge of the document's distribution?",
            ],
            "documents_required": [
                "Original internal Microsoft document (generator quality issue report)",
                "Cummins Generator Warranty & Service Agreement",
                "Email correspondence chain showing external distribution",
                "Teams/Slack chat logs referencing the document",
                "Document access audit logs from SharePoint/OneDrive",
                "NDA & Confidentiality Agreement with Cummins",
                "Microsoft Data Handling Standard (DHS) classification records",
                "Witness interview transcripts (to be generated)",
            ],
        },
        "attorney_info": {
            "name": "Alicia Cullen",
            "role": "Aligned Attorney",
            "seniority": "Senior",
            "specializations": ["Confidentiality Breach", "IP Protection", "Regulatory Compliance"],
            "active_cases": 8,
            "max_cases": 15,
            "business_unit": "Business and Regulatory Investigations",
            "bar_states": ["CA", "WA", "NY"],
            "email": "alicia.cullen@microsoft.com",
        },
    },
    "BRI-24-01183": {
        "case_id": "BRI-24-01183",
        "case_title": "Request to Share Microsoft's IP with NTTData - Japan",
        "area_country": "Japan",
        "assigned_attorney": "David Park",
        "received_date": "15-Mar-2024",
        "status": "Closed",
        "case_resolution": "Substantiated — Written Warning",
        "type": "Investigation",
        "issue_type": "Confidential Information - Misuse of Confidential Information or Data",
        "allegation_summary": "An employee in the Japan office requested to share proprietary Microsoft AI training models and internal API documentation with NTTData during a joint project discussion. The request bypassed the established IP review process and was flagged by the regional compliance officer.",
        "discipline": "Written warning issued. Employee completed mandatory IP awareness training.",
        "contacts": ["Japan Regional Compliance", "IP Review Board"],
        "next_steps": [
            "Case is closed. Written warning was issued to the employee.",
            "Mandatory IP awareness training was completed on 20-May-2024.",
            "No further action required. Case archived for precedent reference."
        ],
        "timeline": [
            {"date": "15-Mar-2024", "event": "Case received — employee request flagged"},
            {"date": "22-Mar-2024", "event": "Investigation initiated by David Park"},
            {"date": "15-Apr-2024", "event": "Interviews completed"},
            {"date": "30-Apr-2024", "event": "Written warning issued"},
            {"date": "20-May-2024", "event": "IP training completed — case closed"},
        ],
    },
    "BRI-26-08049": {
        "case_id": "BRI-26-08049",
        "case_title": "Misuse of Privileged Access - India",
        "area_country": "India",
        "assigned_attorney": "Priya Sharma",
        "received_date": "02-Jul-2025",
        "status": "Active",
        "case_resolution": "Pending",
        "type": "Investigation",
        "issue_type": "Confidential Information - Misuse of Confidential Information or Data",
        "allegation_summary": "A senior engineer in the Hyderabad office allegedly leveraged elevated Azure AD privileges to access confidential HR performance review data for colleagues in their team. The access pattern was detected by the SIEM system during a routine security audit.",
        "discipline": "Under investigation. Preliminary access revocation completed.",
        "contacts": ["MSIT Security", "India HR", "Azure AD Admin Team"],
        "next_steps": [
            "Complete forensic analysis of Azure AD access logs for the past 90 days.",
            "Interview the employee and their direct manager.",
            "Review whether accessed data was exfiltrated or shared.",
            "Coordinate with India HR on interim measures."
        ],
    },
    "BRI-26-08050": {
        "case_id": "BRI-26-08050",
        "case_title": "Misuse of Privileged Access / Third Party Data - U.S.",
        "area_country": "United States",
        "assigned_attorney": "James Miller",
        "received_date": "03-Jul-2025",
        "status": "Active",
        "case_resolution": "Pending",
        "type": "Investigation",
        "issue_type": "Confidential Information - Misuse of Confidential Information or Data",
        "allegation_summary": "A contractor working on the Azure Government Cloud project accessed customer telemetry data from a government agency without proper authorization. The contractor's access exceeds the scope defined in their Statement of Work (SOW).",
        "discipline": "Pending review. Contractor access suspended.",
        "contacts": ["Azure Gov Cloud Security", "Vendor Management", "Government Compliance"],
        "next_steps": [
            "Review contractor SOW and access provisioning records.",
            "Determine extent of unauthorized data access.",
            "Assess potential FedRAMP compliance implications.",
            "Coordinate with vendor management for contract review."
        ],
    },
    "BRI-26-08941": {
        "case_id": "BRI-26-08941",
        "case_title": "Unauthorized External Release of MRI Denoising Models - U.S.",
        "area_country": "United States",
        "assigned_attorney": "Sarah Kim",
        "received_date": "18-Aug-2025",
        "status": "Active",
        "case_resolution": "Pending",
        "type": "Investigation",
        "issue_type": "Confidential Information - Misuse of Confidential Information or Data",
        "allegation_summary": "A Microsoft Research engineer published a proprietary MRI denoising deep learning model to an open-source GitHub repository without completing the internal OSS release review process. The model contains patentable algorithms that are part of a pending patent application.",
        "discipline": "Under investigation. Repository taken down pending review.",
        "contacts": ["Microsoft Research Legal", "OSS Compliance", "Patent Team"],
        "next_steps": [
            "Assess patent exposure from public release of the algorithm.",
            "Review GitHub repository fork history for downstream distribution.",
            "Interview the researcher and their manager.",
            "Coordinate with Patent Team on impact assessment."
        ],
    },
    "BRI-26-10853": {
        "case_id": "BRI-26-10853",
        "case_title": "Concerns with PII Shared - Netherlands",
        "area_country": "Netherlands",
        "assigned_attorney": "Marc Van Der Berg",
        "received_date": "10-Oct-2025",
        "status": "Active",
        "case_resolution": "Pending",
        "type": "Investigation",
        "issue_type": "Confidential Information - Misuse of Confidential Information or Data",
        "allegation_summary": "A customer support representative in the Netherlands office inadvertently shared a spreadsheet containing PII (names, email addresses, phone numbers) of 2,847 EU customers with an unauthorized marketing vendor during a campaign coordination call.",
        "discipline": "GDPR assessment in progress. 72-hour DPA notification timeline triggered.",
        "contacts": ["EU DPO Office", "Netherlands HR", "Marketing Vendor Relations"],
        "next_steps": [
            "Complete GDPR Article 33 breach assessment within 72 hours.",
            "Notify Dutch Data Protection Authority (Autoriteit Persoonsgegevens) if required.",
            "Assess scope of PII exposure — confirm number of affected data subjects.",
            "Implement remediation with marketing vendor (data deletion confirmation).",
            "Review and strengthen data sharing protocols with third-party vendors."
        ],
    },
    "BRI-25-03020": {
        "case_id": "BRI-25-03020",
        "case_title": "Using Corporate Card for Personal Use - India",
        "area_country": "India",
        "assigned_attorney": "Rahul Mehta",
        "received_date": "22-Feb-2025",
        "status": "Closed",
        "case_resolution": "Substantiated — Written Warning & Repayment",
        "type": "Investigation",
        "issue_type": "Expenses / Corporate Card Misuse",
        "allegation_summary": "An employee in the Bangalore office used their corporate AMEX card for personal purchases totalling $3,200 over a 4-month period, including electronics, travel, and dining expenses that were not business-related.",
        "discipline": "Written warning and repayment plan ($3,200 over 6 months).",
        "contacts": ["India Finance", "Employee Relations"],
        "next_steps": ["Case closed. Repayment plan in progress — 3 of 6 installments received."],
    },
    "BRI-25-04374": {
        "case_id": "BRI-25-04374",
        "case_title": "Concern Regarding Personal Usage of AMEX - U.S.",
        "area_country": "United States",
        "assigned_attorney": "Laura Chen",
        "received_date": "15-Apr-2025",
        "status": "Closed",
        "case_resolution": "Substantiated — Administrative Closure",
        "type": "Investigation",
        "issue_type": "Expenses / Corporate Card Misuse",
        "allegation_summary": "Personal charges of $1,450 on corporate AMEX card flagged during quarterly reconciliation. Employee self-reported and initiated voluntary repayment before investigation began.",
        "discipline": "Administrative closure after complete repayment. Employee counseled on policy.",
        "contacts": ["US Finance", "Employee Relations"],
        "next_steps": ["Case closed. Full repayment received. No further action."],
    },
    "BRI-25-05370": {
        "case_id": "BRI-25-05370",
        "case_title": "AMEX Personal Use - Korea",
        "area_country": "Korea",
        "assigned_attorney": "Ji-Yeon Park",
        "received_date": "20-May-2025",
        "status": "Closed",
        "case_resolution": "Substantiated — Written Warning",
        "type": "Investigation",
        "issue_type": "Expenses / Corporate Card Misuse",
        "allegation_summary": "Corporate AMEX card used for personal travel expenses including domestic flights and hotel stays totalling KRW 2,800,000 (approx. $2,100 USD).",
        "discipline": "Written warning. Card spending limit reduced.",
        "contacts": ["Korea Finance", "Korea HR"],
        "next_steps": ["Case closed. Written warning issued. Card limit reduced."],
    },
    "BRI-26-08569": {
        "case_id": "BRI-26-08569",
        "case_title": "Expense Concerns - Request to Deactivate AMEX - Korea",
        "area_country": "Korea",
        "assigned_attorney": "Ji-Yeon Park",
        "received_date": "05-Aug-2025",
        "status": "Active",
        "case_resolution": "Pending",
        "type": "Investigation",
        "issue_type": "Expenses / Corporate Card Misuse",
        "allegation_summary": "A manager in the Seoul office requested deactivation of an employee's corporate AMEX card after discovering a pattern of suspicious expense claims over 6 months totalling KRW 5,200,000 (approx. $3,900 USD). Claims include duplicate submissions and inflated receipt amounts.",
        "discipline": "Under review. Card deactivated pending investigation.",
        "contacts": ["Korea Finance", "Korea HR", "Expense Audit Team"],
        "next_steps": [
            "Complete forensic review of all expense claims from past 12 months.",
            "Cross-reference submitted receipts with merchant records.",
            "Interview employee and reporting manager.",
            "Determine if pattern constitutes policy violation or fraud."
        ],
    },
    "BRI-26-11793": {
        "case_id": "BRI-26-11793",
        "case_title": "Potential Corporate Card Policy Violation - Spain",
        "area_country": "Spain",
        "assigned_attorney": "Carlos Ruiz",
        "received_date": "15-Nov-2025",
        "status": "Active",
        "case_resolution": "Pending",
        "type": "Investigation",
        "issue_type": "Expenses / Corporate Card Misuse",
        "allegation_summary": "Suspected violation of corporate card usage policies in the Madrid office. Employee submitted meal expenses for non-business dinners with personal guests, totalling €2,800 over 3 months. Manager flagged pattern during quarterly expense review.",
        "discipline": "Pending investigation. Employee notified.",
        "contacts": ["Spain Finance", "Spain HR", "EMEA Compliance"],
        "next_steps": [
            "Review all meal expense submissions for the past 6 months.",
            "Verify attendee lists against employee directory and Outlook calendar.",
            "Interview employee regarding business justification.",
            "Assess whether reimbursement or disciplinary action is appropriate."
        ],
    },
}

# Similar cases groupings
SIMILAR_CASES_MAP = {
    "BRI-26-08314": {
        "Confidential Information Misuse / Data Breach": {
            "issue_type": "Confidential Information - Misuse of Confidential Information or Data",
            "discipline": "Ranges from written warnings, termination, administrative closure, or referral to management depending on substantiation.",
            "cases": ["BRI-24-01183", "BRI-26-08049", "BRI-26-08050", "BRI-26-08941", "BRI-26-10853"],
        },
        "Expenses / Corporate Card Misuse": {
            "issue_type": "Expenses / Corporate Card Misuse",
            "discipline": "Written warnings, repayment plans, or administrative closure.",
            "cases": ["BRI-25-03020", "BRI-25-04374", "BRI-25-05370", "BRI-26-08569", "BRI-26-11793"],
        },
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE BASE — RAG Context Documents
# ═══════════════════════════════════════════════════════════════════════════════

KNOWLEDGE_BASE_ARTICLES = {
    "confidentiality_policy": {
        "title": "Microsoft Confidentiality & Data Handling Policy",
        "content": (
            "All Microsoft employees and contractors are required to handle confidential information in accordance with "
            "the Microsoft Data Handling Standard (DHS). Confidential information includes trade secrets, proprietary "
            "technology, customer data, employee PII, and any documents marked as 'Microsoft Confidential' or higher. "
            "External sharing of confidential information requires written approval from the appropriate data owner and "
            "must be governed by a valid NDA or confidentiality agreement. Violations may result in disciplinary action "
            "up to and including termination, and may trigger regulatory reporting obligations."
        ),
    },
    "investigation_framework": {
        "title": "CELA Investigation Lifecycle Framework (CILF)",
        "content": (
            "The CELA Investigation Lifecycle consists of 7 standard phases: (1) Intake & Triage — initial case receipt, "
            "severity assessment, and attorney assignment; (2) Scoping — define investigation scope, identify key witnesses, "
            "and preserve relevant evidence; (3) Evidence Collection — gather documents, communications, access logs, and "
            "digital forensics; (4) Witness Interviews — conduct structured interviews with complainant, respondent, and "
            "witnesses; (5) Analysis — evaluate evidence, assess credibility, identify policy violations; (6) Reporting — "
            "draft investigation report with findings, conclusions, and recommendations; (7) Remediation — implement "
            "corrective actions, monitor compliance, and close case."
        ),
    },
    "discipline_matrix": {
        "title": "BRI Discipline & Remediation Matrix",
        "content": (
            "Discipline ranges depend on severity, intent, and employee history: "
            "Level 1 (Minor/First Offense) — Verbal coaching, written warning; "
            "Level 2 (Moderate/Repeated) — Formal written warning, mandatory training, temporary role restriction; "
            "Level 3 (Serious) — Final written warning, demotion, transfer, bonus forfeiture; "
            "Level 4 (Severe/Willful) — Termination, referral to law enforcement, regulatory notification; "
            "Level 5 (Critical/Systemic) — Immediate termination, legal action, public disclosure if required. "
            "All discipline actions must be reviewed by Employee Relations and approved by the case attorney."
        ),
    },
    "gdpr_breach_protocol": {
        "title": "GDPR Data Breach Response Protocol",
        "content": (
            "Under GDPR Article 33, data breaches involving EU personal data must be reported to the relevant "
            "supervisory authority within 72 hours of becoming aware of the breach. The notification must include: "
            "nature of breach, categories and approximate number of data subjects, likely consequences, and measures "
            "taken to address the breach. If the breach is likely to result in high risk to individuals, affected "
            "data subjects must also be notified under Article 34. The EU DPO must be consulted for all assessments."
        ),
    },
    "expense_policy": {
        "title": "Corporate Card & Expense Policy",
        "content": (
            "Microsoft corporate cards (AMEX) are issued solely for authorized business expenses. Personal use is "
            "strictly prohibited. All expenses must be submitted with valid receipts within 30 days. Meal expenses "
            "for business purposes must include attendee names and business justification. Violations may result in "
            "card deactivation, repayment requirements, written warnings, or termination for repeated offenses. "
            "Managers are required to review and approve all direct report expenses quarterly."
        ),
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# INTENT DETECTION — Extended
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_case_id(text: str) -> str:
    """Extract BRI case ID from user text."""
    match = re.search(r"BRI-\d{2}-\d{4,5}", text, re.IGNORECASE)
    return match.group(0).upper() if match else None


def detect_intent(user_query: str) -> dict:
    """Detect intent from user query — expanded intents."""
    q = user_query.lower()
    case_id = _extract_case_id(user_query)

    if any(kw in q for kw in ["similar cases", "find me similar", "related cases", "find similar", "comparable"]):
        return {"intent": "similar_cases", "case_id": case_id}
    elif any(kw in user_query.lower() for kw in ["next step", "what should i do", "actionable", "plan next", "propose investigation steps"]):
        return {"intent": "next_steps", "case_id": case_id}
    elif any(kw in q for kw in ["attorney", "lawyer", "who is assigned", "assigned to", "counsel"]):
        return {"intent": "attorney_info", "case_id": case_id}
    elif any(kw in q for kw in ["investigation plan", "plan for", "investigation stages", "plan stages"]):
        return {"intent": "investigation_plan", "case_id": case_id}
    elif any(kw in q for kw in ["timeline", "history", "chronolog", "events", "when did"]):
        return {"intent": "timeline", "case_id": case_id}
    elif any(kw in q for kw in ["document", "evidence", "what documents", "required docs", "what do i need"]):
        return {"intent": "documents", "case_id": case_id}
    elif any(kw in q for kw in ["discipline", "penalty", "consequences", "what happens", "punishment"]):
        return {"intent": "discipline", "case_id": case_id}
    elif any(kw in q for kw in ["contact", "who to contact", "stakeholder", "team involved"]):
        return {"intent": "contacts", "case_id": case_id}
    elif any(kw in q for kw in ["allegation", "what happened", "describe the", "breakdown"]):
        return {"intent": "allegation", "case_id": case_id}
    elif any(kw in q for kw in ["policy", "guideline", "standard", "procedure", "protocol", "gdpr", "confidential"]):
        return {"intent": "policy", "case_id": case_id}
    elif any(kw in q for kw in ["latest", "status", "summary", "details", "what is", "tell me about", "info on", "update"]):
        return {"intent": "case_lookup", "case_id": case_id}
    elif case_id:
        return {"intent": "case_lookup", "case_id": case_id}
    else:
        return {"intent": "general", "case_id": None}


# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE FORMATTERS — Rich HTML output
# ═══════════════════════════════════════════════════════════════════════════════

def _format_case_summary(case: dict) -> str:
    """Format case summary as a rich HTML table."""
    case_id = case.get("case_id", "Unknown")
    
    rows_html = f"""
    <tr style="border-bottom: 1px solid #edebe9;"><td style="padding: 8px; font-weight: 600; background: #faf9f8; width: 35%;">Case ID</td><td style="padding: 8px;">{case_id}</td></tr>
    <tr style="border-bottom: 1px solid #edebe9;"><td style="padding: 8px; font-weight: 600; background: #faf9f8;">Title</td><td style="padding: 8px;">{case.get('case_title', 'N/A')}</td></tr>
    <tr style="border-bottom: 1px solid #edebe9;"><td style="padding: 8px; font-weight: 600; background: #faf9f8;">Area/Country</td><td style="padding: 8px;">{case.get('area_country', 'N/A')}</td></tr>
    <tr style="border-bottom: 1px solid #edebe9;"><td style="padding: 8px; font-weight: 600; background: #faf9f8;">Attorney</td><td style="padding: 8px;">{case.get('assigned_attorney', 'N/A')}</td></tr>
    <tr style="border-bottom: 1px solid #edebe9;"><td style="padding: 8px; font-weight: 600; background: #faf9f8;">Status</td><td style="padding: 8px;"><span style="background: #e1dfdd; padding: 2px 6px; border-radius: 2px;">{case.get('status', 'N/A')}</span></td></tr>
    <tr style="border-bottom: 1px solid #edebe9;"><td style="padding: 8px; font-weight: 600; background: #faf9f8;">Issue Type</td><td style="padding: 8px;">{case.get('issue_type', 'N/A')}</td></tr>
    """

    response_html = f"""<div style="font-family: 'Segoe UI', sans-serif;">
        <div style="background: #0078d4; color: white; padding: 10px 15px; border-radius: 4px 4px 0 0; font-size: 14px; font-weight: 600;">
            📁 Case Summary: {case_id}
        </div>
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #edebe9; font-size: 12px; color: #323130;">
            {rows_html}
        </table>
        <div style="padding: 12px; border: 1px solid #edebe9; border-top: none; background: #fff; font-size: 12px; line-height: 1.5;">
            <b style="color: #0078d4;">Allegation:</b><br>
            {case.get('allegation_summary', 'No summary available.')}
        </div>
        <div style="font-size: 11px; color: #605e5c; margin-top: 10px;">
            <i>Click <b>Accept</b> to sync this summary to the Profile and Allegation tabs.</i>
        </div>
    </div>"""
    return response_html


def _format_next_steps(data: dict) -> str:
    """Format next steps as rich HTML matching Image 1/2."""
    case_id = data.get("case_id", "Unknown")
    
    # Formatted List
    steps_html = "<ul>"
    for step in data.get("next_steps", ["Consult with lead attorney for guidance."]):
        steps_html += f'<li style="margin-bottom: 6px;">{step}</li>'
    steps_html += "</ul>"
    
    # Structured Table if available
    structured_html = ""
    if "proposed_investigative_steps" in data:
        structured_html = """
        <div style="margin-top: 15px; border: 1px solid #edebe9; border-radius: 4px;">
            <div style="background: #f3f2f1; padding: 8px; font-weight: 600; font-size: 12px; border-bottom: 1px solid #edebe9;">
                Proposed Investigative Plan Structure
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
                <tr style="background: #faf9f8; border-bottom: 1px solid #edebe9;">
                    <th style="text-align: left; padding: 8px;">Step</th>
                    <th style="text-align: left; padding: 8px;">Owner</th>
                    <th style="text-align: left; padding: 8px;">Due Date</th>
                </tr>
        """
        for s in data["proposed_investigative_steps"]:
            structured_html += f"""
                <tr style="border-bottom: 1px dotted #edebe9;">
                    <td style="padding: 8px;">{s['Step']}</td>
                    <td style="padding: 8px;">{s['Owner']}</td>
                    <td style="padding: 8px;">{s['Due Date']}</td>
                </tr>
            """
        structured_html += "</table></div>"

    response_html = f"""<div style="font-family: 'Segoe UI', sans-serif;">
        <div style="background: #fff8f0; color: #844800; padding: 12px; border-radius: 4px; border-left: 4px solid #ffaa44; margin-bottom: 15px; font-size: 13px;">
            <b>📌 Actionable Next Steps</b> for Case <b>{case_id}</b>
        </div>
        {steps_html}
        {structured_html}
        <div style="font-size: 11px; color: #605e5c; margin-top: 10px;">
            <i>Click <b>Accept</b> to sync this structured plan to the Investigation Plan tab.</i>
        </div>
    </div>"""
    return response_html


def _format_similar_cases(case_id: str) -> str:
    """Format similar cases as rich HTML matching Image 2."""
    groups = SIMILAR_CASES_MAP.get(case_id, {})
    if not groups:
        return f"<p>No similar cases found for {case_id}.</p>"

    html = f"""<div style="font-family: 'Segoe UI', sans-serif; padding: 8px 0;">
<div style="color: #d83b01; font-weight: 600; font-size: 14px; margin-bottom: 8px;">
    Prompt: Find me similar cases to case {case_id} in relation to case contacts, issue type, discipline
</div>
<div style="font-size: 13px; color: #323130; line-height: 1.6; margin-left: 16px;">
    <b>Similar cases to <a href="#" style="color: #0078d4;">[{case_id}]</a> in relation to case contacts, issue type, and discipline:</b><br>"""

    for idx, (category, group_data) in enumerate(groups.items(), 1):
        html += f"""<br><b>{idx}. {category}</b>
    <ul style="margin: 4px 0 4px 10px; padding: 0; list-style: disc;">
        <li><b>Representative Cases:</b>
            <ul style="margin: 2px 0 2px 10px; list-style: none; padding: 0;">"""

        for cid in group_data["cases"]:
            case_data = BRI_CASES_DB.get(cid, {})
            title = case_data.get("case_title", "Unknown")
            html += f"""
                <li style="margin: 3px 0;">• <a href="#" style="color: #0078d4; text-decoration: underline;">[{cid}]</a> ({title})</li>"""

        html += f"""
            </ul>
        </li>
        <li><b>Issue Type:</b> {group_data['issue_type']}</li>
        <li><b>Discipline:</b> {group_data['discipline']}</li>
    </ul>"""

    html += "</div></div>"
    return html


def _format_attorney_info(case: dict) -> str:
    """Format attorney details."""
    atty = case.get("attorney_info", {})
    if not atty:
        return f"""<div style="font-family: 'Segoe UI', sans-serif; padding: 8px; font-size: 13px; color: #323130;">
        <b>👤 Assigned Attorney:</b> {case.get('assigned_attorney', 'N/A')}<br>
        <i>Detailed attorney profile not available in Dataverse for this case.</i>
        </div>"""

    specs = ", ".join(atty.get("specializations", []))
    bars = ", ".join(atty.get("bar_states", []))
    load_pct = int((atty['active_cases'] / atty['max_cases']) * 100) if atty.get('max_cases') else 0

    return f"""<div style="font-family: 'Segoe UI', sans-serif; padding: 8px 0;">
<div style="color: #d83b01; font-weight: 600; font-size: 14px; margin-bottom: 8px;">
    Attorney Profile — {case['case_id']}
</div>
<div style="font-size: 13px; color: #323130; line-height: 1.8; background: #faf9f8; padding: 14px; border-radius: 4px; border: 1px solid #edebe9;">
    <span style="color: #0078d4; font-size: 18px;">👤</span> <b style="font-size: 15px;">{atty['name']}</b>
    <span style="background: #0078d4; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; margin-left: 8px;">{atty['role']}</span><br>
    <b>Seniority:</b> {atty['seniority']}<br>
    <b>Business Unit:</b> {atty.get('business_unit', 'N/A')}<br>
    <b>Specializations:</b> {specs}<br>
    <b>Bar Admissions:</b> {bars}<br>
    <b>Workload:</b> {atty['active_cases']}/{atty['max_cases']} cases ({load_pct}%)
    <div style="background: #edebe9; height: 6px; border-radius: 3px; margin: 4px 0;">
        <div style="background: {'#107c10' if load_pct < 70 else '#f7630c' if load_pct < 90 else '#d13438'}; width: {load_pct}%; height: 6px; border-radius: 3px;"></div>
    </div>
    <b>Contact:</b> <a href="#" style="color: #0078d4;">{atty.get('email', 'N/A')}</a>
</div></div>"""


def _format_investigation_plan(case: dict) -> str:
    """Format investigation plan with stages and questions."""
    plan = case.get("investigation_plan", {})
    if not plan:
        return f"""<div style="font-family: 'Segoe UI', sans-serif; padding: 8px; font-size: 13px;">
            No detailed investigation plan available for {case['case_id']}. Run the Copilot Investigation Planner to generate one.
        </div>"""

    stages_html = ""
    current = plan.get("status", "")
    for i, stage in enumerate(plan.get("stages", []), 1):
        if stage == current:
            icon = "🔵"
            style = "font-weight: 700; color: #0078d4;"
        elif i < plan.get("stages", []).index(current) + 1 if current in plan.get("stages", []) else False:
            icon = "✅"
            style = "color: #107c10;"
        else:
            icon = "⚪"
            style = "color: #605e5c;"
        stages_html += f'<div style="{style} padding: 3px 0;">{icon} Stage {i}: {stage}</div>'

    questions_html = ""
    for i, q in enumerate(plan.get("questions", []), 1):
        questions_html += f'<li style="margin: 4px 0;">{q}</li>'

    return f"""<div style="font-family: 'Segoe UI', sans-serif; padding: 8px 0;">
<div style="color: #d83b01; font-weight: 600; font-size: 14px; margin-bottom: 8px;">
    Investigation Plan — {case['case_id']}
</div>
<div style="font-size: 13px; color: #323130; line-height: 1.6;">
    <b>📋 Investigation Stages:</b>
    <div style="margin: 8px 0 12px 8px;">
        {stages_html}
    </div>
    <b>❓ Key Investigation Questions ({len(plan.get('questions', []))}):</b>
    <ol style="margin: 6px 0; padding-left: 20px; font-size: 12px;">
        {questions_html}
    </ol>
</div></div>"""


def _format_timeline(case: dict) -> str:
    """Format case timeline."""
    events = case.get("timeline", [])
    if not events:
        return f"""<div style="font-family: 'Segoe UI', sans-serif; padding: 8px; font-size: 13px;">
            No timeline data available for {case['case_id']}.
        </div>"""

    items = ""
    for ev in events:
        items += f"""
        <div style="display: flex; gap: 10px; padding: 6px 0; border-bottom: 1px solid #f3f2f1;">
            <div style="min-width: 100px; font-weight: 600; color: #0078d4; font-size: 11px;">{ev['date']}</div>
            <div style="font-size: 12px; color: #323130;">{ev['event']}</div>
        </div>"""

    return f"""<div style="font-family: 'Segoe UI', sans-serif; padding: 8px 0;">
<div style="color: #d83b01; font-weight: 600; font-size: 14px; margin-bottom: 8px;">
    Case Timeline — {case['case_id']}
</div>
<div style="font-size: 13px; color: #323130; background: #faf9f8; padding: 12px; border-radius: 4px; border: 1px solid #edebe9;">
    {items}
</div></div>"""


def _format_documents(case: dict) -> str:
    """Format required documents list."""
    plan = case.get("investigation_plan", {})
    docs = plan.get("documents_required", [])
    if not docs:
        return f"""<div style="font-family: 'Segoe UI', sans-serif; padding: 8px; font-size: 13px;">
            No specific document requirements available for {case['case_id']}. Run the Investigation Planner to generate a document list.
        </div>"""

    items = "".join([f'<li style="margin: 4px 0;">{d}</li>' for d in docs])
    return f"""<div style="font-family: 'Segoe UI', sans-serif; padding: 8px 0;">
<div style="color: #d83b01; font-weight: 600; font-size: 14px; margin-bottom: 8px;">
    Required Documents — {case['case_id']}
</div>
<div style="font-size: 13px; color: #323130; line-height: 1.6;">
    <b>📄 {len(docs)} documents identified for collection:</b>
    <ul style="margin: 6px 0; padding-left: 20px; font-size: 12px;">
        {items}
    </ul>
</div></div>"""


def _format_contacts(case: dict) -> str:
    """Format case contacts."""
    contacts = case.get("contacts", [])
    items = "".join([f'<li style="margin: 3px 0;">📧 {c}</li>' for c in contacts])
    return f"""<div style="font-family: 'Segoe UI', sans-serif; padding: 8px 0;">
<div style="color: #d83b01; font-weight: 600; font-size: 14px; margin-bottom: 8px;">
    Key Contacts — {case['case_id']}
</div>
<div style="font-size: 13px; color: #323130;">
    <ul style="margin: 6px 0; padding-left: 16px; list-style: none;">
        {items}
    </ul>
</div></div>"""


def _format_discipline(case: dict) -> str:
    """Format discipline info with policy context."""
    policy = KNOWLEDGE_BASE_ARTICLES.get("discipline_matrix", {})
    return f"""<div style="font-family: 'Segoe UI', sans-serif; padding: 8px 0;">
<div style="color: #d83b01; font-weight: 600; font-size: 14px; margin-bottom: 8px;">
    Discipline & Remediation — {case['case_id']}
</div>
<div style="font-size: 13px; color: #323130; line-height: 1.6;">
    <b>⚖️ Case-Specific Discipline:</b><br>
    <div style="background: #fff4ce; border-left: 3px solid #f7630c; padding: 10px; margin: 6px 0; font-size: 12px;">
        {case.get('discipline', 'Not yet determined.')}
    </div>
    <br><b>📖 BRI Discipline Matrix (Policy Reference):</b><br>
    <div style="background: #f3f2f1; padding: 10px; border-radius: 4px; margin: 6px 0; font-size: 11px; line-height: 1.6;">
        {policy.get('content', 'Policy document not available.')}
    </div>
</div></div>"""


def _format_allegation(case: dict) -> str:
    """Format detailed allegation breakdown."""
    return f"""<div style="font-family: 'Segoe UI', sans-serif; padding: 8px 0;">
<div style="color: #d83b01; font-weight: 600; font-size: 14px; margin-bottom: 8px;">
    Allegation Breakdown — {case['case_id']}
</div>
<div style="font-size: 13px; color: #323130; line-height: 1.6;">
    <b>📋 Case Title:</b> {case['case_title']}<br>
    <b>📑 Issue Type:</b> {case['issue_type']}<br><br>
    <b>📝 Full Allegation Details:</b>
    <div style="background: #faf9f8; border-left: 3px solid #d83b01; padding: 12px; margin: 8px 0; font-size: 12px; line-height: 1.7;">
        {case['allegation_summary']}
    </div>
    <b>⚖️ Current Discipline Status:</b> {case.get('discipline', 'Not yet determined.')}<br>
    <b>📌 Case Status:</b> {case['status']}<br>
    <b>🌐 Jurisdiction:</b> {case['area_country']}
</div></div>"""


def _format_policy(query: str) -> str:
    """Return relevant policy articles from the knowledge base."""
    q = query.lower()
    relevant = []
    if "gdpr" in q or "privacy" in q or "pii" in q or "data protection" in q:
        relevant.append(KNOWLEDGE_BASE_ARTICLES.get("gdpr_breach_protocol", {}))
    if "confidential" in q or "data handling" in q or "nda" in q:
        relevant.append(KNOWLEDGE_BASE_ARTICLES.get("confidentiality_policy", {}))
    if "expense" in q or "card" in q or "amex" in q:
        relevant.append(KNOWLEDGE_BASE_ARTICLES.get("expense_policy", {}))
    if "discipline" in q or "penalty" in q or "termination" in q:
        relevant.append(KNOWLEDGE_BASE_ARTICLES.get("discipline_matrix", {}))
    if "investigation" in q or "framework" in q or "lifecycle" in q:
        relevant.append(KNOWLEDGE_BASE_ARTICLES.get("investigation_framework", {}))

    if not relevant:
        relevant = list(KNOWLEDGE_BASE_ARTICLES.values())[:2]

    articles_html = ""
    for art in relevant:
        if art:
            articles_html += f"""
            <div style="background: #f3f2f1; padding: 12px; border-radius: 4px; margin: 8px 0; border-left: 3px solid #0078d4;">
                <b style="color: #0078d4;">{art.get('title', 'Policy')}</b><br>
                <span style="font-size: 12px; line-height: 1.6;">{art.get('content', '')}</span>
            </div>"""

    return f"""<div style="font-family: 'Segoe UI', sans-serif; padding: 8px 0;">
<div style="color: #d83b01; font-weight: 600; font-size: 14px; margin-bottom: 8px;">
    📖 Policy & Guidelines — Knowledge Base (RAG)
</div>
<div style="font-size: 13px; color: #323130;">
    <i>Retrieved from Azure AI Search index:</i>
    {articles_html}
</div></div>"""


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CHAT ENGINE — Azure OpenAI "On Your Data" Simulation
# ═══════════════════════════════════════════════════════════════════════════════

def process_query(user_query: str) -> dict:
    """
    Process a user query through the simulated RAG pipeline:
    1. Dataverse lookup → case data
    2. Azure AI Search → knowledge base / similar cases
    3. Azure OpenAI → formatted response
    
    Returns dict with 'response' (HTML) and 'pipeline_stages'.
    """
    intent_data = detect_intent(user_query)
    intent = intent_data["intent"]
    case_id = intent_data["case_id"]

    pipeline = []

    # Stage 1: Dataverse Lookup
    pipeline.append({"stage": "Dataverse", "status": "Searching...", "icon": "🔍"})
    case = BRI_CASES_DB.get(case_id) if case_id else None

    if case:
        pipeline[-1]["status"] = f"Found: {case_id}"
    else:
        pipeline[-1]["status"] = "No exact match"

    # Stage 2: Azure AI Search
    pipeline.append({"stage": "Azure AI Search", "status": "Retrieving context...", "icon": "📚"})

    # Stage 3: Azure OpenAI Response
    pipeline.append({"stage": "Azure OpenAI", "status": "Generating response...", "icon": "🤖"})

    # Generate response based on intent
    if intent == "case_lookup" and case:
        response_html = _format_case_summary(case)
        pipeline[-1]["status"] = "Case summary generated"
    elif intent == "next_steps" and case:
        response_html = _format_next_steps(case)
        pipeline[-1]["status"] = "Next steps generated"
    elif intent == "similar_cases" and case_id:
        pipeline[1]["status"] = f"Found {sum(len(g['cases']) for g in SIMILAR_CASES_MAP.get(case_id, {}).values())} similar cases"
        response_html = _format_similar_cases(case_id)
        pipeline[-1]["status"] = "Similar cases report generated"
    elif intent == "attorney_info" and case:
        response_html = _format_attorney_info(case)
        pipeline[-1]["status"] = "Attorney profile generated"
    elif intent == "investigation_plan" and case:
        response_html = _format_investigation_plan(case)
        pipeline[-1]["status"] = "Investigation plan rendered"
    elif intent == "timeline" and case:
        response_html = _format_timeline(case)
        pipeline[-1]["status"] = "Timeline rendered"
    elif intent == "documents" and case:
        response_html = _format_documents(case)
        pipeline[-1]["status"] = "Document list generated"
    elif intent == "contacts" and case:
        response_html = _format_contacts(case)
        pipeline[-1]["status"] = "Contacts retrieved"
    elif intent == "discipline" and case:
        pipeline[1]["status"] = "Retrieved discipline matrix from KB"
        response_html = _format_discipline(case)
        pipeline[-1]["status"] = "Discipline info generated"
    elif intent == "allegation" and case:
        response_html = _format_allegation(case)
        pipeline[-1]["status"] = "Allegation breakdown generated"
    elif intent == "policy":
        pipeline[1]["status"] = "Searched knowledge base articles"
        response_html = _format_policy(user_query)
        pipeline[-1]["status"] = "Policy articles retrieved"
    elif case_id and not case:
        response_html = f"""<div style="font-family: 'Segoe UI', sans-serif; padding: 8px; color: #a4262c;">
            <b>⚠️ Case {case_id} not found in Dataverse.</b><br>
            Please verify the case ID and try again. Available cases: {', '.join(BRI_CASES_DB.keys())}
        </div>"""
        pipeline[-1]["status"] = "Case not found"
    else:
        # General query — rich help response
        available = ", ".join(list(BRI_CASES_DB.keys())[:5])
        response_html = f"""<div style="font-family: 'Segoe UI', sans-serif; padding: 8px; font-size: 13px; color: #323130; line-height: 1.7;">
            I'm the <b>BRI Investigation Agent</b> powered by <b>Azure OpenAI "On Your Data"</b>.<br><br>
            <b>🔍 What I can do:</b><br>
            <div style="margin-left: 12px; margin-top: 4px;">
                📋 <b>Case Lookup:</b> "What is the latest on case BRI-26-08314"<br>
                📌 <b>Next Steps:</b> "What are the next steps for case BRI-26-08314"<br>
                🔗 <b>Similar Cases:</b> "Find me similar cases to BRI-26-08314"<br>
                👤 <b>Attorney Info:</b> "Who is the attorney assigned to BRI-26-08314"<br>
                📊 <b>Investigation Plan:</b> "Show me the investigation plan for BRI-26-08314"<br>
                🕐 <b>Timeline:</b> "Show timeline for BRI-26-08314"<br>
                📄 <b>Documents:</b> "What documents are needed for BRI-26-08314"<br>
                ⚖️ <b>Discipline:</b> "What are the discipline consequences for BRI-26-08314"<br>
                📧 <b>Contacts:</b> "Who are the contacts for BRI-26-08314"<br>
                📖 <b>Policy:</b> "What is the GDPR breach protocol"<br>
            </div><br>
            <b>Available cases:</b> {available}...
        </div>"""
        pipeline[-1]["status"] = "General help response"

    logger.info(f"Mock Engine: Processed intent={intent}, case_id={case_id}")
    return {"response": response_html, "pipeline_stages": pipeline, "intent": intent}
