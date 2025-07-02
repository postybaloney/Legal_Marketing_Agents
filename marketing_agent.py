from openai import OpenAI
import requests
import os
from dotenv import load_dotenv
load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

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
    """
    return call_openai_agent(prompt)