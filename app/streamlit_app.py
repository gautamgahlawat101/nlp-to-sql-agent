"""
app/streamlit_app.py

The chat interface: type a question, see the generated SQL (for
transparency) and the resulting table. This is a thin UI layer over
agent/conversation_manager.py — all the actual logic lives there.

Run locally:
    streamlit run app/streamlit_app.py
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd

from agent.conversation_manager import ask

st.set_page_config(page_title="NLP-to-SQL Agent", layout="wide")

st.title("NLP-to-SQL Agent")
st.caption(
    "Ask a business question in plain English — it gets translated into SQL, "
    "validated, and run against a live PostgreSQL database across 6 schemas."
)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Replay chat history on every rerun — Streamlit re-executes the whole script
# on each interaction, so past messages have to be stored and redrawn.
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sql"):
            with st.expander("Generated SQL"):
                st.code(msg["sql"], language="sql")
        if msg.get("rows") is not None:
            if len(msg["rows"]) > 0:
                st.dataframe(pd.DataFrame(msg["rows"]), use_container_width=True)
            else:
                st.info("Query ran successfully but returned no rows.")

question = st.chat_input("Ask a question about campaigns, customers, sales, loyalty, or products...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = ask(question)

        if result["status"] == "success":
            summary = f"Found **{len(result['rows'])}** result(s)."
            st.markdown(summary)
            with st.expander("Generated SQL"):
                st.code(result["sql"], language="sql")
            if result["rows"]:
                st.dataframe(pd.DataFrame(result["rows"]), use_container_width=True)
            else:
                st.info("Query ran successfully but returned no rows.")

            st.session_state.messages.append({
                "role": "assistant", "content": summary,
                "sql": result["sql"], "rows": result["rows"],
            })

        elif result["status"] == "clarify":
            st.markdown(result["question"])
            st.session_state.messages.append({"role": "assistant", "content": result["question"]})

        else:
            st.error(result["message"])
            st.session_state.messages.append({
                "role": "assistant", "content": f"Something went wrong: {result['message']}",
            })

            