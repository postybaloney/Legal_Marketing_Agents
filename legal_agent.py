import asyncio
import aiohttp
import concurrent.futures
from openai import OpenAI
import streamlit as st
import json
from datetime import datetime
import time
from typing import Dict, List, Any, Optional
import threading
from queue import Queue
import os
from dotenv import load_dotenv
load_dotenv()

class LegalAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.govinfo_key = os.getenv("GOVINFO_API_KEY")
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        self.results_queue = Queue()
        self.session = None
        
    async def create_session(self):
        """Create async session for concurrent API calls"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close_session(self):
        """Close async session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def call_openai_agent_optimized(self, prompt, temperature=0.2, model="gpt-4o-mini"):
        """Optimized OpenAI call with faster model and reduced tokens"""
        try:
            response = self.client.chat.completions.create(
                model=model,  # Using faster model
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=2000,  # Reduced from 4000
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"OpenAI API Error: {str(e)}"
    
    async def async_case_research(self, brief, max_results=5):
        """Async case research with reduced scope"""
        case_sources = []
        
        try:
            # Generate fewer, more targeted queries
            federal_query = self.call_openai_agent_optimized(
                f"Generate 2-3 precise legal search queries for: {brief}. "
                f"Focus on most critical regulatory and liability issues. "
                f"Return as comma-separated list."
            )
            
            session = await self.create_session()
            
            # Limit to 2-3 queries instead of 5
            queries = [q.strip() for q in federal_query.split(',')[:3]]
            
            # Run queries concurrently
            tasks = []
            for query in queries:
                url = f"https://www.courtlistener.com/api/rest/v4/search/?type=o&order_by=dateFiled%20desc&q={query}&court=scotus,ca1,ca2,ca3,ca4,ca5,ca6,ca7,ca8,ca9,ca10,ca11,cadc,cafc"
                tasks.append(self.fetch_case_data(session, url, query))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    case_sources.extend(result[:3])  # Limit to top 3 per query
                    
        except Exception as e:
            case_sources.append({"error": f"Case search failed: {str(e)}"})
            
        return case_sources
    
    async def fetch_case_data(self, session, url, query):
        """Fetch case data asynchronously"""
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    opinions = data.get("results", [])[:3]
                    return [{
                        "source": "Federal Courts",
                        "case": item.get('caseName', 'Unnamed Case'),
                        "url": f"https://www.courtlistener.com{item['absolute_url']}",
                        "date": item.get('dateFiled', 'Unknown'),
                        "court": item.get('court', 'Unknown Court'),
                        "query": query
                    } for item in opinions]
        except Exception as e:
            return [{"error": f"Fetch failed: {str(e)}"}]
        return []
    
    async def async_regulatory_research(self, brief):
        """Async regulatory research with streamlined approach"""
        regulatory_sources = []
        
        try:
            # Simplified regulatory query
            reg_query = self.call_openai_agent_optimized(
                f"What are the top 3 regulatory agencies for: {brief}? "
                f"List agency names and primary regulation types only."
            )
            
            # Skip complex GovInfo API and use simpler search
            if self.serpapi_key:
                session = await self.create_session()
                
                serp_url = "https://serpapi.com/search"
                params = {
                    "engine": "google",
                    "q": f"{reg_query} compliance requirements 2024",
                    "api_key": self.serpapi_key,
                    "num": 3  # Reduced from 5
                }
                
                try:
                    async with session.get(serp_url, params=params) as response:
                        if response.status == 200:
                            results = await response.json()
                            for item in results.get("organic_results", [])[:3]:
                                regulatory_sources.append({
                                    "source": "Regulatory Compliance",
                                    "title": item.get('title', 'Regulation'),
                                    "url": item.get('link', ''),
                                    "snippet": item.get('snippet', ''),
                                    "relevance": "High"
                                })
                except Exception as e:
                    regulatory_sources.append({"error": f"Regulatory search failed: {str(e)}"})
                    
        except Exception as e:
            regulatory_sources.append({"error": f"Regulatory research failed: {str(e)}"})
            
        return regulatory_sources
    
    def generate_streaming_analysis(self, brief, research_data, progress_callback=None):
        """Generate analysis with streaming updates"""
        
        # Step 1: Generate risk matrix
        if progress_callback:
            progress_callback("Generating risk assessment matrix...", 0.3)
            
        risk_matrix = self.generate_risk_matrix_optimized(brief, research_data)
        
        # Step 2: Generate compliance roadmap
        if progress_callback:
            progress_callback("Creating compliance roadmap...", 0.6)
            
        compliance_roadmap = self.generate_compliance_roadmap_optimized(brief, research_data)
        
        # Step 3: Generate executive summary
        if progress_callback:
            progress_callback("Finalizing executive summary...", 0.9)
            
        executive_summary = self.generate_executive_summary_optimized(brief, risk_matrix, compliance_roadmap)
        
        return {
            "risk_matrix": risk_matrix,
            "compliance_roadmap": compliance_roadmap,
            "executive_summary": executive_summary
        }
    
    def generate_risk_matrix_optimized(self, brief, research_data):
        """Optimized risk matrix generation"""
        risk_prompt = f"""
        Based on: "{brief}"
        
        Create a focused legal risk matrix:
        
        1. TOP 3 CRITICAL RISKS
        2. TOP 3 SIGNIFICANT RISKS
        3. KEY MITIGATION STRATEGIES
        
        For each risk: Description, Impact, Probability, Mitigation
        Keep response under 1500 words.
        """
        
        return self.call_openai_agent_optimized(risk_prompt, temperature=0.1)
    
    def generate_compliance_roadmap_optimized(self, brief, research_data):
        """Optimized compliance roadmap"""
        roadmap_prompt = f"""
        Create a focused compliance roadmap for: "{brief}"
        
        ## IMMEDIATE ACTIONS (0-30 days)
        ## SHORT-TERM (1-6 months)
        ## MEDIUM-TERM (6-18 months)
        
        For each: 3-5 key actions, resources needed, timeline
        Keep response under 1500 words.
        """
        
        return self.call_openai_agent_optimized(roadmap_prompt, temperature=0.1)
    
    def generate_executive_summary_optimized(self, brief, risk_matrix, compliance_roadmap):
        """Optimized executive summary"""
        summary_prompt = f"""
        Create executive summary for: "{brief}"
        
        ## EXECUTIVE SUMMARY
        ### Key Findings
        ### Critical Risks
        ### Strategic Recommendations
        
        ## DETAILED ANALYSIS
        ### Risk Assessment
        {risk_matrix}
        
        ### Compliance Roadmap
        {compliance_roadmap}
        
        Keep total response under 2000 words.
        """
        
        return self.call_openai_agent_optimized(summary_prompt, temperature=0.1)
    
    async def legal_agent_optimized(self, brief, progress_callback=None):
        """Optimized main legal analysis function"""
        
        if progress_callback:
            progress_callback("Starting legal research...", 0.1)
        
        # Run research concurrently
        research_tasks = [
            self.async_case_research(brief, max_results=3),
            self.async_regulatory_research(brief)
        ]
        
        if progress_callback:
            progress_callback("Gathering research data...", 0.2)
        
        # Execute research in parallel
        case_research, regulatory_intel = await asyncio.gather(*research_tasks)
        
        # Compile research data
        research_data = {
            "case_law": case_research,
            "regulatory": regulatory_intel,
            "analysis_date": datetime.now().isoformat()
        }
        
        if progress_callback:
            progress_callback("Analyzing research data...", 0.25)
        
        # Generate analysis with streaming updates
        analysis_results = self.generate_streaming_analysis(brief, research_data, progress_callback)
        
        # Compile final results
        final_analysis = analysis_results["executive_summary"]
        
        # Add simplified citations
        citations = "\n\n## KEY SOURCES\n\n"
        for source_type, sources in research_data.items():
            if source_type != "analysis_date" and sources:
                citations += f"### {source_type.title()}:\n"
                for source in sources[:3]:  # Limit to top 3
                    if isinstance(source, dict) and "error" not in source:
                        citations += f"- {source.get('title', source.get('case', 'Source'))}\n"
                        if source.get('url'):
                            citations += f"  📎 {source['url']}\n"
        
        # Close session
        await self.close_session()
        
        if progress_callback:
            progress_callback("Analysis complete!", 1.0)
        
        return final_analysis + citations

# Streamlit integration functions
def run_optimized_legal_analysis(brief, progress_callback=None):
    """Run optimized legal analysis with progress updates"""
    agent = LegalAgent()
    return asyncio.run(agent.legal_agent_optimized(brief, progress_callback))

def legal_agent_optimized(brief):
    """Main function for optimized legal analysis"""
    return run_optimized_legal_analysis(brief)