import streamlit as st
from legal_agent import legal_agent
from marketing_agent import marketing_agent
import time

def typewriter_output(text):
    container = st.empty()
    full_output = ""
    for char in text:
        full_output += char
        container.markdown(full_output, unsafe_allow_html=True)
        time.sleep(0.005)

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
        typewriter_output(output)
        # st.markdown(output, unsafe_allow_html=True)
