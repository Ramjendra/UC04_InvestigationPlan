import streamlit as st
import asyncio
import json
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from simulated_data import EXISTING_CASES, ATTORNEYS, DATA_SOURCES, KNOWLEDGE_BASE
from plan_agent import run_plan_agent
from dataverse_client import DataverseClient
from logger_config import logger

load_dotenv()
logger.info("--- BRI Assistant Starting Up ---")

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="UCM | BRI Agent",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

dv_client = DataverseClient()
if "current_plan" not in st.session_state:
    st.session_state.current_plan = dv_client.get_investigation_plan("BRI-26-11514")
plan = st.session_state.current_plan

# ── Global Premium CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {
        font-family: 'Segoe UI', 'Inter', sans-serif;
        background-color: #ffffff !important;
        color: #323130 !important;
    }

    /* Sidebar specific overrides — Dark Dynamics 365 */
    [data-testid="stSidebar"] {
        background: #212121 !important;
        border-right: none;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p, 
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #ffffff !important;
        font-size: 12px !important;
        margin-bottom: 0px;
        padding: 6px 0;
        cursor: pointer;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p:hover {
        background: #333333;
    }
    [data-testid="stSidebar"] hr {
        border-color: #444 !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        color: #ffffff !important;
        font-size: 11px !important;
    }
    
    /* Ensure radio buttons and info boxes look good on white */
    .stRadio label { color: #323130 !important; }
    .stAlert { background-color: #f3f2f1 !important; border: 1px solid #edebe9 !important; color: #323130 !important; }

    /* UCM Styling */
    .ucm-card {
        background: white;
        border: 1px solid #e1dfdd;
        border-radius: 4px;
        padding: 0;
        margin-bottom: 24px;
        box-shadow: 0 1.6px 3.6px 0 rgba(0,0,0,0.132), 0 0.3px 0.9px 0 rgba(0,0,0,0.108);
    }
    .ucm-header {
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        padding: 12px 16px;
        background: #faf9f8;
        border-bottom: 1px solid #edebe9;
        color: #323130;
    }
    .ucm-body { padding: 16px; color: #323130; }

    /* Progress Bar Text Visibility */
    .progress-text {
        font-size: 11px;
        margin-top: 6px;
        color: #323130;
    }

    /* Floating Assistant Button */
    .stButton > button#fab_btn {
        position: fixed;
        bottom: 30px;
        right: 30px;
        width: 64px;
        height: 64px;
        border-radius: 50% !important;
        background: linear-gradient(135deg, #0078d4, #005a9e) !important;
        color: white !important;
        font-size: 28px !important;
        box-shadow: 0 8px 16px rgba(0, 120, 212, 0.3) !important;
        border: none !important;
        z-index: 99999 !important;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s ease !important;
    }
    .stButton > button#fab_btn:hover {
        transform: scale(1.1);
        box-shadow: 0 12px 24px rgba(0, 120, 212, 0.4) !important;
    }

    /* Assistant Panel Style */
    .assistant-panel {
        background: white;
        border-left: 2px solid #edebe9;
        height: 100vh;
        padding-left: 20px;
        box-shadow: -4px 0 16px rgba(0,0,0,0.05);
    }

    /* Suggestion Chips */
    .suggestion-chip {
        display: inline-block;
        background: #f3f2f1;
        border: 1px solid #e1dfdd;
        border-radius: 16px;
        padding: 6px 14px;
        font-size: 11px;
        color: #0078d4;
        cursor: pointer;
        margin: 3px 4px;
        transition: all 0.2s ease;
    }
    .suggestion-chip:hover {
        background: #e1dfdd;
        border-color: #0078d4;
    }

    /* Pipeline Indicator */
    .pipeline-bar {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        background: #f0f6ff;
        border-radius: 4px;
        font-size: 10px;
        color: #005a9e;
        margin: 8px 0;
    }
    .pipeline-step {
        display: flex;
        align-items: center;
        gap: 3px;
    }
    .pipeline-arrow {
        color: #a19f9d;
        font-size: 10px;
    }

    /* Chat message rendering */
    .bri-response {
        max-height: 400px;
        overflow-y: auto;
        padding-right: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────
if "chat_open" not in st.session_state: st.session_state.chat_open = False
if "messages" not in st.session_state: st.session_state.messages = []
if "ai_mode" not in st.session_state: st.session_state.ai_mode = "Simulated Mock"
if "suggestion_prompt" not in st.session_state: st.session_state.suggestion_prompt = None
if "handled_messages" not in st.session_state: st.session_state.handled_messages = set()

# ── Sidebar — Dynamics 365 Navigation ──────────────────────────────────────
with st.sidebar:
    # Dynamics 365 branding
    st.markdown("""
    <div style="padding: 10px 15px 5px 15px; font-size: 14px; font-weight: 600; color: #ffffff;">
        Dynamics 365
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Navigation items
    st.markdown("🏠  Home")
    st.markdown("🕐  Recent")
    st.markdown("📌  Pinned")
    
    st.markdown('<div style="color: #8a8886; font-size: 10px; font-weight: 600; padding: 15px 0 5px 0; text-transform: uppercase;">Case Management</div>', unsafe_allow_html=True)
    st.markdown("🏛️  Home Dashboard")
    st.markdown("📂  Cases")
    st.markdown("🔍  Contact Search")
    st.markdown("🔒  Revoke Access")

    st.markdown('<div style="color: #8a8886; font-size: 10px; font-weight: 600; padding: 15px 0 5px 0; text-transform: uppercase;">Configurations</div>', unsafe_allow_html=True)
    st.markdown("📋  Policies")

    st.markdown('<div style="color: #8a8886; font-size: 10px; font-weight: 600; padding: 15px 0 5px 0; text-transform: uppercase;">Other Tools</div>', unsafe_allow_html=True)
    st.markdown("🔗  PMO Link")
    st.markdown("🎬  Video Link")

    st.markdown("---")
    # AI mode toggle (compact, at bottom)
    st.session_state.ai_mode = st.radio(
        "AI Mode",
        ["Simulated Mock", "Live Azure Foundry"],
        index=0,
        label_visibility="collapsed"
    )

# ── Persistent Assistant Toggle ──────────────────────────────────────────────
if not st.session_state.chat_open:
    if st.button("🤖", key="fab_btn"):
        st.session_state.chat_open = True
        st.rerun()

# ── Layout ──────────────────────────────────────────────────────────────────
if st.session_state.chat_open:
    main_col, chat_col = st.columns([0.65, 0.35])
else:
    main_col = st.container()

with main_col:
    # Breadcrumbs
    st.markdown('<div style="font-size:12px; color:#0078d4; margin-bottom:10px">Dynamics 365 > Business and Regulatory Investigations > Cases</div>', unsafe_allow_html=True)
    
    # Case Title
    col_t, col_s = st.columns([3, 1])
    with col_t:
        st.markdown('<h2 style="margin:0; font-size:22px; font-weight:700; color:#323130">BRI-26-11514 [Pending - NAVEX]</h2>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:13px; color:#605e5c">Asian Desktop · Created 2/22/2026</div>', unsafe_allow_html=True)
    with col_s:
        st.markdown('<div style="text-align:right"><span style="background:#0078d4; color:white; padding:6px 12px; border-radius:2px; font-weight:700">Active</span></div>', unsafe_allow_html=True)

    # Progress Bar UI
    st.markdown("""
    <div style="background:white; padding:24px; border:1px solid #e1dfdd; border-radius:4px; margin:20px 0">
        <div style="display:flex; justify-content:space-between; position:relative; padding:0 10%">
            <div style="position:absolute; top:8px; left:10%; right:10%; height:2px; background:#edebe9"></div>
            <div style="position:absolute; top:8px; left:10%; width:50%; height:2px; background:#0078d4"></div>
            <div style="z-index:2; text-align:center"><div style="width:16px; height:16px; background:#0078d4; border-radius:50%; margin:auto"></div><div class="progress-text">Intake</div></div>
            <div style="z-index:2; text-align:center"><div style="width:16px; height:16px; background:#0078d4; border-radius:50%; margin:auto"></div><div class="progress-text">Triage</div></div>
            <div style="z-index:2; text-align:center"><div style="width:20px; height:20px; background:white; border:4px solid #0078d4; border-radius:50%; margin:-2px auto 0 auto"></div><div class="progress-text" style="font-weight:700">Investigation</div></div>
            <div style="z-index:2; text-align:center"><div style="width:16px; height:16px; background:#edebe9; border-radius:50%; margin:auto"></div><div class="progress-text">Reporting</div></div>
            <div style="z-index:2; text-align:center"><div style="width:16px; height:16px; background:#edebe9; border-radius:50%; margin:auto"></div><div class="progress-text">Closed</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tabs
    tabs = st.tabs(["Profile", "Parties", "Case Relationship", "Investigation Plan", "Documents", "Task Board", "Timeline"])
    
    with tabs[3]: # Investigation Plan
        st.markdown('<div style="text-align:center; padding:10px 0; font-size:12px; color:#605e5c">Privileged and Confidential</div>', unsafe_allow_html=True)
        
        # Sections
        st.markdown('<div class="ucm-card"><div class="ucm-header">Attorney Comments</div><div class="ucm-body">', unsafe_allow_html=True)
        st.text_area("att_comm", value=plan["attorney_comments"], height=100, label_visibility="collapsed")
        st.markdown('</div></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="ucm-card"><div class="ucm-header">Summary of Allegations</div><div class="ucm-body">', unsafe_allow_html=True)
        st.markdown(f'<div style="background:#f3f2f1; padding:12px; border-radius:2px; font-size:13px; line-height:1.6; color:#323130">{plan["summary_of_allegations"]}</div>', unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="ucm-card"><div class="ucm-header">Questions to be Answered</div><div class="ucm-body">', unsafe_allow_html=True)
        st.table(pd.DataFrame(plan["questions_to_be_answered"]))
        st.markdown('</div></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="ucm-card"><div class="ucm-header">Proposed Investigative Steps</div><div class="ucm-body">', unsafe_allow_html=True)
        st.table(pd.DataFrame(plan["proposed_investigative_steps"]))
        st.markdown('</div></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# ASSISTANT PANEL (BRI Agent — 35% Vertical)
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.chat_open:
    with chat_col:
        # ── Header ──
        st.markdown("""
            <div style="background: linear-gradient(135deg, #0078d4, #005a9e); color:white; padding:16px 20px; border-radius:4px 4px 0 0;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span style="font-weight:700; font-size: 15px;">BRI Agent</span>
                        <span style="font-size:10px; background:rgba(255,255,255,0.2); padding:2px 8px; border-radius:4px; margin-left:8px;">Connected</span>
                    </div>
                    <span style="font-size:10px; opacity:0.8;">Azure OpenAI "On Your Data"</span>
                </div>
                <div style="margin-top:8px;">
                    <div class="pipeline-bar" style="background: rgba(255,255,255,0.15); color: white;">
                        <span class="pipeline-step">🔍 Dataverse</span>
                        <span class="pipeline-arrow">→</span>
                        <span class="pipeline-step">🧠 Embeddings</span>
                        <span class="pipeline-arrow">→</span>
                        <span class="pipeline-step">📚 AI Search</span>
                        <span class="pipeline-arrow">→</span>
                        <span class="pipeline-step">💬 Chatbot</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # ── Suggestion Chips ──
        chip_col1, chip_col2, chip_col3, chip_col4 = st.columns(4)
        with chip_col1:
            if st.button("📋 Status", key="chip_status", use_container_width=True):
                st.session_state.suggestion_prompt = "What is the latest on case BRI-26-08314"
                st.rerun()
        with chip_col2:
            if st.button("📌 Next Steps", key="chip_next", use_container_width=True):
                st.session_state.suggestion_prompt = "What are the next steps for case BRI-26-08314"
                st.rerun()
        with chip_col3:
            if st.button("🔗 Similar", key="chip_similar", use_container_width=True):
                st.session_state.suggestion_prompt = "Find me similar cases to BRI-26-08314"
                st.rerun()
        with chip_col4:
            if st.button("📊 Propose Steps", key="chip_propose", use_container_width=True):
                st.session_state.suggestion_prompt = "Propose investigation steps for case BRI-26-08314"
                st.rerun()

        # ── Welcome message when no messages yet ──
        if not st.session_state.messages:
            st.markdown("""
            <div style="font-family: 'Segoe UI', sans-serif; padding: 16px; font-size: 13px; color: #323130; 
                        line-height: 1.7; background: #f9f9f9; border-radius: 4px; border: 1px solid #edebe9; margin: 8px 0;">
                👋 <b>Welcome!</b> I'm the <b>BRI Investigation Agent</b>.<br><br>
                <b>🔍 Try asking me:</b><br>
                <div style="margin-left: 12px; margin-top: 4px;">
                    📊 "Propose investigation steps for BRI-26-08314"<br>
                    📋 "What is the latest on case BRI-26-08314"<br>
                    📌 "What are the next steps for case BRI-26-08314"<br>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ── Display existing messages ──
        for i, msg in enumerate(st.session_state.messages):
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["content"])
            else:
                with st.chat_message("assistant"):
                    content = msg["content"]
                    response_text = content.get("response", "") if isinstance(content, dict) else str(content)
                    st.markdown(response_text, unsafe_allow_html=True)
                    
                    # Show Accept/Reject buttons for assistant messages that haven't been handled
                    msg_id = f"msg_{i}"
                    if msg_id not in st.session_state.handled_messages:
                        col_acc, col_rej = st.columns(2)
                        with col_acc:
                            if st.button("✅ Accept", key=f"acc_{i}", use_container_width=True):
                                content_preview = response_text[:100].replace('\n', ' ') + "..."
                                logger.info(f"ACTION: User ACCEPTED message {i}. Content Preview: {content_preview}")
                                st.session_state.handled_messages.add(msg_id)
                                
                                # Logic to update Investigation Plan tab
                                updated = False
                                if "Proposed Investigative Plan Structure" in response_text:
                                    logger.info(f"DATA_TRANSFER: Updating Proposed Steps from message {i}")
                                    # Simulate extracting the table data (since this is mock-focused)
                                    # In a real app, we'd extract from metadata or structured response
                                    new_steps = [
                                        {"Step": "Internal Document Review", "Owner": "Forensics Team", "Due Date": "2025-08-30", "Status": "In Progress"},
                                        {"Step": "Cummins Stakeholder Interview", "Owner": "Alicia Cullen", "Due Date": "2025-09-02", "Status": "Not Started"},
                                        {"Step": "Safety Risk Assessment", "Owner": "Engineering Lead", "Due Date": "2025-09-05", "Status": "Not Started"}
                                    ]
                                    st.session_state.current_plan["proposed_investigative_steps"] = new_steps
                                    updated = True

                                if "Case Summary" in response_text or "Allegation" in response_text:
                                    logger.info(f"DATA_TRANSFER: Updating Allegation Summary from message {i}")
                                    st.session_state.current_plan["summary_of_allegations"] = f"AI Update ({datetime.now().strftime('%m/%d/%Y')}): " + response_text
                                    updated = True
                                
                                if updated:
                                    st.success("Plan updated successfully!")
                                st.rerun()
                        with col_rej:
                            if st.button("❌ Reject", key=f"rej_{i}", use_container_width=True):
                                logger.info(f"ACTION: User REJECTED message {i}")
                                st.session_state.handled_messages.add(msg_id)
                                st.rerun()

        # ── Process prompt (from chip or chat input) ──
        prompt = st.session_state.suggestion_prompt
        st.session_state.suggestion_prompt = None  # Reset after consuming

        if not prompt:
            prompt = st.chat_input("Ask about BRI cases... (e.g., BRI-26-08314)", key="bri_chat_input")

        if prompt:
            logger.info(f"User submitted prompt: {prompt}")
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            
            with st.spinner("🔍 Searching Dataverse → 🧠 Embeddings → 📚 AI Search → 💬 Response..."):
                try:
                    from assistant_agent import get_assistant_response
                    history = [{"role": m["role"], "content": m["content"] if isinstance(m["content"], str) else m["content"].get("response", "")} for m in st.session_state.messages[:-1]]
                    response = asyncio.run(get_assistant_response(prompt, history, st.session_state.ai_mode))
                    logger.info("Successfully retrieved assistant response")
                except Exception as e:
                    logger.error(f"Error in get_assistant_response: {str(e)}")
                    response = "I encountered an error while processing your request. Please check the logs."
            
            # Store and render
            if isinstance(response, dict):
                st.session_state.messages.append({"role": "assistant", "content": response})
                with st.chat_message("assistant"):
                    st.markdown(response.get("response", ""), unsafe_allow_html=True)
            else:
                st.session_state.messages.append({"role": "assistant", "content": str(response)})
                with st.chat_message("assistant"):
                    st.write(str(response))
            
            st.rerun()

        # ── Minimize Button ──
        if st.button("✕ Minimize", use_container_width=True, key="minimize_btn"):
            st.session_state.chat_open = False
            st.rerun()

