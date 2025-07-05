import asyncio
import aiohttp
import concurrent.futures
from openai import OpenAI
import requests
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import time
import re
from typing import Dict, List, Tuple, Optional
from queue import Queue
import threading

load_dotenv()

class MarketingAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        self.results_queue = Queue()
        self.session = None
        
        # Streamlined industry consultancy mapping (top 3 per industry)
        self.industry_consultancies = {
            "technology": ["Gartner", "Forrester", "IDC"],
            "healthcare": ["IQVIA", "Frost & Sullivan", "McKinsey Health"],
            "financial_services": ["Oliver Wyman", "McKinsey Financial", "PwC Financial"],
            "retail": ["NRF", "Euromonitor", "McKinsey Retail"],
            "manufacturing": ["Frost & Sullivan", "Strategy&", "McKinsey Operations"],
            "energy": ["Wood Mackenzie", "S&P Global", "McKinsey Energy"],
            "automotive": ["Strategy&", "McKinsey Automotive", "BCG"],
            "real_estate": ["CBRE Research", "JLL Research", "PwC Real Estate"],
            "telecommunications": ["Analysys Mason", "Frost & Sullivan", "McKinsey TMT"],
            "cybersecurity": ["Gartner Security", "Forrester Security", "IDC Security"],
            "artificial_intelligence": ["Gartner AI", "Forrester AI", "McKinsey AI"],
            "fintech": ["CB Insights", "McKinsey Fintech", "BCG Fintech"],
            "e_commerce": ["Forrester", "Gartner", "McKinsey Retail"]
        }
        
        # Core consultancy sites
        self.consultancy_sites = {
            "McKinsey": "mckinsey.com",
            "BCG": "bcg.com",
            "Gartner": "gartner.com",
            "Forrester": "forrester.com",
            "IDC": "idc.com",
            "Frost & Sullivan": "frost.com",
            "CB Insights": "cbinsights.com",
            "Strategy&": "strategyand.pwc.com",
            "PwC": "pwc.com",
            "Deloitte": "deloitte.com"
        }
        
        # SEC EDGAR API base URL
        self.sec_base_url = "https://data.sec.gov"
        
    async def create_session(self):
        """Create async session for concurrent API calls"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=20)
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
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=1500,  # Reduced from 4000
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"OpenAI API Error: {str(e)}"
    
    def identify_industry_optimized(self, brief):
        """Streamlined industry identification"""
        industry_prompt = f"""
        Identify the primary industry for: "{brief}"
        
        Return JSON format:
        {{
            "primary_industry": "industry_name",
            "industry_keywords": ["key1", "key2", "key3"],
            "market_focus": ["market size", "growth", "competitive landscape"]
        }}
        
        Keep response concise and focused on top 3 keywords only.
        """
        
        try:
            response = self.call_openai_agent_optimized(industry_prompt, temperature=0.1)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {
                    "primary_industry": "technology",
                    "industry_keywords": ["market", "analysis", "research"],
                    "market_focus": ["market size", "growth", "competitive landscape"]
                }
        except Exception as e:
            return {
                "primary_industry": "technology",
                "industry_keywords": ["market", "analysis", "research"],
                "market_focus": ["market size", "growth", "competitive landscape"]
            }
    
    def get_top_consultancies(self, industry_data):
        """Get top 5 consultancies for the industry"""
        primary_industry = industry_data.get("primary_industry", "technology")
        consultancies = set()
        
        # Add industry-specific consultancies
        if primary_industry in self.industry_consultancies:
            consultancies.update(self.industry_consultancies[primary_industry])
        
        # Add top-tier general consultancies
        consultancies.update(["McKinsey", "BCG", "Gartner"])
        
        return list(consultancies)[:5]  # Limit to top 5
    
    async def async_market_research(self, brief, industry_data, max_results=3):
        """Async market research with reduced scope"""
        market_data = []
        
        try:
            consultancies = self.get_top_consultancies(industry_data)
            search_terms = ' '.join(industry_data.get('industry_keywords', []))
            
            session = await self.create_session()
            
            # Create 3 targeted queries instead of multiple per consultancy
            queries = [
                f"{search_terms} market size TAM billion 2024 2025",
                f"{search_terms} industry analysis growth forecast",
                f"{search_terms} competitive landscape market share"
            ]
            
            # Run queries concurrently
            tasks = []
            for query in queries:
                tasks.append(self.fetch_market_data(session, query))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    market_data.extend(result[:2])  # Top 2 per query
                    
        except Exception as e:
            market_data.append({"error": f"Market research failed: {str(e)}"})
            
        return market_data
    
    async def fetch_market_data(self, session, query):
        """Fetch market data asynchronously"""
        try:
            url = "https://serpapi.com/search"
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.serpapi_key,
                "num": 3,  # Reduced from 6
                "gl": "us",
                "hl": "en"
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []
                    
                    for item in data.get("organic_results", []):
                        snippet = item.get('snippet', '')
                        title = item.get('title', 'Market Report')
                        relevance_score = self._calculate_relevance_optimized(snippet, title)
                        
                        if relevance_score > 3:
                            results.append({
                                "source": "Market Research",
                                "title": title,
                                "url": item.get('link', ''),
                                "snippet": snippet,
                                "relevance_score": relevance_score
                            })
                    
                    return results
                    
        except Exception as e:
            return [{"error": f"Market data fetch failed: {str(e)}"}]
        
        return []
    
    def _calculate_relevance_optimized(self, snippet, title=""):
        """Simplified relevance scoring"""
        high_value_terms = ['billion', 'million', 'market size', 'TAM', 'growth rate', 'CAGR']
        text = (snippet + " " + title).lower()
        
        score = 0
        for term in high_value_terms:
            if term in text:
                score += 2
        
        # Bonus for recent content
        if any(year in text for year in ['2024', '2025', '2023']):
            score += 1
            
        return score
    
    async def async_competitive_analysis(self, brief, industry_data):
        """Streamlined competitive analysis"""
        competitive_data = []
        
        try:
            search_terms = ' '.join(industry_data.get('industry_keywords', []))
            
            if self.serpapi_key:
                session = await self.create_session()
                
                # 2 focused competitive queries
                queries = [
                    f"{search_terms} competitors market share funding",
                    f"{search_terms} competitive analysis industry leaders"
                ]
                
                tasks = []
                for query in queries:
                    tasks.append(self.fetch_competitive_data(session, query))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, list):
                        competitive_data.extend(result[:2])
                        
        except Exception as e:
            competitive_data.append({"error": f"Competitive analysis failed: {str(e)}"})
            
        return competitive_data
    
    async def fetch_competitive_data(self, session, query):
        """Fetch competitive data asynchronously"""
        try:
            url = "https://serpapi.com/search"
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.serpapi_key,
                "num": 3,
                "gl": "us",
                "hl": "en"
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []
                    
                    for item in data.get("organic_results", []):
                        results.append({
                            "source": "Competitive Intelligence",
                            "title": item.get('title', 'Competitive Analysis'),
                            "url": item.get('link', ''),
                            "snippet": item.get('snippet', ''),
                            "relevance_score": 5  # Simplified scoring
                        })
                    
                    return results
                    
        except Exception as e:
            return [{"error": f"Competitive data fetch failed: {str(e)}"}]
        
        return []
    
    def get_top_public_companies_optimized(self, brief, industry_data):
        """Get top 3 public companies for SEC analysis"""
        company_prompt = f"""
        Identify the top 3 public companies most relevant to: "{brief}"
        Industry: {industry_data.get('primary_industry', 'technology')}
        
        Return JSON array:
        [
            {{"company": "Company Name", "ticker": "TICKER"}},
            {{"company": "Company Name", "ticker": "TICKER"}},
            {{"company": "Company Name", "ticker": "TICKER"}}
        ]
        
        Focus on largest, most established companies only.
        """
        
        try:
            response = self.call_openai_agent_optimized(company_prompt, temperature=0.1)
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return []
        except Exception as e:
            return []
    
    async def async_sec_analysis(self, brief, industry_data):
        """Streamlined SEC analysis"""
        sec_insights = []
        
        try:
            companies = self.get_top_public_companies_optimized(brief, industry_data)
            
            if companies:
                session = await self.create_session()
                
                # Limit to top 2 companies for faster processing
                tasks = []
                for company in companies[:2]:
                    tasks.append(self.fetch_sec_data(session, company))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, dict) and "error" not in result:
                        sec_insights.append(result)
                        
        except Exception as e:
            sec_insights.append({"error": f"SEC analysis failed: {str(e)}"})
            
        return sec_insights
    
    async def fetch_sec_data(self, session, company):
        """Fetch SEC data asynchronously"""
        try:
            ticker = company.get('ticker', '').upper()
            company_name = company.get('company', '')
            
            # Get company tickers
            tickers_url = f"{self.sec_base_url}/files/company_tickers.json"
            headers = {
                'User-Agent': 'MarketingAgent/1.0 (contact@yourcompany.com)',
                'Accept-Encoding': 'gzip, deflate'
            }
            
            async with session.get(tickers_url, headers=headers) as response:
                if response.status == 200:
                    tickers_data = await response.json()
                    cik = None
                    
                    # Find CIK
                    for key, value in tickers_data.items():
                        if value.get('ticker') == ticker:
                            cik = str(value.get('cik_str')).zfill(10)
                            break
                    
                    if cik:
                        # Get recent filings
                        submissions_url = f"{self.sec_base_url}/submissions/CIK{cik}.json"
                        async with session.get(submissions_url, headers=headers) as sub_response:
                            if sub_response.status == 200:
                                filing_data = await sub_response.json()
                                
                                return {
                                    "source": "SEC Analysis",
                                    "company": company_name,
                                    "ticker": ticker,
                                    "industry": filing_data.get('sicDescription', 'Unknown'),
                                    "business_description": filing_data.get('description', 'No description')[:300],
                                    "relevance_score": 9
                                }
                                
        except Exception as e:
            return {"error": f"SEC fetch failed for {company.get('ticker', 'Unknown')}: {str(e)}"}
        
        return {"error": "No data found"}
    
    def generate_streaming_analysis(self, brief, research_data, progress_callback=None):
        """Generate analysis with streaming updates"""
        
        # Step 1: Market analysis
        if progress_callback:
            progress_callback("Analyzing market data...", 0.4)
            
        market_analysis = self.generate_market_analysis_optimized(brief, research_data)
        
        # Step 2: Competitive intelligence
        if progress_callback:
            progress_callback("Processing competitive intelligence...", 0.7)
            
        competitive_analysis = self.generate_competitive_analysis_optimized(brief, research_data)
        
        # Step 3: Executive summary
        if progress_callback:
            progress_callback("Generating executive summary...", 0.9)
            
        executive_summary = self.generate_executive_summary_optimized(brief, market_analysis, competitive_analysis)
        
        return {
            "market_analysis": market_analysis,
            "competitive_analysis": competitive_analysis,
            "executive_summary": executive_summary
        }
    
    def generate_market_analysis_optimized(self, brief, research_data):
        """Optimized market analysis generation"""
        market_prompt = f"""
        Based on: "{brief}"
        
        Create focused market analysis:
        
        ## MARKET OPPORTUNITY
        - Market Size (TAM/SAM/SOM estimates)
        - Growth Rate & Trends
        - Key Market Drivers
        
        ## TARGET MARKET
        - Primary Customer Segments
        - Market Entry Strategy
        - Revenue Potential
        
        Keep response under 1000 words. Focus on actionable insights.
        """
        
        return self.call_openai_agent_optimized(market_prompt, temperature=0.1)
    
    def generate_competitive_analysis_optimized(self, brief, research_data):
        """Optimized competitive analysis"""
        competitive_prompt = f"""
        Create competitive analysis for: "{brief}"
        
        ## COMPETITIVE LANDSCAPE
        - Top 3 Direct Competitors
        - Competitive Advantages/Disadvantages
        - Market Positioning
        
        ## STRATEGIC RECOMMENDATIONS
        - Differentiation Strategy
        - Competitive Response
        - Market Entry Tactics
        
        Keep response under 1000 words. Focus on strategic insights.
        """
        
        return self.call_openai_agent_optimized(competitive_prompt, temperature=0.1)
    
    def generate_executive_summary_optimized(self, brief, market_analysis, competitive_analysis):
        """Optimized executive summary"""
        summary_prompt = f"""
        Create executive summary for: "{brief}"
        
        ## EXECUTIVE SUMMARY
        ### Key Market Opportunity
        ### Competitive Position
        ### Strategic Recommendations
        
        ## DETAILED ANALYSIS
        
        ### Market Analysis
        {market_analysis}
        
        ### Competitive Analysis
        {competitive_analysis}
        
        Keep total response under 1500 words. Focus on actionable insights.
        """
        
        return self.call_openai_agent_optimized(summary_prompt, temperature=0.1)
    
    async def marketing_agent_optimized(self, brief, progress_callback=None):
        """Optimized main marketing analysis function"""
        
        if progress_callback:
            progress_callback("Starting market research...", 0.1)
        
        # Step 1: Industry identification
        industry_data = self.identify_industry_optimized(brief)
        
        if progress_callback:
            progress_callback("Gathering market intelligence...", 0.2)
        
        # Step 2: Run research concurrently
        research_tasks = [
            self.async_market_research(brief, industry_data),
            self.async_competitive_analysis(brief, industry_data),
            self.async_sec_analysis(brief, industry_data)
        ]
        
        market_research, competitive_intel, sec_analysis = await asyncio.gather(*research_tasks)
        
        # Compile research data
        research_data = {
            "market_research": market_research,
            "competitive_intel": competitive_intel,
            "sec_analysis": sec_analysis,
            "industry_data": industry_data,
            "analysis_date": datetime.now().isoformat()
        }
        
        if progress_callback:
            progress_callback("Analyzing research data...", 0.3)
        
        # Generate analysis with streaming updates
        analysis_results = self.generate_streaming_analysis(brief, research_data, progress_callback)
        
        # Compile final results
        final_analysis = analysis_results["executive_summary"]
        
        # Add simplified citations
        citations = "\n\n## KEY SOURCES\n\n"
        source_count = 0
        
        for source_type, sources in research_data.items():
            if source_type not in ["analysis_date", "industry_data"] and sources:
                citations += f"### {source_type.replace('_', ' ').title()}:\n"
                for source in sources[:2]:  # Limit to top 2
                    if isinstance(source, dict) and "error" not in source:
                        citations += f"- {source.get('title', source.get('company', 'Source'))}\n"
                        if source.get('url'):
                            citations += f"  📎 {source['url']}\n"
                        source_count += 1
        
        citations += f"\n**Total Sources Analyzed:** {source_count}\n"
        citations += f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        # Close session
        await self.close_session()
        
        if progress_callback:
            progress_callback("Analysis complete!", 1.0)
        
        return final_analysis + citations

# Integration functions
def run_optimized_marketing_analysis(brief, progress_callback=None):
    """Run optimized marketing analysis with progress updates"""
    agent = MarketingAgent()
    return asyncio.run(agent.marketing_agent_optimized(brief, progress_callback))

def marketing_agent(brief):
    return run_optimized_marketing_analysis(brief)
     
# def marketing_agent(brief: str):
#     agent = MarketingAgent()
#     report_dict = agent.generate_comprehensive_report(brief)
#     if brief.find("- Output Format: Detailed Report") != -1:
#         formatted_report = f"""{report_dict.get('comprehensive_analysis', 'Comprehensive analysis not available')}"""
#     else:
#         formatted_report = f"""{report_dict.get('executive_summary', 'Executive summary not available')}"""
#     formatted_report += f"""

