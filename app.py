# ✅ FINAL VERSION (Cloud-Ready)

import os
import json
import re
import io
import PyPDF2
import streamlit as st
import spacy
from openai import OpenAI
import base64
import pandas as pd

client = OpenAI(
    api_key="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",
    base_url="https://api.groq.com/openai/v1"
)

nlp = spacy.load("en_core_web_sm")

st.set_page_config(layout="wide")
st.title("📄 AI Investor Memo Generator (Groq + Web Simulation)")

for key in ["chat_history", "memo_generated", "final_memo", "pdf_bytes", "page_texts", "combined_page_summaries", "condensed_summary", "simulated_web_data", "entities"]:
    if key not in st.session_state:
        st.session_state[key] = None

if "user_company_name" not in st.session_state:
    st.session_state.user_company_name = None

if not st.session_state.user_company_name:
    with st.form("company_form"):
        st.markdown("### 🚀 Before we begin, tell us the startup's name:")
        entered_name = st.text_input("Company Name", placeholder="e.g., Zepto, Bluelearn, etc.", max_chars=100)
        submitted = st.form_submit_button("Start")
        if submitted and entered_name.strip():
            st.session_state.user_company_name = entered_name.strip()
            st.rerun()
    st.stop()

with st.sidebar:
    st.markdown("### 🏷️ Company Details")
    st.markdown(f"**Current Company:** `{st.session_state.user_company_name}`")
    if st.button("🔁 Change Company Name"):
        st.session_state.user_company_name = None
        st.session_state.memo_generated = False
        st.rerun()
    uploaded_file = st.file_uploader("Upload a Pitch Deck (PDF)", type="pdf")

def chat_with_groq(user_input):
    messages = (st.session_state.chat_history or []) + [{"role": "user", "content": user_input}]
    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=messages,
            temperature=0.5
        )
        reply = response.choices[0].message.content.strip()
        st.session_state.chat_history = messages + [{"role": "assistant", "content": reply}]
        return reply
    except Exception as e:
        return f"[Chatbot Error: {str(e)}]"

def summarize_page_content(page_text, page_number):
    prompt = f"Summarize this pitch deck page {page_number} for investment analysis:\n\n{page_text}"
    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Groq failed on page {page_number}: {str(e)}]"

def summarize_entire_deck(summary_text, company, founders):
    prompt = f"""
You are helping compress a pitch deck for a VC analyst...
Company name: {company}
Founders: {', '.join(founders)}

--- Full Pitch Text ---
{summary_text}
"""
    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Groq summarization failed: {str(e)}]"

def analyze_entities(text):
    doc = nlp(text)
    return {
        "companies": list(set(ent.text.strip() for ent in doc.ents if ent.label_ == "ORG")),
        "people": list(set(ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON")),
    }

def groq_simulate_web_research(company, founders):
    prompt = f"""
Simulate online research for a startup: {company}, by {', '.join(founders)}
(Website, product, traction, news, etc.) in JSON.
"""
    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Groq search simulation failed: {str(e)}]"

def generate_final_memo(condensed_summary, simulated_web_data):
    prompt = f"""
Write a detailed VC memo using:
--- Pitch ---
{condensed_summary}
--- Web Research ---
{simulated_web_data}
"""
    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Groq final memo failed: {str(e)}]"

def show_pdf():
    pdf_base64 = base64.b64encode(st.session_state.pdf_bytes).decode("utf-8")
    st.markdown(f'<iframe src="data:application/pdf;base64,{pdf_base64}" width="100%" height="700px"></iframe>', unsafe_allow_html=True)

def build_summary_table():
    prompt = f"Extract detailed summary as structured JSON from:\n{st.session_state.final_memo}"
    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        content = response.choices[0].message.content.strip()
        json_block = re.search(r'\[.*?\]', content, re.DOTALL)
        return pd.DataFrame(json.loads(json_block.group(0)))
    except Exception as e:
        return pd.DataFrame([{"Section": "Error", "Details": str(e)}])

if uploaded_file and not st.session_state.memo_generated:
    st.session_state.pdf_bytes = uploaded_file.read()
    reader = PyPDF2.PdfReader(io.BytesIO(st.session_state.pdf_bytes))
    st.session_state.page_texts = [page.extract_text() for page in reader.pages if page.extract_text()]

    status_box = st.empty()
    summaries = []
    for i, page in enumerate(st.session_state.page_texts):
        status_box.info(f"🧠 Summarizing page {i+1}...")
        summaries.append(f"[Page {i+1}]\n{summarize_page_content(page[:3000], i+1)}")
    st.session_state.combined_page_summaries = summaries

    all_text = "\n".join(st.session_state.page_texts)
    st.session_state.entities = analyze_entities(all_text)
    company = st.session_state.user_company_name
    founders = st.session_state.entities["people"][:3]

    status_box.info("🧠 Condensing pitch content...")
    st.session_state.condensed_summary = summarize_entire_deck("\n\n".join(summaries), company, founders)

    status_box.info("🌐 Simulating web research...")
    st.session_state.simulated_web_data = groq_simulate_web_research(company, founders)

    status_box.info("📊 Generating investor memo...")
    st.session_state.final_memo = generate_final_memo(st.session_state.condensed_summary, st.session_state.simulated_web_data)
    st.session_state.memo_generated = True
    status_box.success("✅ Memo generated!")

if st.session_state.memo_generated:
    tab1, tab2, tab3, tab4 = st.tabs(["📘 Memo", "📄 PDF Preview", "💬 Chat", "📋 Summary Table"])

    with tab1:
        st.subheader("📘 Final Investor Memo")
        st.markdown(st.session_state.final_memo)
        st.download_button("📥 Download Memo", st.session_state.final_memo, file_name="Investor_Memo.txt")

    with tab2:
        st.subheader("📄 Original Pitch Deck Preview")
        show_pdf()

    with tab3:
        st.subheader("💬 VC Chat Assistant")
        user_input = st.text_input("Ask a question about the startup, market, team...", key="chat_input")
        if user_input and user_input.strip():
            response = chat_with_groq(user_input)
            st.markdown(f"**🧑‍💼 You:** {user_input}")
            st.markdown(f"**🤖 AI Analyst:** {response}")

        if st.session_state.chat_history:
            st.markdown("---")
            st.markdown("### 💬 Chat History")
            for msg in st.session_state.chat_history:
                role = "🧑‍💼 You" if msg["role"] == "user" else "🤖 AI Analyst"
                st.markdown(f"**{role}:** {msg['content']}")

    with tab4:
        st.subheader("📋 In-Depth AI-Filled Executive Summary Table (with Links)")
        df = build_summary_table()
        st.dataframe(df, use_container_width=True, hide_index=True)
