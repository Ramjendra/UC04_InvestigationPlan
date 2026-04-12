"""
UC-04 Investigation Plan — Enterprise Frontend (VerseAPI & Azure Directory)
Mocked for demonstration.
"""

import streamlit as st
import asyncio
import json
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.insert(0, os.path.dirname(__file__))

# Re-use the same logger/file as triage_agent
from plan_agent import setup_logging
log = setup_logging()
log = logging.getLogger("uc04.app")

from simulated_data import (
    ATTORNEYS, EXISTING_CASES, KNOWLEDGE_BASE,
    ALLEGATION_TAXONOMY, SLA_RULES,
    DATA_SOURCES, LOADED_FILES, get_data_load_summary,
)
# Enterprise endpoints (Mocks)
VERSE_API_ENDPOINT = "https://cela.crm.dynamics.com/api/data/v9.2"
AZURE_AI_SEARCH    = "https://cela-search.search.windows.net"

# ── Page Config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="UC-04 Investigation Plan Assistant",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS ────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* Global Dynamics 365 Theme - Exact Match */
[data-testid="stAppViewContainer"] { background: #ffffff; }
[data-testid="stHeader"] { background: #ffffff; border-bottom: 1px solid #edebe9; height: 48px; }
[data-testid="stSidebar"] { background: #212121; border-right: none; color: #ffffff; width: 200px !important; }
h1,h2,h3,h4 { color: #323130 !important; font-family: 'Segoe UI', sans-serif; }

/* Sidebar icons and text */
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { 
    color: #ffffff !important; 
    font-size: 12px !important; 
    margin-bottom: 0px; 
    padding: 8px 15px;
    cursor: pointer;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p:hover { background: #333333; }
.sidebar-header { color: #8a8886 !important; font-size: 10px !important; font-weight: 600; padding: 15px 15px 5px 15px; text-transform: uppercase; }

/* Dynamics Top Ribbon */
.ucm-ribbon {
    background: #ffffff;
    border-bottom: 1px solid #edebe9;
    padding: 8px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 12px;
}
.ucm-ribbon-title { font-weight: 600; color: #000; font-size: 16px; margin-bottom: 4px; }
.ucm-ribbon-sub { font-size: 11px; color: #605e5c; }
.ucm-actions-bar {
    background: #ffffff;
    border-bottom: 1px solid #edebe9;
    padding: 5px 20px;
    display: flex;
    gap: 20px;
    font-size: 12px;
    color: #444;
}
.ucm-action-item { display: flex; align-items: center; gap: 5px; cursor: pointer; }
.ucm-action-item:hover { color: #005a9e; }

/* Business Process Flow (BPF) - Green Circles style */
.bpf-container {
    background: #ffffff;
    border-bottom: 1px solid #edebe9;
    padding: 15px 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 40px;
    position: relative;
}
.bpf-line {
    position: absolute;
    top: 50%;
    left: 100px;
    right: 100px;
    height: 1px;
    background: #edebe9;
    z-index: 1;
}
.bpf-circle {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: #ffffff;
    border: 1px solid #edebe9;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    color: #605e5c;
    z-index: 2;
    position: relative;
}
.bpf-circle-done { border-color: #107c10; color: #107c10; }
.bpf-circle-active { border: 2px solid #107c10; color: #107c10; background: #ffffff; box-shadow: 0 0 0 4px #dff6dd; }
.bpf-label { font-size: 10px; color: #605e5c; position: absolute; top: 30px; white-space: nowrap; }

/* Tabs - Full Set */
.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
    background-color: #ffffff;
    padding-left: 20px;
    border-bottom: 1px solid #edebe9;
}
.stTabs [data-baseweb="tab"] {
    height: 36px;
    background-color: transparent !important;
    border: none !important;
    color: #605e5c !important;
    font-size: 12px !important;
    padding: 0 10px !important;
}

/* Dynamics Table Styling */
.ucm-table-header { background: #f3f2f1; padding: 10px; font-weight: 600; font-size: 11px; color: #323130; border-bottom: 1px solid #edebe9; }
.ucm-table-row { padding: 10px; border-bottom: 1px solid #f3f2f1; font-size: 11px; }

/* Assistant Bubble */
.floating-assistant {
    position: fixed;
    bottom: 30px;
    right: 30px;
    width: 40px;
    height: 40px;
    background: #ffffff;
    border: 1px solid #edebe9;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #005a9e !important;
    font-size: 18px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

SEV_COLORS = {5:"#ef4444", 4:"#f97316", 3:"#eab308", 2:"#3b82f6", 1:"#22c55e"}
SEV_LABELS = {5:"CRITICAL",4:"URGENT",3:"HIGH",2:"STANDARD",1:"LOW"}

def sev_color(s): return SEV_COLORS.get(s,"#718096")

def load_bar(pct, color):
    return f"""<div class="load-bar-bg">
<div class="load-bar-fg" style="width:{pct}%;background:{color}"></div></div>"""

def load_color(pct):
    if pct >= 90: return "#ef4444"
    if pct >= 70: return "#f97316"
    if pct >= 50: return "#eab308"
    return "#22c55e"

def get_atty_name(atty_ref):
    """Resolve attorney name from ID or direct name string."""
    if not atty_ref:
        return "Unassigned"
    # Try ATT-ID lookup first (backward compat)
    a = ATTORNEYS.get(atty_ref)
    if a:
        return a.name
    # Check if it matches any attorney by name
    for att in ATTORNEYS.values():
        if att.name == atty_ref:
            return att.name
    return atty_ref  # already a name string


# ── Session State ──────────────────────────────────────────────────────────────

if "messages"        not in st.session_state: st.session_state.messages = []
if "triage_log"      not in st.session_state: st.session_state.triage_log = []
if "last_triage"     not in st.session_state: st.session_state.last_triage = None
if "pipeline_steps"  not in st.session_state: st.session_state.pipeline_steps = []
if "page"           not in st.session_state: st.session_state.page = "📊 Dashboard"
if "show_assistant" not in st.session_state: st.session_state.show_assistant = False
if "assistant_messages" not in st.session_state: st.session_state.assistant_messages = [
    {"role": "assistant", "content": "How can I help you with your investigation plan today?"}
]

# Sync fields for Investigation Plan
if "bci_synopsis" not in st.session_state:
    st.session_state.bci_synopsis = "This investigation concerns alleged harassment incidents occurring between Q3 and Q4 2025. Preliminary evidence from NAVEX intake suggests a pattern of behavior involving Target A and multiple witnesses in the EMEA region. All relevant email logs and Teams chat history have been indexed via VerseAPI for context retrieval."
if "bci_exec" not in st.session_state:
    st.session_state.bci_exec = "The investigation is currently in the Triage phase. High-priority witnesses have been identified. AI Copilot has drafted initial interview protocols and cross-referenced 2 precedent cases with similar fact patterns."
if "last_sync_time" not in st.session_state:
    st.session_state.last_sync_time = None



# ── Triage Runner (sync wrapper) ───────────────────────────────────────────────

PIPELINE_STEPS = [
    ("identify_investigation_stages",    "📌 Identify Stages",       "VerseAPI (CILA)"),
    ("suggest_interview_questions",     "❓ Interview Questions",    "Azure OpenAI (AD)"),
    ("identify_required_documents",     "📄 Required Documents",     "VerseAPI Index"),
    ("link_precedent_cases",            "🔗 Precedent Cases",        "Azure AI Search"),
    ("assign_investigation_tasks",      "📅 Investigation Tasks",    "VerseAPI Board"),
    ("generate_plan_summary",           "📝 Plan Summary",           "Azure OpenAI"),
    ("write_plan_to_ucm",               "💾 Write to Dataverse",     "VerseAPI"),
]

PLANNING_SYSTEM = """You are the CELA Investigation Planning Assistant (UC-04).
Utilizing VerseAPI and Azure Directory to generate a comprehensive plan."""

async def _run_planning_async(case_input: dict, step_callback):
    # Now calls our enterprise-mocked agent instead of Ollama
    from plan_agent import run_plan_agent
    return await run_plan_agent(case_input, step_callback=step_callback)

def run_planning_sync(case_input: dict, step_callback):
    return asyncio.run(_run_planning_async(case_input, step_callback))


# ── Chatbot ────────────────────────────────────────────────────────────────────

CHAT_SYSTEM = """You are the UC-04 Investigation Planning Assistant for CELA.
Answer questions about investigation plans, stages, interview questions, and required evidence.
Be concise and professional. Reference actual case IDs and attorney names.

CURRENT DATA:
{context}"""

def build_context():
    cases = "\n".join([
        f"  [{c.sla_flag}] {c.case_id} ({c.ticket_number}) | {c.allegation_type} | Sev {c.severity} | "
        f"#{c.queue_position} | {get_atty_name(c.assigned_attorney)} | {c.status} | {c.business_unit}"
        + (f" | Complexity: {c.complexity}" if c.complexity else "")
        + (f" | {c.summary[:80]}" if c.summary else "")
        for c in sorted(EXISTING_CASES, key=lambda x: x.queue_position)
    ])
    attorneys = "\n".join([
        f"  {a.name} ({a.seniority}) {a.active_cases}/{a.max_cases} [{a.availability}]"
        f" — {','.join(a.specializations[:2])} | {a.business_unit}"
        for a in ATTORNEYS.values()
    ])
    sources = "\n".join([f"  {s['name']}: {s['detail']}" for s in DATA_SOURCES])
    return f"CASES:\n{cases}\n\nATTORNEYS:\n{attorneys}\n\nDATA SOURCES:\n{sources}"

async def chat_stream(user_msg: str, mode="general"):
    # Mocking the assistant response without Ollama
    if mode == "assistant":
        responses = [
            "I'm analyzing the case details in VerseAPI. What specifically are you looking for?",
            "You can find required documents under the 'Evidence Matrix' section of the plan.",
            "Azure Directory is currently indexing the precedent cases for this allegation type.",
        ]
    else:
        responses = [
            "I'm the UC-04 Investigation Assistant. How can I help you with VerseAPI or Azure Directory today?",
            "That's a great question about the investigation process. Our VerseAPI integration handles that.",
            "You can find precedent cases via the Azure AI Search tool in the Plan Generator.",
        ]
    import random
    reply = random.choice(responses)
    for char in reply:
        yield char
        await asyncio.sleep(0.01)


# ═══════════════════════════════════════════════════════════════════
# LAYOUT & NAVIGATION
# ═══════════════════════════════════════════════════════════════════

# ── Sidebar (Exact UCM Match) ───────────────────────────────────
with st.sidebar:
    st.markdown("Dynamics 365")
    st.markdown("---")
    
    st.markdown("Home")
    st.markdown("Recent")
    st.markdown("Pinned")
    
    st.markdown('<div class="sidebar-header">Case Management</div>', unsafe_allow_html=True)
    st.markdown("Home Dashboard")
    st.markdown("Cases")
    st.markdown("Contact Search")
    st.markdown("Revoke Access")
    
    st.markdown('<div class="sidebar-header">Configurations</div>', unsafe_allow_html=True)
    st.markdown("Policies")
    
    st.markdown('<div class="sidebar-header">Other Tools</div>', unsafe_allow_html=True)
    st.markdown("PMO Link")
    
    st.markdown('<div class="sidebar-header">API Explorer</div>', unsafe_allow_html=True)
    st.markdown("[🚀 Chatbot API Docs](http://localhost:8000/docs)")
    st.markdown("[🧪 API Test UI](http://localhost:8080/api_test_ui.html)")

# ── Dynamic Layout Wrapper ──────────────────────────────────────────
if st.session_state.show_assistant:
    main_col, assistant_col = st.columns([0.75, 0.25])
else:
    main_col = st.container()
    assistant_col = None

with main_col:
    # ── Dynamics 365 Record Header ──────────────────────────────────
    st.markdown("""
<div style="padding: 15px 20px 5px 20px; background:white;">
    <div class="ucm-ribbon-sub">Case</div>
    <div class="ucm-ribbon-title">BRI-26-11514 : [Pending - NAVEX]</div>
</div>
""", unsafe_allow_html=True)

    # ── Ribbon Actions (Full Set from Image) ────────────────────────
    st.markdown("""
<div class="ucm-actions-bar">
    <div class="ucm-action-item">New</div>
    <div class="ucm-action-item">Refer</div>
    <div class="ucm-action-item">Spam</div>
    <div class="ucm-action-item">Generate ROI Document</div>
    <div class="ucm-action-item">Generate AI ROI</div>
    <div class="ucm-action-item">Invite Individual</div>
    <div class="ucm-action-item">Invite Team</div>
    <div class="ucm-action-item">Univista</div>
    <div class="ucm-action-item">Save</div>
    <div class="ucm-action-item">Save & Close</div>
    <div class="ucm-action-item">Resolve Case</div>
    <div class="ucm-action-item">Refresh</div>
    <div class="ucm-action-item">Word Templates</div>
</div>
""", unsafe_allow_html=True)

    # ── Business Process Flow (BPF) - Exact Styling ────────────────
    st.markdown(f"""
<div class="bpf-container">
    <div class="bpf-line"></div>
    <div class="bpf-circle bpf-circle-active"><div class="bpf-label" style="color:#107c10; font-weight:700">Intake (2 Hrs)</div></div>
    <div class="bpf-circle"><div class="bpf-label">Triage</div></div>
    <div class="bpf-circle"><div class="bpf-label">Investigation</div></div>
    <div class="bpf-circle"><div class="bpf-label">Reporting</div></div>
    <div class="bpf-circle"><div class="bpf-label">Closed</div></div>
</div>
""", unsafe_allow_html=True)

    # ── Full Tabs List (13 Tabs) ───────────────────────────────────
    tabs = st.tabs([
        "Profile", "Parties", "Case Relationship", "Investigation Plan", 
        "Documents", "Task Board", "Activity Log", "Evidence", 
        "Communication", "Report", "Close Out", "Admin Notes", "Related"
    ])

    with tabs[0]: # Profile
        st.markdown("### Profile")
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown("#### Case Queue (UCM)")
            for case in sorted(EXISTING_CASES, key=lambda x: x.queue_position):
                dot_color = sev_color(case.severity)
                st.markdown(f"""
<div class="case-row"><div class="sev-dot" style="background:{dot_color}"></div><div class="case-id">{case.case_id}</div><span class="badge badge-{case.sla_flag}">{case.sla_flag}</span><div class="case-type">{case.allegation_type.replace('_',' ').title()}</div><div style="color:#718096;font-size:12px">Sev {case.severity}/5</div><div class="case-atty">At: {get_atty_name(case.assigned_attorney)}</div></div>
""", unsafe_allow_html=True)

    with tabs[3]: # Investigation Plan
        st.markdown("### INVESTIGATION REPORT")
        
        # Cross-Process Sync Checker
        sync_file = "sync_data.json"
        if os.path.exists(sync_file):
            try:
                with open(sync_file, "r") as f:
                    sync_data = json.load(f)
                
                # If timestamp is new, notify user
                st.success(f"🤖 AI suggestion available (Synced at {sync_data.get('timestamp')})")
                if st.button("Apply Sycned AI Suggestion"):
                    # Update both the display variable and the component's internal state (key)
                    new_val = sync_data.get("summary", "")
                    st.session_state.bci_synopsis = new_val
                    st.session_state.last_sync_time = sync_data.get("timestamp")
                    
                    # Force update the widget keys if they exist
                    st.session_state["synopsis_area_live"] = new_val
                    
                    st.toast("Investigation Plan Updated!")
                    st.rerun()
            except:
                pass


        st.markdown("""
<div style="display:flex; justify-content:flex-end; gap:15px; font-size:11px; color:#605e5c; padding:8px 0; border-bottom:1px solid #edebe9;">
    <span>Refresh</span>
    <span>Export Documents</span>
    <span>See all records</span>
</div>
<div class="ucm-table-header" style="display:grid; grid-template-columns: 1.5fr 3fr 1fr 1fr;">
    <div>Name</div><div>AI Summary</div><div>Modified</div><div>Modified By</div>
</div>
""", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### BCI CASE SYNOPSIS")
        st.text_area("Synopsis Editor", st.session_state.bci_synopsis, height=120, label_visibility="collapsed", key="synopsis_area_live")
        
        st.markdown("### BCI EXECUTIVE SUMMARY")
        st.text_area("Exec Summary", st.session_state.bci_exec, height=100, label_visibility="collapsed", key="exec_area_live")

        
        if st.button("Run Copilot Investigation Planner", use_container_width=True):
            # ... pipeline logic remains same for real generation
            # No steps display, just result as requested
            case_input = {"case_id": "BRI-26-11514", "allegation_type": "Harassment", "severity": 4, "parties": ["Target A"], "summary": "Detailed case info."}
            with st.spinner("Copilot is analyzing VerseAPI & Generating Plan..."):
                report = run_planning_sync(case_input, lambda t,r: None)
                st.session_state.current_report = report
        
        if st.session_state.get("current_report"):
            st.markdown("#### Copilot Analysis Result")
            st.markdown(f'<div class="triage-result" style="background:#ffffff; border:1px solid #edebe9; color:#323130 !important">{st.session_state.current_report}</div>', unsafe_allow_html=True)

# ── Global Assistant Panel (Copilot Style) ─────────────────────────
if assistant_col:
    with assistant_col:
        st.markdown("""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
            <div style="background:#005a9e; width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center; color:white; font-weight:700;">C</div>
            <div style="font-weight:700; font-size:16px; color:#323130;">Copilot</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="font-size:12px; color:#605e5c; line-height:1.4; margin-bottom:15px; background:#f3f2f1; padding:10px; border-radius:4px;">
            <b>Suggestions:</b><br>
            - Summarize the NAVEX intake<br>
            - Find similar precedent cases<br>
            - Draft witness interview plan
        </div>
        """, unsafe_allow_html=True)
        
        # Initial greeting if empty
        if not st.session_state.assistant_messages:
            st.session_state.assistant_messages.append({"role": "assistant", "content": "Hello! I have analyzed BRI-26-11514. Would you like me to draft an initial investigation plan or search for similar cases in our archives?"})

        for m in st.session_state.assistant_messages:
            with st.chat_message(m["role"]):
                st.markdown(f'<div style="font-size:13px; color:#323130;">{m["content"]}</div>', unsafe_allow_html=True)
        
        if a_prompt := st.chat_input("Ask Copilot...", key="copilot_input_final"):
            st.session_state.assistant_messages.append({"role": "user", "content": a_prompt})
            with st.chat_message("assistant"):
                placeholder = st.empty()
                res_dict = {"full": ""}
                
                if "precedent" in a_prompt.lower() or "similar" in a_prompt.lower():
                    m_res = "I found 2 similar cases: BRI-24-0021 (Harassment) and BRI-25-1104 (Workplace Policy). Both were resolved within 45 days."
                    placeholder.markdown(m_res)
                    res_dict["full"] = m_res
                elif "summarize" in a_prompt.lower() or "navex" in a_prompt.lower():
                    m_res = "The NAVEX intake alleges verbal harassment and policy violations. There are 3 witnesses mentioned. The SLA is currently Standard (10 days)."
                    placeholder.markdown(m_res)
                    res_dict["full"] = m_res
                else:
                    async def run_a_stream_final():
                        async for chunk in chat_stream(a_prompt, mode="assistant"):
                            res_dict["full"] += chunk
                            placeholder.markdown(res_dict["full"] + "▌")
                        placeholder.markdown(res_dict["full"])
                    asyncio.run(run_a_stream_final())
            
            if res_dict["full"]:
                st.session_state.assistant_messages.append({"role": "assistant", "content": res_dict["full"]})
                st.rerun()

# ── Global Floating Toggle (Copilot) ────────────────────────────────
st.markdown("""
<div style="position: fixed; bottom: 30px; right: 30px; z-index: 10000;">
""", unsafe_allow_html=True)
if st.button("Copilot", key="floating_bubble_btn_sparkle", help="Open Copilot Assistant"):
    st.session_state.show_assistant = not st.session_state.show_assistant
    st.rerun()
st.markdown("</div>", unsafe_allow_html=True)
