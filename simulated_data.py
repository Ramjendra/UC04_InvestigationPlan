"""
UC-04 Investigation Plan — Data Layer
Loads real data from all xlsx files in the project folder with step-by-step logging.
Falls back to built-in defaults if xlsx files are unavailable.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ─── Logger Setup ───────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler("planning.log", mode="a", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("UC04.data")

# ─── Data Models ────────────────────────────────────────────────────────────────

@dataclass
class Attorney:
    id: str
    name: str
    specializations: List[str]
    active_cases: int
    max_cases: int
    seniority: str          # "junior", "senior", "partner"
    availability: str       # "available", "busy", "out_of_office"
    bar_state: List[str]    # Licensed states
    business_unit: str = ""
    source: str = "default"

@dataclass
class CaseRecord:
    case_id: str
    allegation_type: str
    severity: int
    parties: Dict[str, str]
    assigned_attorney: Optional[str]
    status: str
    submitted_at: str
    priority_score: float
    queue_position: int
    sla_flag: str
    ticket_number: str = ""
    business_unit: str = ""
    complexity: str = ""
    summary: str = ""
    team_prefix: str = ""
    source_file: str = ""

@dataclass
class KBArticle:
    article_id: str
    allegation_category: str
    keywords: List[str]
    required_documents: List[str]
    typical_severity: str
    handling_notes: str
    precedents: List[str]

# ─── XLSX Loading Helpers ────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

XLSX_FILES = {
    "incident":          "incident.xlsx",
    "incident_bri":      "incident_BRI-26-11626.xlsx",
    "attorney":          "ucm_attorney.xlsx",
    "investigation_team":"ucm_caseinvestigationteam.xlsx",
    "inv_process":       "ucm_caseinvestigationprocess.xlsx",
    "process_flow":      "ucm_caseprocessflow.xlsx",
    "casenote":          "ucm_casenote.xlsx",
    "datasource":        "ucm_datasource.xlsx",
    "ext_investigator":  "ucm_externalinvestigator.xlsx",
}

def _xlsx_path(key: str) -> str:
    return os.path.join(BASE_DIR, XLSX_FILES[key])

def _try_read_xlsx(key: str):
    """Read an xlsx file using pandas. Returns DataFrame or None."""
    try:
        import pandas as pd
        path = _xlsx_path(key)
        if not os.path.exists(path):
            logger.warning("  [SKIP] File not found: %s", path)
            return None
        df = pd.read_excel(path)
        logger.info("  [OK]   Loaded %s — %d rows × %d cols", XLSX_FILES[key], len(df), len(df.columns))
        return df
    except ImportError:
        logger.warning("  [WARN] pandas/openpyxl not installed — xlsx loading skipped")
        return None
    except Exception as exc:
        logger.error("  [ERR]  Failed to read %s: %s", XLSX_FILES.get(key, key), exc)
        return None

def _try_read_bri_transposed(key: str) -> dict:
    """Read a transposed xlsx (col A = field name, col B = value) as a dict."""
    try:
        import pandas as pd
        path = _xlsx_path(key)
        if not os.path.exists(path):
            logger.warning("  [SKIP] File not found: %s", path)
            return {}
        df = pd.read_excel(path, header=None)
        df.columns = ["field", "value"]
        df = df[df["value"].notna()]
        result = dict(zip(df["field"].astype(str), df["value"]))
        logger.info("  [OK]   Loaded transposed %s — %d non-null fields", XLSX_FILES[key], len(result))
        return result
    except Exception as exc:
        logger.error("  [ERR]  Failed to read transposed %s: %s", XLSX_FILES.get(key, key), exc)
        return {}

# ─── Allegation Type Mapping ─────────────────────────────────────────────────────

# Maps business unit name / team prefix to allegation type
_BU_ALLEGATION_MAP = {
    "Business and Regulatory Investigations": "regulatory_compliance",
    "Workplace Investigation Team": "harassment",
    "Digital Markets Act": "regulatory_compliance",
    "UCM CELA ROOT BU": "employee_misconduct",
    "WIT": "harassment",
    "BRI": "regulatory_compliance",
    "PRE": "employee_misconduct",
}

_ROLE_SENIORITY_MAP = {
    "Aligned Attorney": "senior",
    "2nd Chair": "junior",
    "Assigned Owner": "partner",
    "Intake Manager": "senior",
    "Vendor/Secondee": "junior",
}

def _infer_allegation(bu: str = "", prefix: str = "", summary: str = "", case_types: str = "") -> str:
    """Infer allegation type from available fields."""
    text = f"{bu} {prefix} {summary} {case_types}".lower()
    if "harassment" in text or "wit" in text.split() or prefix == "WIT":
        return "harassment"
    if "discriminat" in text:
        return "employment_discrimination"
    if "privacy" in text or "breach" in text or "gdpr" in text or "data" in text:
        return "data_privacy"
    if "retaliat" in text or "whistleblow" in text:
        return "retaliation"
    if "ip" in text or "patent" in text or "trade secret" in text or "copyright" in text:
        return "intellectual_property"
    if "contract" in text or "vendor" in text or "sla violation" in text:
        return "contract_dispute"
    if "fraud" in text or "theft" in text or "misconduct" in text or "pre" in text.split():
        return "employee_misconduct"
    if "regulatory" in text or "compliance" in text or "securities" in text or "bri" in text.split():
        return "regulatory_compliance"
    return "employee_misconduct"

def _severity_from_fields(priority_code, is_escalated, is_urgent, is_high_priority, complexity: str) -> int:
    """Compute severity 1-5 from incident fields."""
    sev = 3  # default Normal
    try:
        pc = int(priority_code) if priority_code else 2
        if pc == 1:
            sev = 5  # High → Critical
        elif pc == 2:
            sev = 3  # Normal
        elif pc == 3:
            sev = 2  # Low
    except (ValueError, TypeError):
        pass

    if str(is_escalated).strip().lower() in ("true", "yes", "1"):
        sev = min(sev + 1, 5)
    if str(is_urgent).strip().lower() in ("true", "yes", "1"):
        sev = max(sev, 4)
    if str(is_high_priority).strip().lower() in ("true", "yes", "1"):
        sev = max(sev, 4)
    if "most complex" in str(complexity).lower():
        sev = max(sev, 4)
    elif "complex" in str(complexity).lower():
        sev = max(sev, 3)
    return sev

def _sla_flag(severity: int) -> str:
    flags = {5: "CRITICAL", 4: "URGENT", 3: "HIGH", 2: "STANDARD", 1: "LOW"}
    return flags.get(severity, "STANDARD")

def _priority_score(severity: int, sla_flag: str, is_escalated: bool) -> float:
    base = severity * 15.0
    if sla_flag == "CRITICAL":
        base += 25
    elif sla_flag == "URGENT":
        base += 15
    elif sla_flag == "HIGH":
        base += 5
    if is_escalated:
        base += 10
    return min(base, 100.0)

def _safe_str(val) -> str:
    return "" if (val is None or str(val).strip() in ("nan", "NaT", "None")) else str(val).strip()

def _safe_dt(val) -> str:
    if val is None:
        return datetime.now().isoformat()
    s = str(val).strip()
    if s in ("nan", "NaT", "None", ""):
        return datetime.now().isoformat()
    return s

# ─── Step 1: Load Attorneys ───────────────────────────────────────────────────────

def _load_attorneys_from_xlsx() -> Dict[str, Attorney]:
    logger.info("[STEP 1] Loading attorneys from xlsx files...")
    attorneys: Dict[str, Attorney] = {}
    seen_names: set = set()

    # --- ucm_attorney.xlsx ---
    df_att = _try_read_xlsx("attorney")
    if df_att is not None:
        for i, row in df_att.iterrows():
            name = _safe_str(row.get("ucm_selectapersonname") or row.get("ucm_name"))
            if not name or name in seen_names or name == "ucm_attorney":
                continue
            seen_names.add(name)
            att_id = f"ATT{len(attorneys)+1:03d}"
            bu = _safe_str(row.get("owningbusinessunitname", ""))
            seniority = "senior" if "partner" in bu.lower() or "root" not in bu.lower() else "junior"
            specializations = _get_specializations_for_bu(bu)
            att = Attorney(
                id=att_id,
                name=name,
                specializations=specializations,
                active_cases=0,
                max_cases=15,
                seniority=seniority,
                availability="available" if _safe_str(row.get("statecodename")) == "Active" else "busy",
                bar_state=["CA", "WA"],
                business_unit=bu,
                source="ucm_attorney.xlsx",
            )
            attorneys[att_id] = att
            logger.info("    [ATT] %s — %s (%s)", att_id, name, bu)

    # --- ucm_caseinvestigationteam.xlsx (additional people) ---
    df_team = _try_read_xlsx("investigation_team")
    if df_team is not None:
        for i, row in df_team.iterrows():
            name = _safe_str(row.get("ucm_systemusername"))
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            att_id = f"ATT{len(attorneys)+1:03d}"
            role = _safe_str(row.get("ucm_rolelawfirmname")).strip("​").strip()
            bu = _safe_str(row.get("owningbusinessunitname", ""))
            seniority = _ROLE_SENIORITY_MAP.get(role, "senior")
            specializations = _get_specializations_for_bu(bu)
            att = Attorney(
                id=att_id,
                name=name,
                specializations=specializations,
                active_cases=0,
                max_cases=12,
                seniority=seniority,
                availability="available",
                bar_state=["CA", "TX"],
                business_unit=bu,
                source="ucm_caseinvestigationteam.xlsx",
            )
            attorneys[att_id] = att
            logger.info("    [ATT] %s — %s (role: %s)", att_id, name, role)

    # --- ucm_externalinvestigator.xlsx ---
    df_ext = _try_read_xlsx("ext_investigator")
    if df_ext is not None:
        for i, row in df_ext.iterrows():
            name = _safe_str(row.get("ucm_name"))
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            att_id = f"ATT{len(attorneys)+1:03d}"
            att = Attorney(
                id=att_id,
                name=name,
                specializations=["employee_misconduct", "regulatory_compliance"],
                active_cases=0,
                max_cases=10,
                seniority="junior",
                availability="available",
                bar_state=["NY", "TX"],
                business_unit="External",
                source="ucm_externalinvestigator.xlsx",
            )
            attorneys[att_id] = att
            logger.info("    [ATT] %s — %s (external investigator)", att_id, name)

    logger.info("[STEP 1] Total attorneys loaded: %d", len(attorneys))
    return attorneys

def _get_specializations_for_bu(bu: str) -> List[str]:
    bu_lower = bu.lower()
    if "business and regulatory" in bu_lower or "bri" in bu_lower:
        return ["regulatory_compliance", "contract_dispute", "financial_fraud"]
    if "workplace investigation" in bu_lower or "wit" in bu_lower:
        return ["harassment", "employment_discrimination", "retaliation", "employee_misconduct"]
    if "digital markets" in bu_lower:
        return ["regulatory_compliance", "data_privacy", "intellectual_property"]
    return ["employee_misconduct", "regulatory_compliance"]

# ─── Step 2: Load Cases ───────────────────────────────────────────────────────────

def _load_cases_from_xlsx() -> List[CaseRecord]:
    logger.info("[STEP 2] Loading cases from xlsx files...")
    cases: List[CaseRecord] = []
    seen_case_ids: set = set()

    # --- incident.xlsx (multiple rows, normal layout) ---
    df_inc = _try_read_xlsx("incident")
    if df_inc is not None:
        logger.info("  [STEP 2a] Parsing %d rows from incident.xlsx...", len(df_inc))
        for i, row in df_inc.iterrows():
            case_id = _safe_str(row.get("title") or row.get("ticketnumber"))
            ticket_num = _safe_str(row.get("ticketnumber"))
            if not case_id or case_id in seen_case_ids:
                continue
            seen_case_ids.add(case_id)

            bu = _safe_str(row.get("owningbusinessunitname", ""))
            prefix = case_id.split("-")[0] if "-" in case_id else ""
            summary = _safe_str(row.get("ucm_summaryofallegation") or row.get("ucm_summaryofallegations") or "")
            case_types = _safe_str(row.get("ucm_casetypesname", ""))
            allegation = _infer_allegation(bu, prefix, summary, case_types)

            sev = _severity_from_fields(
                row.get("prioritycode"),
                row.get("isescalated"),
                row.get("ucm_urgent"),
                row.get("ucm_highpriority"),
                _safe_str(row.get("ucm_casecomplexity", "")),
            )
            sla = _sla_flag(sev)
            is_escalated = str(row.get("isescalated", "")).lower() in ("true", "yes", "1")
            score = _priority_score(sev, sla, is_escalated)

            complainant = _safe_str(
                row.get("ucm_complainant")
                or f"{row.get('ucm_firstname', '')} {row.get('ucm_lastname', '')}".strip()
                or row.get("customeridname", "Unknown")
            )
            respondent = _safe_str(row.get("owningbusinessunitname") or "Unknown Department")

            assigned = _safe_str(row.get("ucm_briassignedattorneyname") or row.get("ucm_assignedwitinvestigator", ""))
            if assigned in ("Not Assigned", "nan", ""):
                assigned = None

            case = CaseRecord(
                case_id=case_id,
                allegation_type=allegation,
                severity=sev,
                parties={"complainant": complainant, "respondent": respondent},
                assigned_attorney=assigned,
                status=_safe_str(row.get("pam_casestatusname", "Intake")),
                submitted_at=_safe_dt(row.get("createdon")),
                priority_score=score,
                queue_position=len(cases),
                sla_flag=sla,
                ticket_number=ticket_num,
                business_unit=bu,
                complexity=_safe_str(row.get("ucm_casecomplexity", "")),
                summary=summary[:300] if summary else "",
                team_prefix=prefix,
                source_file="incident.xlsx",
            )
            cases.append(case)
            logger.info(
                "    [CASE] %s | %s | severity=%d | sla=%s | score=%.0f",
                case_id, allegation, sev, sla, score,
            )

    # --- incident_BRI-26-11626.xlsx (transposed single-record) ---
    logger.info("  [STEP 2b] Parsing incident_BRI-26-11626.xlsx (transposed)...")
    bri_data = _try_read_bri_transposed("incident_bri")
    if bri_data:
        case_id = _safe_str(bri_data.get("ucm_casenumber") or bri_data.get("title") or bri_data.get("ticketnumber"))
        ticket_num = _safe_str(bri_data.get("ticketnumber"))
        if case_id and case_id not in seen_case_ids:
            seen_case_ids.add(case_id)
            bu = _safe_str(bri_data.get("owningbusinessunitname", ""))
            prefix = _safe_str(bri_data.get("ucm_teamprefixname", case_id.split("-")[0] if "-" in case_id else ""))
            summary = _safe_str(bri_data.get("ucm_summaryofallegation") or bri_data.get("ucm_summaryofallegations") or "")
            case_types = _safe_str(bri_data.get("ucm_casetypesname", ""))
            allegation = _infer_allegation(bu, prefix, summary, case_types)

            sev = _severity_from_fields(
                bri_data.get("prioritycode"),
                bri_data.get("isescalated"),
                bri_data.get("ucm_urgent"),
                bri_data.get("ucm_highpriority"),
                _safe_str(bri_data.get("ucm_casecomplexity", "")),
            )
            sla = _sla_flag(sev)
            is_escalated = str(bri_data.get("isescalated", "")).lower() in ("true", "yes", "1")
            score = _priority_score(sev, sla, is_escalated)

            complainant = _safe_str(
                bri_data.get("ucm_complainant")
                or f"{bri_data.get('ucm_firstname', '')} {bri_data.get('ucm_lastname', '')}".strip()
            ) or "Unknown"
            respondent = bu or "Unknown Department"

            assigned = _safe_str(bri_data.get("ucm_briassignedattorneyname", ""))
            if assigned in ("Not Assigned", "nan", ""):
                assigned = None

            case = CaseRecord(
                case_id=case_id,
                allegation_type=allegation,
                severity=sev,
                parties={"complainant": complainant, "respondent": respondent},
                assigned_attorney=assigned,
                status=_safe_str(bri_data.get("pam_casestatusname", "Intake")),
                submitted_at=_safe_dt(bri_data.get("createdon")),
                priority_score=score,
                queue_position=len(cases),
                sla_flag=sla,
                ticket_number=ticket_num,
                business_unit=bu,
                complexity=_safe_str(bri_data.get("ucm_casecomplexity", "")),
                summary=summary[:300] if summary else "",
                team_prefix=prefix,
                source_file="incident_BRI-26-11626.xlsx",
            )
            cases.append(case)
            logger.info(
                "    [CASE] %s | %s | severity=%d | sla=%s | score=%.0f | complexity=%s",
                case_id, allegation, sev, sla, score, case.complexity,
            )

    # Re-sort by priority score descending and re-assign queue positions
    cases.sort(key=lambda c: -c.priority_score)
    for idx, c in enumerate(cases):
        c.queue_position = idx

    logger.info("[STEP 2] Total cases loaded: %d", len(cases))
    return cases

# ─── Step 3: Load Data Sources ────────────────────────────────────────────────────

def _load_datasources_from_xlsx() -> List[dict]:
    logger.info("[STEP 3] Loading data sources from ucm_datasource.xlsx...")
    sources = []
    df = _try_read_xlsx("datasource")
    if df is not None:
        for _, row in df.iterrows():
            name = _safe_str(row.get("ucm_name"))
            detail = _safe_str(row.get("ucm_sourcedetails"))
            if name:
                sources.append({"name": name, "detail": detail})
                logger.info("    [SRC] %s — %s", name, detail[:80])
    logger.info("[STEP 4] Data sources loaded: %d", len(sources))
    return sources

# ─── Step 4: Attorney Workload Update ────────────────────────────────────────────

def _update_attorney_workloads(attorneys: Dict[str, Attorney], cases: List[CaseRecord]):
    logger.info("[STEP 5] Updating attorney workloads from case assignments...")
    counts: Dict[str, int] = {}
    for case in cases:
        if case.assigned_attorney:
            counts[case.assigned_attorney] = counts.get(case.assigned_attorney, 0) + 1

    for att in attorneys.values():
        # Match by name
        att.active_cases = counts.get(att.name, att.active_cases)
        capacity_pct = att.active_cases / att.max_cases
        if capacity_pct >= 0.95:
            att.availability = "busy"
        elif capacity_pct >= 0.75:
            att.availability = "available"
        logger.info(
            "    [WRK] %s — %d/%d cases (%s)",
            att.name, att.active_cases, att.max_cases, att.availability,
        )

# ─── Step 5: Build Default Fallbacks ─────────────────────────────────────────────

def _default_attorneys() -> Dict[str, Attorney]:
    logger.info("[FALLBACK] Using built-in attorney defaults")
    return {
        "ATT001": Attorney("ATT001", "Annapureddy Ashok Reddy",
                           ["regulatory_compliance", "employee_misconduct", "contract_dispute"],
                           8, 15, "senior", "available", ["CA", "WA", "TX"],
                           "Business and Regulatory Investigations", "default"),
        "ATT002": Attorney("ATT002", "Alekhya Priyanka A",
                           ["regulatory_compliance", "data_privacy", "intellectual_property"],
                           10, 15, "senior", "available", ["CA", "NY"],
                           "Business and Regulatory Investigations", "default"),
        "ATT003": Attorney("ATT003", "Swapnil Mishra",
                           ["harassment", "employment_discrimination", "retaliation"],
                           5, 12, "senior", "available", ["CA", "WA"],
                           "Workplace Investigation Team", "default"),
        "ATT004": Attorney("ATT004", "Cantrell Jones",
                           ["employee_misconduct", "regulatory_compliance"],
                           3, 10, "junior", "available", ["NY", "TX"],
                           "External", "default"),
        "ATT005": Attorney("ATT005", "Temi Anderson",
                           ["harassment", "employment_discrimination"],
                           2, 10, "junior", "available", ["CA", "IL"],
                           "External", "default"),
        "ATT006": Attorney("ATT006", "Bernice Blessing",
                           ["regulatory_compliance", "contract_dispute"],
                           4, 10, "junior", "available", ["WA", "OR"],
                           "External", "default"),
    }

def _default_cases() -> List[CaseRecord]:
    logger.info("[FALLBACK] Using built-in case defaults")
    return [
        CaseRecord("WIT-24-07158", "harassment", 3,
                   {"complainant": "Employee A", "respondent": "Workplace Investigation Team"},
                   None, "Intake", "2024-05-09T11:45:40", 50.0, 0, "HIGH",
                   "CAS-07789-K1B8J9", "Workplace Investigation Team", "", "", "WIT", "incident.xlsx"),
        CaseRecord("WIT-24-07161", "harassment", 3,
                   {"complainant": "Employee B", "respondent": "Workplace Investigation Team"},
                   None, "Intake", "2024-05-09T13:05:19", 50.0, 1, "HIGH",
                   "CAS-07792-B2K9L3", "Workplace Investigation Team", "", "", "WIT", "incident.xlsx"),
        CaseRecord("BRI-26-11626", "regulatory_compliance", 3,
                   {"complainant": "Ashish-test-witness Pandey", "respondent": "Business and Regulatory Investigations"},
                   None, "Intake", "2026-03-20T09:07:51", 50.0, 2, "HIGH",
                   "CAS-12516-Q4Y9S9", "Business and Regulatory Investigations",
                   "Most Complex", "A test data for Allegation summary...", "BRI",
                   "incident_BRI-26-11626.xlsx"),
    ]

# ─── Main Initialization ──────────────────────────────────────────────────────────

logger.info("=" * 70)
logger.info("UC-04 Investigation Plan — Data initialization starting")
logger.info("Base directory: %s", BASE_DIR)

# Check available xlsx files
logger.info("[STEP 0] Scanning for xlsx files in %s...", BASE_DIR)
available_files = []
for key, fname in XLSX_FILES.items():
    fpath = os.path.join(BASE_DIR, fname)
    exists = os.path.exists(fpath)
    status = "FOUND" if exists else "MISSING"
    logger.info("  [%s] %s", status, fname)
    if exists:
        available_files.append(fname)

# All xlsx files found on disk — exported so the UI can display them all
LOADED_FILES: List[dict] = [
    {"file": fname, "key": key}
    for key, fname in XLSX_FILES.items()
    if os.path.exists(os.path.join(BASE_DIR, fname))
]

xlsx_available = len(available_files) > 0

if xlsx_available:
    ATTORNEYS = _load_attorneys_from_xlsx()
    if not ATTORNEYS:
        logger.warning("[WARN] No attorneys loaded from xlsx — using defaults")
        ATTORNEYS = _default_attorneys()

    EXISTING_CASES = _load_cases_from_xlsx()
    if not EXISTING_CASES:
        logger.warning("[WARN] No cases loaded from xlsx — using defaults")
        EXISTING_CASES = _default_cases()

    DATA_SOURCES = _load_datasources_from_xlsx()
    _update_attorney_workloads(ATTORNEYS, EXISTING_CASES)
else:
    logger.warning("[WARN] No xlsx files found — using built-in defaults")
    ATTORNEYS = _default_attorneys()
    EXISTING_CASES = _default_cases()
    DATA_SOURCES = []

# ─── Knowledge Base (authoritative — not in xlsx) ────────────────────────────────

logger.info("[STEP 6] Loading knowledge base articles (built-in)...")

KNOWLEDGE_BASE: List[KBArticle] = [
    KBArticle("KB-001", "harassment",
              ["sexual harassment", "hostile environment", "unwanted advances", "inappropriate conduct", "harassment"],
              ["incident_report", "witness_statements", "communication_logs", "hr_records"],
              "3-5", "Immediate interim measures may be required. Preserve all digital communications.",
              ["UCM-2023-045", "UCM-2023-112", "UCM-2022-089"]),
    KBArticle("KB-002", "employment_discrimination",
              ["racial discrimination", "gender discrimination", "age discrimination", "disability", "promotion denial", "discrimination"],
              ["employment_records", "performance_reviews", "comparator_data", "hr_communications"],
              "2-4", "Gather statistical data on comparable employees. Check EEOC timelines.",
              ["UCM-2023-078", "UCM-2023-201"]),
    KBArticle("KB-003", "data_privacy",
              ["data breach", "GDPR violation", "unauthorized access", "personal data", "privacy", "data leak"],
              ["security_incident_report", "affected_user_list", "system_logs", "dpa_notification"],
              "4-5", "Notify DPA within 72 hours if EU data involved. Engage cybersecurity team immediately.",
              ["UCM-2023-156", "UCM-2022-234"]),
    KBArticle("KB-004", "retaliation",
              ["retaliation", "whistleblower", "adverse action", "demotion", "termination after complaint"],
              ["original_complaint_reference", "timeline_of_events", "employment_changes", "communications"],
              "3-5", "Link to original protected activity. Strong legal protections apply under SOX/Dodd-Frank.",
              ["UCM-2023-092", "UCM-2023-167"]),
    KBArticle("KB-005", "intellectual_property",
              ["patent infringement", "trade secret", "copyright", "IP theft", "confidential information misuse"],
              ["ip_registration_docs", "evidence_of_infringement", "nda_agreements", "technical_analysis"],
              "3-4", "Seek preliminary injunction if ongoing infringement. Engage IP counsel.",
              ["UCM-2023-203", "UCM-2022-178"]),
    KBArticle("KB-006", "contract_dispute",
              ["breach of contract", "vendor dispute", "SLA violation", "non-payment", "contract terms"],
              ["original_contract", "breach_evidence", "correspondence", "financial_records"],
              "1-3", "Review liquidated damages clauses. Check arbitration requirements.",
              ["UCM-2023-034", "UCM-2022-089"]),
    KBArticle("KB-007", "employee_misconduct",
              ["theft", "fraud", "policy violation", "code of conduct", "integrity violation"],
              ["investigation_report", "evidence_documentation", "witness_interviews", "policy_docs"],
              "2-5", "Preserve chain of custody for all evidence. HR must be involved from start.",
              ["UCM-2023-145", "UCM-2023-198"]),
    KBArticle("KB-008", "regulatory_compliance",
              ["regulatory violation", "compliance failure", "securities violation", "financial reporting",
               "audit finding", "digital markets act", "business regulatory"],
              ["regulatory_notice", "compliance_records", "audit_reports", "remediation_plan"],
              "3-5", "Notify board audit committee. Engage external compliance counsel if SEC involved.",
              ["UCM-2023-067", "UCM-2022-145"]),
]

for kb in KNOWLEDGE_BASE:
    logger.info("  [KB]  %s — %s", kb.article_id, kb.allegation_category)

# ─── SLA Rules ────────────────────────────────────────────────────────────────────

SLA_RULES = {
    5: {"flag": "CRITICAL", "response_hours": 2,   "resolution_days": 7},
    4: {"flag": "URGENT",   "response_hours": 24,  "resolution_days": 30},
    3: {"flag": "HIGH",     "response_hours": 48,  "resolution_days": 60},
    2: {"flag": "STANDARD", "response_hours": 72,  "resolution_days": 90},
    1: {"flag": "LOW",      "response_hours": 120, "resolution_days": 180},
}

# ─── Allegation Type Taxonomy ─────────────────────────────────────────────────────

ALLEGATION_TAXONOMY = {
    "harassment": {
        "subtypes": ["sexual_harassment", "workplace_harassment", "cyber_harassment"],
        "base_severity": 4, "auto_escalate": True,
    },
    "employment_discrimination": {
        "subtypes": ["racial", "gender", "age", "disability", "religious"],
        "base_severity": 3, "auto_escalate": False,
    },
    "data_privacy": {
        "subtypes": ["data_breach", "gdpr_violation", "unauthorized_access", "data_retention"],
        "base_severity": 4, "auto_escalate": True,
    },
    "retaliation": {
        "subtypes": ["whistleblower", "protected_activity", "adverse_employment_action"],
        "base_severity": 4, "auto_escalate": True,
    },
    "intellectual_property": {
        "subtypes": ["patent", "copyright", "trade_secret", "trademark"],
        "base_severity": 3, "auto_escalate": False,
    },
    "contract_dispute": {
        "subtypes": ["breach", "non_payment", "sla_violation", "vendor_dispute"],
        "base_severity": 2, "auto_escalate": False,
    },
    "employee_misconduct": {
        "subtypes": ["fraud", "theft", "policy_violation", "integrity_breach"],
        "base_severity": 3, "auto_escalate": False,
    },
    "regulatory_compliance": {
        "subtypes": ["securities", "financial_reporting", "environmental", "safety", "digital_markets"],
        "base_severity": 4, "auto_escalate": True,
    },
}

logger.info("[DONE] Data initialization complete — %d attorneys, %d cases, %d KB articles",
            len(ATTORNEYS), len(EXISTING_CASES), len(KNOWLEDGE_BASE))
logger.info("=" * 70)

# ─── Helper Functions ──────────────────────────────────────────────────────────────

def get_all_cases_summary() -> str:
    """Return a formatted summary of all cases in the queue."""
    lines = ["=== CURRENT CASE QUEUE (UCM) ===\n"]
    for case in sorted(EXISTING_CASES, key=lambda c: c.queue_position):
        atty_id = case.assigned_attorney
        atty_name = "Unassigned"
        if atty_id:
            matched = next((a for a in ATTORNEYS.values() if a.name == atty_id or a.id == atty_id), None)
            atty_name = matched.name if matched else atty_id
        lines.append(
            f"[{case.sla_flag}] {case.case_id} | {case.allegation_type.upper()} | "
            f"Severity: {case.severity}/5 | Queue#{case.queue_position} | "
            f"Attorney: {atty_name} | Status: {case.status} | BU: {case.business_unit}"
        )
    return "\n".join(lines)

def get_attorney_workload_summary() -> str:
    """Return formatted attorney workload."""
    lines = ["=== ATTORNEY WORKLOAD (UCM Dataverse) ===\n"]
    for atty in ATTORNEYS.values():
        load_pct = (atty.active_cases / atty.max_cases) * 100
        load_bar = "█" * int(load_pct / 10) + "░" * (10 - int(load_pct / 10))
        lines.append(
            f"{atty.name:30} | {atty.seniority:8} | [{load_bar}] {load_pct:.0f}% "
            f"({atty.active_cases}/{atty.max_cases}) | {atty.availability} | {atty.business_unit}"
        )
    return "\n".join(lines)

def get_next_queue_position() -> int:
    """Get the next available queue position."""
    if not EXISTING_CASES:
        return 1
    return max(c.queue_position for c in EXISTING_CASES) + 1

def find_duplicate(parties: Dict, allegation_type: str) -> Optional[str]:
    """Simple duplicate check based on parties and allegation type."""
    for case in EXISTING_CASES:
        if (case.allegation_type == allegation_type
                and any(p in case.parties.values() for p in parties.values())):
            return case.case_id
    return None

def get_data_load_summary() -> str:
    """Return a summary of what data was loaded and from where."""
    lines = ["=== DATA LOAD SUMMARY ===\n"]
    lines.append(f"Base directory : {BASE_DIR}")
    lines.append(f"Attorneys      : {len(ATTORNEYS)} loaded")
    lines.append(f"Cases          : {len(EXISTING_CASES)} loaded")
    lines.append(f"KB Articles    : {len(KNOWLEDGE_BASE)} built-in")
    lines.append(f"Data Sources   : {len(DATA_SOURCES)}")
    lines.append("\nSource breakdown:")
    sources = {}
    for c in EXISTING_CASES:
        sources[c.source_file] = sources.get(c.source_file, 0) + 1
    for src, cnt in sources.items():
        lines.append(f"  {src:40} → {cnt} cases")
    att_sources = {}
    for a in ATTORNEYS.values():
        att_sources[a.source] = att_sources.get(a.source, 0) + 1
    for src, cnt in att_sources.items():
        lines.append(f"  {src:40} → {cnt} attorneys")
    return "\n".join(lines)
