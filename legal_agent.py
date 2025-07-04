from openai import OpenAI
import requests
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import time

load_dotenv()

class LegalAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.govinfo_key = os.getenv("GOVINFO_API_KEY")
        self.serpapi_key = os.getenv("SERPAPI_KEY")
    
    def call_openai_agent(self, prompt, temperature=0.2, model="gpt-4o"):
        """Enhanced OpenAI call with better error handling and optimization for legal analysis"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=4000
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"OpenAI API Error: {str(e)}"
    
    def get_comprehensive_case_research(self, brief, max_results=10):
        """Enhanced case research with multiple jurisdictions and precedent analysis"""
        case_sources = []
        
        # CourtListener Federal Cases
        try:
            federal_query = self.call_openai_agent(
                f"Generate 5 to {max_results} precise legal search queries for federal cases related to: {brief}. "
                f"Focus on regulatory compliance, liability, and jurisdictional issues. "
                f"Return as comma-separated list."
            )
            
            for query in federal_query.split(',')[:5]:
                query = query.strip()
                url = f"https://www.courtlistener.com/api/rest/v4/search/?type=o&order_by=dateFiled%20desc&q={query}&court=scotus,ca1,ca2,ca3,ca4,ca5,ca6,ca7,ca8,ca9,ca10,ca11,cadc,cafc"
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    opinions = data.get("results", [])[:5]
                    for item in opinions:
                        case_sources.append({
                            "source": "Federal Courts",
                            "case": item.get('caseName', 'Unnamed Case'),
                            "url": f"https://www.courtlistener.com{item['absolute_url']}",
                            "date": item.get('dateFiled', 'Unknown'),
                            "court": item.get('court', 'Unknown Court'),
                            "query": query
                        })
        except Exception as e:
            case_sources.append({"error": f"Federal case search failed: {str(e)}"})
        
        # State Court Research
        try:
            state_query = self.call_openai_agent(
                f"Generate search terms for state court cases involving: {brief}. "
                f"Focus on state-specific regulations, licensing, and compliance issues."
            )
            
            # Using SerpAPI for state court research
            if self.serpapi_key:
                serp_url = "https://serpapi.com/search"
                params = {
                    "engine": "google",
                    "q": f"site:courts.state.*.us OR site:*.gov {state_query} case law",
                    "api_key": self.serpapi_key,
                    "num": 5
                }
                response = requests.get(serp_url, params=params)
                if response.status_code == 200:
                    results = response.json()
                    for item in results.get("organic_results", [])[:3]:
                        case_sources.append({
                            "source": "State Courts",
                            "case": item.get('title', 'State Case'),
                            "url": item.get('link', ''),
                            "snippet": item.get('snippet', ''),
                            "query": state_query
                        })
        except Exception as e:
            case_sources.append({"error": f"State case search failed: {str(e)}"})
            
        return case_sources
    
    def get_regulatory_intelligence(self, brief):
        """Advanced regulatory research across multiple agencies"""
        regulatory_sources = []
        
        # Federal Register Search
        try:
            reg_query = self.call_openai_agent(
                f"What are the key regulatory agencies and specific regulations that would apply to: {brief}? "
                f"List top 5 agencies (like SEC, FTC, FDA, EPA, etc.) and their relevant regulation types."
            )
            
            # GovInfo API for recent regulations
            if self.govinfo_key:
                url = f"https://api.govinfo.gov/collections/FR/2024-01-01T00:00:00Z"
                params = {
                    "query": reg_query,
                    "pageSize": 5,
                    "api_key": self.govinfo_key
                }
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    for doc in data.get("packages", []):
                        regulatory_sources.append({
                            "source": "Federal Register",
                            "title": doc.get('title', 'Regulation'),
                            "url": doc.get('packageLink', ''),
                            "date": doc.get('dateIssued', 'Unknown'),
                            "summary": doc.get('summary', 'No summary available')
                        })
        except Exception as e:
            regulatory_sources.append({"error": f"Regulatory search failed: {str(e)}"})
            
        # Industry-specific compliance research
        try:
            if self.serpapi_key:
                industry_query = self.call_openai_agent(
                    f"What industry does this business fall under: {brief}? "
                    f"What are the key compliance requirements and governing bodies?"
                )
                
                serp_url = "https://serpapi.com/search"
                params = {
                    "engine": "google",
                    "q": f"{industry_query} compliance requirements 2024 2025",
                    "api_key": self.serpapi_key,
                    "num": 5
                }
                response = requests.get(serp_url, params=params)
                if response.status_code == 200:
                    results = response.json()
                    for item in results.get("organic_results", [])[:3]:
                        regulatory_sources.append({
                            "source": "Industry Compliance",
                            "title": item.get('title', 'Compliance Guide'),
                            "url": item.get('link', ''),
                            "snippet": item.get('snippet', ''),
                            "relevance": "High"
                        })
        except Exception as e:
            regulatory_sources.append({"error": f"Industry compliance search failed: {str(e)}"})
            
        return regulatory_sources

    def get_international_considerations(self, brief):
        """Research international legal implications"""
        international_sources = []
        
        try:
            intl_query = self.call_openai_agent(
                f"Does this business have international implications: {brief}? "
                f"Consider data privacy (GDPR), trade regulations, IP laws, and cross-border compliance."
            )
            
            if self.serpapi_key:
                serp_url = "https://serpapi.com/search"
                params = {
                    "engine": "google",
                    "q": f"international compliance {brief} GDPR trade regulations",
                    "api_key": self.serpapi_key,
                    "num": 5
                }
                response = requests.get(serp_url, params=params)
                if response.status_code == 200:
                    results = response.json()
                    for item in results.get("organic_results", [])[:3]:
                        international_sources.append({
                            "source": "International Compliance",
                            "title": item.get('title', 'International Regulation'),
                            "url": item.get('link', ''),
                            "snippet": item.get('snippet', ''),
                            "jurisdiction": "Multi-jurisdictional"
                        })
        except Exception as e:
            international_sources.append({"error": f"International search failed: {str(e)}"})
            
        return international_sources

    def generate_risk_matrix(self, brief, research_data):
        """Generate comprehensive risk assessment matrix"""
        risk_prompt = f"""
        Based on this business brief: "{brief}"
        
        And this legal research data: {json.dumps(research_data, indent=2)}
        
        Create a comprehensive legal risk matrix with the following structure:
        
        1. CRITICAL RISKS (High Impact, High Probability)
        2. SIGNIFICANT RISKS (High Impact, Medium Probability)
        3. MODERATE RISKS (Medium Impact, Various Probabilities)
        4. MONITORING RISKS (Low Impact, Various Probabilities)
        
        For each risk, provide:
        - Risk Description
        - Potential Impact (Financial, Operational, Reputational)
        - Probability Assessment
        - Mitigation Strategies
        - Timeline for Action
        - Estimated Costs
        
        Format as a structured analysis suitable for C-suite presentation.
        """
        
        return self.call_openai_agent(risk_prompt, temperature=0.1)

    def generate_compliance_roadmap(self, brief, research_data):
        """Create actionable compliance roadmap"""
        roadmap_prompt = f"""
        As a senior partner at a top-tier law firm, create a comprehensive compliance roadmap for: "{brief}"
        
        Based on research: {json.dumps(research_data, indent=2)}
        
        Structure the roadmap as follows:
        
        ## IMMEDIATE ACTIONS (0-30 days)
        ## SHORT-TERM PRIORITIES (1-6 months)
        ## MEDIUM-TERM STRATEGIC INITIATIVES (6-18 months)
        ## LONG-TERM COMPLIANCE EVOLUTION (18+ months)
        
        For each phase, include:
        - Specific action items
        - Required resources
        - Key stakeholders
        - Success metrics
        - Budget estimates
        - Dependencies and risks
        
        Include recommendations for legal counsel specialization and estimated legal costs.
        """
        
        return self.call_openai_agent(roadmap_prompt, temperature=0.1)

    def legal_agent(self, brief):
        """Main legal analysis function delivering McKinsey-level insights"""
        
        print("🔍 Conducting comprehensive legal research...")
        
        # Gather comprehensive research
        case_research = self.get_comprehensive_case_research(brief)
        regulatory_intel = self.get_regulatory_intelligence(brief)
        international_considerations = self.get_international_considerations(brief)
        
        # Compile all research data
        research_data = {
            "case_law": case_research,
            "regulatory": regulatory_intel,
            "international": international_considerations,
            "analysis_date": datetime.now().isoformat()
        }
        
        print("📊 Generating risk assessment matrix...")
        risk_matrix = self.generate_risk_matrix(brief, research_data)
        
        print("🗺️ Creating compliance roadmap...")
        compliance_roadmap = self.generate_compliance_roadmap(brief, research_data)
        
        # Generate executive summary
        executive_summary_prompt = f"""
        As a senior legal advisor to Fortune 500 companies, create an executive summary for: "{brief}"
        
        Based on comprehensive legal research and analysis, provide:
        
        ## EXECUTIVE SUMMARY
        
        ### Key Legal Findings
        ### Critical Risk Assessment
        ### Regulatory Landscape Overview
        ### Strategic Recommendations
        ### Investment in Legal Infrastructure
        
        ## DETAILED ANALYSIS
        
        ### 1. REGULATORY COMPLIANCE FRAMEWORK
        - Federal Requirements
        - State/Local Considerations
        - Industry-Specific Regulations
        - International Implications
        
        ### 2. LEGAL RISK PROFILE
        {risk_matrix}
        
        ### 3. COMPLIANCE ROADMAP
        {compliance_roadmap}
        
        ### 4. JURISDICTIONAL ANALYSIS
        - Primary Jurisdictions of Operation
        - Conflict of Laws Considerations
        - Forum Selection Strategies
        
        ### 5. RECOMMENDED LEGAL TEAM STRUCTURE
        - Internal Counsel Requirements
        - External Counsel Specializations
        - Estimated Annual Legal Budget
        
        ### 6. COMPETITIVE LEGAL INTELLIGENCE
        - How competitors handle similar compliance issues
        - Industry best practices
        - Regulatory trend analysis
        
        Include specific citations to cases and regulations found in research.
        Format for C-suite presentation with clear action items and timelines.
        """
        
        final_analysis = self.call_openai_agent(executive_summary_prompt, temperature=0.1)
        
        # Add research citations
        citations = "\n\n## RESEARCH SOURCES\n\n"
        for source_type, sources in research_data.items():
            if source_type != "analysis_date" and sources:
                citations += f"### {source_type.title()} Sources:\n"
                for source in sources[:5]:  # Limit to top 5 per category
                    if isinstance(source, dict) and "error" not in source:
                        citations += f"- {source.get('title', source.get('case', 'Source'))}\n"
                        if source.get('url'):
                            citations += f"  📎 {source['url']}\n"
                        if source.get('snippet'):
                            citations += f"  💡 {source['snippet'][:200]}...\n"
                        citations += "\n"
        
        return final_analysis + citations

# Usage function for the main application
def legal_agent(brief):
    """Main function to be called from main.py"""
    agent = LegalAgent()
    return agent.legal_agent(brief)