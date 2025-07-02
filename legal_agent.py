from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()


def call_openai_agent(prompt):
    client = OpenAI(
    # This is the default and can be omitted
    api_key=os.getenv("OPENAI_API_KEY"),
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return response.choices[0].message.content

def legal_agent(brief):
    prompt = f"""
    You are a legal and compliance expert. Based on the following business idea, give a structured legal analysis.

    Brief: "{brief}"

    Return:
    1. Applicable regulations or laws
    2. Risks & legal concerns
    3. Recommended next steps
    4. Jurisdictions of concern

    Include links or cases that could be relevant to the brief
    """
    return call_openai_agent(prompt)