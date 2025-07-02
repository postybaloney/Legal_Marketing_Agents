import streamlit as st
from legal_agent import legal_agent
from marketing_agent import marketing_agent

st.title("AI Advisor Agents")

agent_type = st.selectbox("Choose your Agent", ["Legal & Compliance", "Marketing & Analysis"])
brief = st.text_area("Enter your business brief")
if st.button("Run Agent") and brief:
    with st.spinner("Processing..."):
        if agent_type == "Legal & Compliance":
            output = legal_agent(brief)
        else:
            output = marketing_agent(brief)
        st.markdown("---")
        st.text_area("Result", output, height=400)
