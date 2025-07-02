from openai import OpenAI
import requests
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

def get_courtlistener_cases(query, max_results=5):
    url = f"https://www.courtlistener.com/api/rest/v4/search/?type=o&order_by=dateFiled%20desc&q={query}"
    response = requests.get(url)
    data = response.json()
    opinions = data.get("results", [])[:max_results]
    return "\n".join([f"{item.get('caseName', 'Unnamed Case')} - https://www.courtlistener.com{item['absolute_url']}" for item in opinions])

# --- Harvard Caselaw Search ---
def get_harvard_caselaw_links(brief):
    query = call_openai_agent(f"Choose an efficient query for https://case.law/search to find relevant documents to {brief}. Return only a query")
    return f"Search Harvard Caselaw: https://case.law/search/?q={query.replace(' ', '+')}"

# --- GovInfo Docs ---
def get_govinfo_docs(query, max_results=3):
    url = f"https://api.govinfo.gov/collections/USCOURTS/2024-01-01T00:00:00Z?query={query}&pageSize={max_results}&api_key={os.getenv("GOVINFO_API_KEY")}"
    response = requests.get(url)
    if response.status_code != 200:
        return "GovInfo API error or rate-limited."
    data = response.json()
    items = data.get("packages", [])
    return "\n".join([f"{doc.get('title', 'Untitled')} - {doc.get('packageLink')}" for doc in items])

def legal_agent(brief):
    courtlistener_cases = get_courtlistener_cases(brief)
    harvard_link = get_harvard_caselaw_links(brief)
    govinfo_refs = get_govinfo_docs(brief)

    prompt = f"""
        You are a legal and compliance expert. Based on the following business idea, give a structured legal analysis.

        Brief: "{brief}"

        Return:
        1. Applicable regulations or laws
        2. Risks & legal concerns
        3. Recommended next steps
        4. Jurisdictions of concern

        Use these resources to enrich your analysis
            Relevant Court Cases (CourtListener):
            {courtlistener_cases}

            Harvard Caselaw Search:
            {harvard_link}

            GovInfo Documents:
            {govinfo_refs}
        Include all links to references that you use in your analysis
    """
    return call_openai_agent(prompt)