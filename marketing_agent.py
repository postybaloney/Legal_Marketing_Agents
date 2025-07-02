from openai import OpenAI
import requests
import os
from dotenv import load_dotenv
load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

def get_statista_data(query):
    serp_query = f"site:statista.com {query}"
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": serp_query,
        "api_key": SERPAPI_KEY
    }
    res = requests.get(url, params=params)
    results = res.json()
    statista_results = [
        f"{item.get('title')}: {item.get('link')}" for item in results.get("organic_results", [])
        if "statista.com" in item.get("link", "")
    ]
    return "\n".join(statista_results[:5])

# --- OpenAI Prompt Wrapper ---
def call_openai_agent(prompt):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return response.choices[0].message.content

# --- SerpAPI Wrapper ---
def get_serpapi_results(query):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY
    }
    response = requests.get(url, params=params)
    results = response.json()
    snippets = []
    for item in results.get("organic_results", []):
        if "snippet" in item:
            snippets.append(item["snippet"])
    return "\n".join(snippets[:3])

def marketing_agent(brief):
    serp_snippets = get_serpapi_results(f"market size and competitors for: {brief}")
    statista_info = get_statista_data(f"{brief} market size or trend")

    prompt = f"""
        You are a marketing analyst. Based on this startup idea, provide a marketing analysis.

        Brief: "{brief}"

        Include:
        1. Total addressable market (based on known data)
        2. Key competitors and their pros/cons
        3. Market trends
        4. Opportunities for this product
        5. Based on this real-world info:
        {serp_snippets}

        Statista-based references:
        {statista_info}

        Include links to any specific sources or SERP API queries used.
    """
    return call_openai_agent(prompt)