#         **Analysis Date:** {report_dict.get('research_metadata', {}).get('analysis_date', 'Not available')}

#         **Industry Classification:** {report_dict.get('research_metadata', {}).get('industry_classification', {}).get('primary_industry', 'Not specified')}

#         **Total Sources Analyzed:** {report_dict.get('research_metadata', {}).get('total_sources', 0)}

#         ### Data Sources Breakdown:
#         """
    
#     # Add data sources breakdown
#     data_sources = report_dict.get('research_metadata', {}).get('data_sources_analyzed', {})
#     for source_type, count in data_sources.items():
#         formatted_report += f"- **{source_type.replace('_', ' ').title()}:** {count} sources\n"
    
#     # Add data source summary if available
#     data_source_summary = report_dict.get('data_source_summary', {})
#     if data_source_summary:
#         formatted_report += f"\n### 🔍 DATA SOURCE QUALITY ASSESSMENT\n"
        
#         high_cred_sources = len(data_source_summary.get('high_credibility_sources', []))
#         sec_sources = len(data_source_summary.get('sec_filing_sources', []))
#         quant_sources = len(data_source_summary.get('quantitative_data_sources', []))
#         recent_sources = len(data_source_summary.get('recent_sources', []))
        
#         formatted_report += f"- **High Credibility Sources:** {high_cred_sources}\n"
#         formatted_report += f"- **SEC Filing Sources:** {sec_sources}\n"
#         formatted_report += f"- **Quantitative Data Sources:** {quant_sources}\n"
#         formatted_report += f"- **Recent Sources (2024-2025):** {recent_sources}\n"
    
#     formatted_report += f"""

#             This comprehensive analysis leverages {report_dict.get('research_metadata', {}).get('total_sources', 0)} data sources including:
#             - Industry-specific consultancy reports
#             - SEC filing analysis from relevant public companies
#             - Competitive intelligence and market research
#             - Macro trend analysis and regulatory insights
#             - Investment and funding landscape analysis

#             **Recommended Next Steps:**
#             1. Review the executive summary for immediate strategic priorities
#             2. Analyze the competitive positioning recommendations
#             3. Evaluate the market sizing and revenue opportunity
#             4. Consider the regulatory and compliance requirements
#             5. Develop implementation roadmap based on strategic recommendations

#             ---

#             *This report was generated using advanced AI-powered market research and analysis. The insights are based on publicly available data and should be validated with additional primary research as needed.*
#             """
#     return formatted_report

