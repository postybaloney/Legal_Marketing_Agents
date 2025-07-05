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
        self.data_sources = []
        self.results_queue = Queue()
        self.session = None
        
        # Industry-specific consultancy mapping
        self.industry_consultancies = {
            "technology": ["Gartner", "Forrester", "IDC", "McKinsey Digital", "Accenture", "Deloitte Tech"],
            "healthcare": ["IQVIA", "Frost & Sullivan", "Grand View Research", "McKinsey Health", "BCG Health"],
            "financial_services": ["Oliver Wyman", "Aite Group", "Celent", "McKinsey Financial", "PwC Financial"],
            "retail": ["Retail Industry Leaders", "NRF", "Euromonitor", "Mintel", "BCG Retail"],
            "manufacturing": ["Frost & Sullivan", "Roland Berger", "Strategy&", "McKinsey Operations"],
            "energy": ["Wood Mackenzie", "IHS Markit", "S&P Global", "McKinsey Energy", "BCG Energy"],
            "automotive": ["IHS Automotive", "Strategy&", "AlixPartners", "McKinsey Automotive"],
            "aerospace": ["Teal Group", "Frost & Sullivan", "Strategy&", "Roland Berger"],
            "real_estate": ["CBRE Research", "JLL Research", "PwC Real Estate", "McKinsey Capital Projects"],
            "telecommunications": ["Analysys Mason", "Ovum", "Frost & Sullivan", "McKinsey TMT"],
            "media": ["PwC Entertainment", "Deloitte TMT", "Strategy& Media", "McKinsey Media"],
            "chemicals": ["IHS Chemical", "Frost & Sullivan", "Strategy&", "McKinsey Chemicals"],
            "agriculture": ["Rabobank", "McKinsey Agriculture", "Frost & Sullivan", "Strategy&"],
            "logistics": ["Armstrong & Associates", "Frost & Sullivan", "Strategy&", "McKinsey Travel Transport"],
            "education": ["HolonIQ", "Frost & Sullivan", "Tyton Partners", "McKinsey Education"],
            "cybersecurity": ["Gartner Security", "Forrester Security", "IDC Security", "Frost & Sullivan"],
            "artificial_intelligence": ["Gartner AI", "Forrester AI", "IDC AI", "McKinsey AI", "BCG AI"],
            "fintech": ["CB Insights", "Frost & Sullivan", "McKinsey Fintech", "BCG Fintech"],
            "biotechnology": ["Frost & Sullivan", "Grand View Research", "McKinsey Pharma", "BCG Biopharma"],
            "e_commerce": ["Forrester", "Gartner", "McKinsey Retail", "BCG Digital Commerce"]
        }
        
        # SEC EDGAR API base URL
        self.sec_base_url = "https://data.sec.gov"
        
        # Enhanced consultancy site mapping for better search targeting
        self.consultancy_sites = {
            "McKinsey": "mckinsey.com",
            "BCG": "bcg.com",
            "Bain": "bain.com",
            "Deloitte": "deloitte.com",
            "PwC": "pwc.com",
            "Accenture": "accenture.com",
            "Gartner": "gartner.com",
            "Forrester": "forrester.com",
            "IDC": "idc.com",
            "Frost & Sullivan": "frost.com",
            "Grand View Research": "grandviewresearch.com",
            "Oliver Wyman": "oliverwyman.com",
            "Strategy&": "strategyand.pwc.com",
            "Roland Berger": "rolandberger.com",
            "IQVIA": "iqvia.com",
            "Wood Mackenzie": "woodmac.com",
            "IHS Markit": "ihsmarkit.com",
            "S&P Global": "spglobal.com",
            "CB Insights": "cbinsights.com",
            "Euromonitor": "euromonitor.com",
            "Mintel": "mintel.com",
            "NRF": "nrf.com",
            "CBRE Research": "cbre.com",
            "JLL Research": "jll.com",
            "Analysys Mason": "analysysmason.com",
            "Ovum": "ovum.com",
            "Teal Group": "tealgroup.com",
            "AlixPartners": "alixpartners.com",
            "Armstrong & Associates": "3plogistics.com",
            "HolonIQ": "holoniq.com",
            "Tyton Partners": "tytonpartners.com",
            "Aite Group": "aitegroup.com",
            "Celent": "celent.com",
            "Rabobank": "rabobank.com"
        }

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
        
    def call_openai_agent(self, prompt, temperature=0.2, model="gpt-4o-mini"):
        """Optimized OpenAI API call with timeout"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=2000,  # Reduced for faster response
                timeout=15  # 15 second timeout
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"OpenAI API Error: {str(e)}"
    
    def identify_industry_and_consultancies(self, brief):
        """Identify industry and select relevant consultancies"""
        industry_prompt = f"""
        Analyze this business brief and identify the primary industry: "{brief}"
        
        Return your response in this exact JSON format:
        {{
            "primary_industry": "one of: technology, healthcare, financial_services, retail, manufacturing, energy, automotive, aerospace, real_estate, telecommunications, media, chemicals, agriculture, logistics, education, cybersecurity, artificial_intelligence, fintech, biotechnology, e_commerce",
            "secondary_industries": ["list of 1-2 secondary industries"],
            "industry_keywords": ["5-10 specific industry keywords for research"],
            "naics_codes": ["relevant NAICS codes if identifiable"],
            "market_research_focus": ["3-5 specific market research topics to focus on"]
        }}
        """
        
        try:
            response = self.call_openai_agent(industry_prompt, temperature=0.1)
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                industry_data = json.loads(json_match.group())
                return industry_data
            else:
                # Fallback
                return {
                    "primary_industry": "technology",
                    "secondary_industries": [],
                    "industry_keywords": ["market", "analysis", "research"],
                    "naics_codes": [],
                    "market_research_focus": ["market size", "competitive landscape", "growth trends"]
                }
        except Exception as e:
            print(f"Industry identification error: {e}")
            return {
                "primary_industry": "technology",
                "secondary_industries": [],
                "industry_keywords": ["market", "analysis", "research"],
                "naics_codes": [],
                "market_research_focus": ["market size", "competitive landscape", "growth trends"]
            }
    
    def get_industry_specific_consultancies(self, industry_data):
        """Get consultancies specific to the identified industry"""
        primary_industry = industry_data.get("primary_industry", "technology")
        secondary_industries = industry_data.get("secondary_industries", [])
        
        consultancies = set()
        
        # Add primary industry consultancies
        if primary_industry in self.industry_consultancies:
            consultancies.update(self.industry_consultancies[primary_industry])
        
        # Add secondary industry consultancies
        for secondary in secondary_industries:
            if secondary in self.industry_consultancies:
                consultancies.update(self.industry_consultancies[secondary][:3])  # Top 3 from secondary
        
        # Always include top-tier general consultancies
        consultancies.update(["McKinsey", "BCG", "Bain", "Deloitte", "PwC", "Accenture"])
        
        return list(consultancies)
    
    async def async_market_research(self, brief, industry_data, max_results=3):
            """Async market research with reduced scope"""
            market_data = []
            
            try:
                consultancies = self.get_industry_specific_consultancies(industry_data)
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

    def get_relevant_public_companies(self, brief, industry_data):
        """Identify relevant public companies for SEC filing analysis"""
        company_prompt = f"""
        Based on this business brief: "{brief}"
        And industry classification: {json.dumps(industry_data)}
        
        Identify 12-15 relevant public companies that would be:
        1. Direct competitors (same business model/market)
        2. Companies in the same industry vertical
        3. Companies with similar customer segments
        4. Technology/service providers in the ecosystem
        5. Potential partners or acquisition targets
        
        Return company names and ticker symbols in this format:
        [
            {{"company": "Company Name", "ticker": "SYMBOL", "relevance": "direct_competitor|industry_peer|similar_model|strategic_partner|ecosystem_player", "market_cap_tier": "large_cap|mid_cap|small_cap"}},
            ...
        ]
        
        Focus on companies that would have meaningful market data, competitive intelligence, 
        and industry insights in their 10-K/10-Q filings.
        """
        
        try:
            response = self.call_openai_agent(company_prompt, temperature=0.1)
            # Extract JSON array from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                companies = json.loads(json_match.group())
                return companies
            else:
                return []
        except Exception as e:
            print(f"Company identification error: {e}")
            return []
    
    def search_sec_filings(self, companies, industry_keywords):
        """Enhanced SEC filing search with better error handling and data extraction"""
        sec_data = []
        
        # Set proper headers for SEC API
        headers = {
            'User-Agent': 'MarketingAgent/1.0 (contact@yourcompany.com)',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'data.sec.gov'
        }
        
        for company in companies[:10]:  # Limit to top 10 companies
            ticker = company.get('ticker', '').upper()
            company_name = company.get('company', '')
            
            try:
                # First, try to get company information by ticker
                company_tickers_url = f"{self.sec_base_url}/files/company_tickers.json"
                tickers_response = requests.get(company_tickers_url, headers=headers)
                
                if tickers_response.status_code == 200:
                    tickers_data = tickers_response.json()
                    cik = None
                    
                    # Find CIK for the ticker
                    for key, value in tickers_data.items():
                        if value.get('ticker') == ticker:
                            cik = str(value.get('cik_str')).zfill(10)
                            break
                    
                    if cik:
                        # Get company submissions
                        submissions_url = f"{self.sec_base_url}/submissions/CIK{cik}.json"
                        submissions_response = requests.get(submissions_url, headers=headers)
                        
                        if submissions_response.status_code == 200:
                            filing_data = submissions_response.json()
                            
                            # Get recent 10-K and 10-Q filings
                            recent_filings = []
                            forms = filing_data.get('filings', {}).get('recent', {})
                            
                            if forms:
                                form_list = forms.get('form', [])
                                filing_dates = forms.get('filingDate', [])
                                accession_numbers = forms.get('accessionNumber', [])
                                primary_docs = forms.get('primaryDocument', [])
                                
                                for i, form in enumerate(form_list):
                                    if form in ['10-K', '10-Q'] and len(recent_filings) < 4:
                                        filing_info = {
                                            'form': form,
                                            'filingDate': filing_dates[i] if i < len(filing_dates) else 'Unknown',
                                            'accessionNumber': accession_numbers[i] if i < len(accession_numbers) else 'Unknown',
                                            'primaryDocument': primary_docs[i] if i < len(primary_docs) else 'Unknown'
                                        }
                                        recent_filings.append(filing_info)
                            
                            sec_data.append({
                                'company': company_name,
                                'ticker': ticker,
                                'cik': cik,
                                'recent_filings': recent_filings,
                                'sic': filing_data.get('sic', 'Unknown'),
                                'sicDescription': filing_data.get('sicDescription', 'Unknown'),
                                'industry': filing_data.get('sicDescription', 'Unknown'),
                                'relevance': company.get('relevance', 'unknown'),
                                'market_cap_tier': company.get('market_cap_tier', 'unknown'),
                                'business_description': filing_data.get('description', 'No description available')
                            })
                
                # Rate limiting to respect SEC API limits
                time.sleep(0.1)
                
            except Exception as e:
                print(f"SEC filing search error for {ticker}: {e}")
                continue
        
        return sec_data
    
    def analyze_sec_filing_content(self, sec_data, industry_keywords, brief):
        """Enhanced SEC filing analysis with market intelligence extraction"""
        market_insights = []
        
        for company_data in sec_data:
            company = company_data.get('company', '')
            ticker = company_data.get('ticker', '')
            business_desc = company_data.get('business_description', '')
            
            # Analyze filing metadata and extract insights
            filing_analysis = {
                'company': company,
                'ticker': ticker,
                'market_insights': [],
                'competitive_intelligence': [],
                'financial_benchmarks': [],
                'risk_factors': [],
                'growth_strategies': [],
                'market_size_references': []
            }
            
            # Create comprehensive analysis of available data
            recent_filings = company_data.get('recent_filings', [])
            if recent_filings:
                filing_summary = f"SEC Filing Analysis for {company} ({ticker}):\n"
                filing_summary += f"Industry: {company_data.get('sicDescription', 'Unknown')}\n"
                filing_summary += f"Business Description: {business_desc[:500]}...\n"
                filing_summary += f"Recent Filings:\n"
                
                for filing in recent_filings:
                    filing_summary += f"- {filing['form']} filed on {filing['filingDate']}\n"
                
                # Market intelligence extraction prompt
                market_intelligence_prompt = f"""
                As a senior equity research analyst, analyze this SEC filing information for {company} ({ticker}):
                
                {filing_summary}
                
                Target Business Context: {brief}
                Industry Keywords: {', '.join(industry_keywords)}
                Company Relevance: {company_data.get('relevance', 'unknown')}
                Market Cap Tier: {company_data.get('market_cap_tier', 'unknown')}
                
                Extract specific market intelligence that would be valuable for competitive analysis:
                
                1. **Market Size and Opportunity References**
                   - TAM/SAM mentions or market sizing data
                   - Growth rate projections and market forecasts
                   - Market share positions and competitive positioning
                
                2. **Competitive Landscape Intelligence**
                   - Direct and indirect competitors mentioned
                   - Competitive advantages and differentiation factors
                   - Market consolidation trends and M&A activity
                
                3. **Financial Performance Benchmarks**
                   - Revenue growth rates and margin trends
                   - R&D investment levels and innovation focus
                   - Customer acquisition and retention metrics
                
                4. **Strategic Initiatives and Investments**
                   - Technology investments and digital transformation
                   - Geographic expansion and market entry strategies
                   - Partnership and acquisition strategies
                
                5. **Risk Factors and Market Challenges**
                   - Industry-specific risks and regulatory challenges
                   - Competitive threats and market disruptions
                   - Economic and market condition impacts
                
                6. **Customer and Market Trends**
                   - Customer segment analysis and behavior trends
                   - Market demand drivers and adoption patterns
                   - Pricing trends and customer willingness to pay
                
                Provide specific, actionable insights that would inform strategic decision-making.
                Focus on quantitative data and specific market intelligence.
                """
                
                market_intelligence = self.call_openai_agent(market_intelligence_prompt, temperature=0.2)
                
                # Additional competitive positioning analysis
                competitive_positioning_prompt = f"""
                Based on the SEC filing data for {company} ({ticker}), provide a competitive positioning analysis:
                
                {filing_summary}
                
                Focus on:
                1. Competitive moats and sustainable advantages
                2. Market positioning vs. industry peers
                3. Strategic vulnerabilities and competitive threats
                4. Innovation and technology leadership indicators
                5. Financial strength and resource advantages
                
                Provide 3-5 key strategic insights that would be valuable for competitive analysis.
                """
                
                competitive_positioning = self.call_openai_agent(competitive_positioning_prompt, temperature=0.2)
                
                filing_analysis['market_insights'] = market_intelligence
                filing_analysis['competitive_intelligence'] = competitive_positioning
                
                # Extract financial benchmarks
                financial_benchmark_prompt = f"""
                Extract key financial benchmarks from {company} ({ticker}) SEC filing data:
                
                {filing_summary}
                
                Provide specific metrics that would be useful for financial modeling:
                - Revenue growth rates (historical and projected)
                - Gross margin trends and drivers
                - Operating margin and scalability indicators
                - R&D spending as % of revenue
                - Sales & marketing efficiency metrics
                - Customer acquisition cost trends
                - Working capital and cash flow patterns
                
                Focus on quantitative metrics that can be used for benchmarking.
                """
                
                financial_benchmarks = self.call_openai_agent(financial_benchmark_prompt, temperature=0.1)
                filing_analysis['financial_benchmarks'] = financial_benchmarks
            
            market_insights.append(filing_analysis)
        
        return market_insights
    
    def get_tam_sam_som_analysis(self, brief):
        """Enhanced TAM/SAM/SOM analysis with industry-specific consultancies and SEC data"""
        print("🔍 Identifying industry and relevant consultancies...")
        
        # Identify industry and get specific consultancies
        industry_data = self.identify_industry_and_consultancies(brief)
        consultancies = self.get_industry_specific_consultancies(industry_data)
        
        print(f"📊 Focusing on {industry_data['primary_industry']} industry with {len(consultancies)} specialized consultancies...")
        
        market_data = []
        
        # Industry-specific market research from consultancies
        try:
            if self.serpapi_key:
                # Search each relevant consultancy with targeted queries
                for consultancy in consultancies:
                    # Get consultancy website domain
                    site_domain = self.consultancy_sites.get(consultancy, consultancy.lower().replace(' ', '').replace('&', '') + '.com')
                    
                    # Create targeted search queries for each consultancy
                    search_terms = ' '.join(industry_data.get('industry_keywords', []))
                    market_focus_terms = ' '.join(industry_data.get('market_research_focus', []))
                    
                    # Multiple targeted queries per consultancy
                    consultancy_queries = [
                        f"site:{site_domain} {search_terms} market size TAM SAM billion 2024 2025",
                        f"site:{site_domain} {search_terms} industry analysis market forecast CAGR",
                        f"site:{site_domain} {market_focus_terms} competitive landscape market share",
                        f"site:{site_domain} {search_terms} market opportunity addressable market revenue"
                    ]
                    
                    for query in consultancy_queries:
                        consultancy_data = self._search_data_source(query, consultancy)
                        market_data.extend(consultancy_data[:2])  # Top 2 results per query
                
                # Add specialized industry research with broader sources
                broader_industry_queries = [
                    f"{' '.join(industry_data.get('industry_keywords', []))} market size billion TAM SAM SOM 2024 2025",
                    f"{industry_data.get('primary_industry')} industry analysis market forecast growth rate",
                    f"{' '.join(industry_data.get('market_research_focus', []))} market research report industry outlook"
                ]
                
                for query in broader_industry_queries:
                    market_data.extend(self._search_data_source(query, "Industry Research"))
                
        except Exception as e:
            market_data.append({"error": f"Market research failed: {str(e)}"})
        
        # SEC filing analysis for market intelligence
        print("📋 Analyzing SEC filings for market intelligence...")
        try:
            relevant_companies = self.get_relevant_public_companies(brief, industry_data)
            if relevant_companies:
                sec_data = self.search_sec_filings(relevant_companies, industry_data.get('industry_keywords', []))
                sec_insights = self.analyze_sec_filing_content(sec_data, industry_data.get('industry_keywords', []), brief)
                
                # Add SEC insights to market data
                for insight in sec_insights:
                    market_data.append({
                        "source": "SEC Filings Analysis",
                        "company": insight['company'],
                        "ticker": insight['ticker'],
                        "market_insights": insight['market_insights'],
                        "competitive_intelligence": insight['competitive_intelligence'],
                        "financial_benchmarks": insight['financial_benchmarks'],
                        "relevance_score": 9,  # High relevance for SEC data
                        "data_type": "Primary Financial Data",
                        "analysis_depth": "Comprehensive"
                    })
        except Exception as e:
            market_data.append({"error": f"SEC analysis failed: {str(e)}"})
        
        return market_data, industry_data
    
    def _search_data_source(self, query, source_type):
        """Enhanced helper function to search specific data sources"""
        results = []
        try:
            url = "https://serpapi.com/search"
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.serpapi_key,
                "num": 6,
                "gl": "us",
                "hl": "en"
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                
                for item in data.get("organic_results", []):
                    snippet = item.get('snippet', '')
                    title = item.get('title', 'Unnamed Report')
                    
                    # Enhanced relevance scoring
                    relevance_score = self._calculate_relevance(snippet, source_type, title)
                    
                    if relevance_score > 3:  # Only include high-relevance results
                        results.append({
                            "source": source_type,
                            "title": title,
                            "url": item.get('link', ''),
                            "snippet": snippet,
                            "relevance_score": relevance_score,
                            "publication_indicators": self._extract_publication_indicators(snippet),
                            "data_quality": self._assess_data_quality(snippet, source_type)
                        })
                
                # Also check for featured snippets and knowledge panels
                if "answer_box" in data:
                    answer_box = data["answer_box"]
                    results.append({
                        "source": f"{source_type} (Featured)",
                        "title": answer_box.get("title", "Featured Answer"),
                        "url": answer_box.get("link", ""),
                        "snippet": answer_box.get("snippet", ""),
                        "relevance_score": 10,
                        "data_type": "Featured Answer",
                        "data_quality": "High"
                    })
                
        except Exception as e:
            results.append({"error": f"{source_type} search failed: {str(e)}"})
            
        return results

    def _calculate_relevance(self, snippet, source_type, title=""):
        """Enhanced relevance scoring with source type weighting"""
        # High-value indicators
        high_value_indicators = ['billion', 'trillion', 'market size', 'TAM', 'SAM', 'SOM', 'addressable market']
        medium_value_indicators = ['million', 'growth rate', 'CAGR', 'forecast', 'projected', 'market share']
        low_value_indicators = ['revenue', 'industry', 'analysis', 'report', 'research', 'study']
        
        # Calculate base score
        base_score = 0
        text_to_analyze = (snippet + " " + title).lower()
        
        for indicator in high_value_indicators:
            if indicator.lower() in text_to_analyze:
                base_score += 3
        
        for indicator in medium_value_indicators:
            if indicator.lower() in text_to_analyze:
                base_score += 2
        
        for indicator in low_value_indicators:
            if indicator.lower() in text_to_analyze:
                base_score += 1
        
        # Weight by source credibility
        source_weights = {
            'Gartner': 1.8, 'Forrester': 1.8, 'IDC': 1.6,
            'McKinsey': 1.7, 'BCG': 1.7, 'Bain': 1.7,
            'Deloitte': 1.5, 'PwC': 1.5, 'Accenture': 1.5,
            'SEC Filings': 1.9, 'SEC Filings Analysis': 1.9,
            'Frost & Sullivan': 1.4, 'Grand View Research': 1.3,
            'Oliver Wyman': 1.4, 'Strategy&': 1.4, 'Roland Berger': 1.3,
            'IQVIA': 1.6, 'Wood Mackenzie': 1.5, 'IHS Markit': 1.5,
            'CB Insights': 1.4, 'Euromonitor': 1.3, 'Mintel': 1.3
        }
        
        weight = source_weights.get(source_type, 1.0)
        final_score = int(base_score * weight)
        
        # Bonus for recent content
        if any(year in text_to_analyze for year in ['2024', '2025', '2023']):
            final_score += 1
        
        return final_score
    
    def _extract_publication_indicators(self, snippet):
        """Extract publication date and credibility indicators"""
        indicators = {
            'has_date': bool(re.search(r'\b(2024|2025|2023)\b', snippet)),
            'has_numbers': bool(re.search(r'\$?\d+\.?\d*\s*(billion|million|trillion)', snippet, re.IGNORECASE)),
            'has_forecast': bool(re.search(r'\b(forecast|projected|expected|estimated)\b', snippet, re.IGNORECASE)),
            'has_growth': bool(re.search(r'\b(growth|CAGR|increase|expand)\b', snippet, re.IGNORECASE))
        }
        return indicators
    
    def _assess_data_quality(self, snippet, source_type):
        """Assess the quality of data from the snippet"""
        quality_score = 0
        
        # Check for quantitative data
        if re.search(r'\$?\d+\.?\d*\s*(billion|million|trillion)', snippet, re.IGNORECASE):
            quality_score += 2
        
        # Check for time-bound data
        if re.search(r'\b(2024|2025|2023)\b', snippet):
            quality_score += 1
        
        # Check for methodology indicators
        if re.search(r'\b(survey|analysis|research|study|report)\b', snippet, re.IGNORECASE):
            quality_score += 1
        
        # Source credibility bonus
        if source_type in ['Gartner', 'Forrester', 'McKinsey', 'BCG', 'SEC Filings']:
            quality_score += 2
        
        if quality_score >= 4:
            return "High"
        elif quality_score >= 2:
            return "Medium"
        else:
            return "Low"
    
    def get_competitive_intelligence(self, brief, industry_data=None):
        """Enhanced competitive analysis with industry focus"""
        competitive_data = []
        
        # Use industry-specific keywords for better targeting
        industry_keywords = industry_data.get('industry_keywords', []) if industry_data else []
        search_terms = ' '.join(industry_keywords) if industry_keywords else brief
        
        # Identify key competitors with industry context
        competitor_query = self.call_openai_agent(
            f"Identify the top 12 competitors for: {brief}. "
            f"Industry context: {industry_data.get('primary_industry', 'general') if industry_data else 'general'}. "
            f"Focus on: Direct Competitors, Indirect Competitors, Substitute Threats, New Entrants, Industry Disruptors. "
            f"Include both established players and emerging companies."
        )
        
        try:
            if self.serpapi_key:
                # Enhanced competitive research queries
                queries = [
                    f"{search_terms} competitors funding investment Series A B C IPO",
                    f"{search_terms} industry partnerships acquisitions M&A strategic alliances",
                    f"{search_terms} technology innovation patents R&D investments",
                    f"{search_terms} market share leaders competitive positioning",
                    f"{search_terms} competitive analysis Porter five forces",
                    f"{search_terms} industry consolidation market dynamics"
                ]
                
                for query in queries:
                    competitive_data.extend(self._search_data_source(query, "Competitive Intelligence"))
                
        except Exception as e:
            competitive_data.append({"error": f"Competitive intelligence failed: {str(e)}"})
            
        return competitive_data
    
    def get_macro_trend_analysis(self, brief, industry_data=None):
        """Enhanced macro trend analysis with industry-specific focus"""
        trend_data = []
        
        industry_keywords = industry_data.get('industry_keywords', []) if industry_data else []
        search_terms = ' '.join(industry_keywords) if industry_keywords else brief
        primary_industry = industry_data.get('primary_industry', 'general') if industry_data else 'general'
        
        try:
            if self.serpapi_key:
                # Industry-specific trend queries
                trend_queries = [
                    f"{search_terms} emerging trends 2024 2025 future outlook digital transformation",
                    f"{primary_industry} industry trends technology adoption automation AI",
                    f"{search_terms} regulatory changes compliance requirements government policy",
                    f"{search_terms} consumer behavior shifts demographic trends millennial GenZ",
                    f"{search_terms} sustainability ESG environmental social governance trends",
                    f"{search_terms} economic outlook inflation interest rates recession recovery",
                    f"{search_terms} supply chain disruption globalization reshoring trends",
                    f"{search_terms} cybersecurity threats data privacy regulations",
                    f"{search_terms} remote work hybrid workplace future of work trends",
                    f"{search_terms} investment trends venture capital private equity funding"
                ]
                
                for query in trend_queries:
                    trend_data.extend(self._search_data_source(query, "Macro Trend Analysis"))
                
                # Add specialized consultancy trend reports
                consultancy_trend_queries = [
                    f"site:mckinsey.com {search_terms} trends report outlook 2024 2025",
                    f"site:bcg.com {search_terms} industry transformation digital trends",
                    f"site:deloitte.com {search_terms} tech trends future outlook",
                    f"site:pwc.com {search_terms} global trends CEO survey outlook",
                    f"site:accenture.com {search_terms} technology trends innovation"
                ]
                
                for query in consultancy_trend_queries:
                    trend_data.extend(self._search_data_source(query, "Consultancy Trend Reports"))
                
        except Exception as e:
            trend_data.append({"error": f"Macro trend analysis failed: {str(e)}"})
            
        return trend_data
    
    def get_funding_and_investment_analysis(self, brief, industry_data=None):
        """Analyze funding trends and investment patterns"""
        funding_data = []
        
        industry_keywords = industry_data.get('industry_keywords', []) if industry_data else []
        search_terms = ' '.join(industry_keywords) if industry_keywords else brief
        
        try:
            if self.serpapi_key:
                # Funding and investment queries
                funding_queries = [
                    f"{search_terms} venture capital funding Series A B C investment rounds",
                    f"{search_terms} private equity buyout M&A acquisition deals",
                    f"{search_terms} IPO initial public offering SPAC listing",
                    f"{search_terms} investment trends valuation multiples funding rounds",
                    f"{search_terms} startup funding unicorn decacorn valuations",
                    f"{search_terms} corporate venture capital strategic investments",
                    f"{search_terms} angel investment seed funding early stage",
                    f"{search_terms} growth equity late stage funding expansion"
                ]
                
                for query in funding_queries:
                    funding_data.extend(self._search_data_source(query, "Funding Analysis"))
                
                # Add CB Insights and PitchBook data
                specialized_funding_queries = [
                    f"site:cbinsights.com {search_terms} funding report venture capital",
                    f"site:pitchbook.com {search_terms} private equity venture capital data",
                    f"site:crunchbase.com {search_terms} startup funding investment rounds"
                ]
                
                for query in specialized_funding_queries:
                    funding_data.extend(self._search_data_source(query, "Investment Data Providers"))
                
        except Exception as e:
            funding_data.append({"error": f"Funding analysis failed: {str(e)}"})
            
        return funding_data
    
    def get_regulatory_and_compliance_analysis(self, brief, industry_data=None):
        """Analyze regulatory environment and compliance requirements"""
        regulatory_data = []
        
        industry_keywords = industry_data.get('industry_keywords', []) if industry_data else []
        search_terms = ' '.join(industry_keywords) if industry_keywords else brief
        primary_industry = industry_data.get('primary_industry', 'general') if industry_data else 'general'
        
        try:
            if self.serpapi_key:
                # Regulatory analysis queries
                regulatory_queries = [
                    f"{search_terms} regulatory requirements compliance standards",
                    f"{primary_industry} industry regulations government oversight",
                    f"{search_terms} data privacy GDPR CCPA compliance requirements",
                    f"{search_terms} FDA approval regulatory pathway clinical trials",
                    f"{search_terms} SEC regulations financial compliance reporting",
                    f"{search_terms} environmental regulations sustainability compliance",
                    f"{search_terms} cybersecurity regulations data protection laws",
                    f"{search_terms} international trade regulations export controls"
                ]
                
                for query in regulatory_queries:
                    regulatory_data.extend(self._search_data_source(query, "Regulatory Analysis"))
                
        except Exception as e:
            regulatory_data.append({"error": f"Regulatory analysis failed: {str(e)}"})
            
        return regulatory_data
    
    def generate_comprehensive_report(self, brief):
        """Generate a comprehensive marketing intelligence report"""
        print("🚀 Starting comprehensive marketing intelligence analysis...")
        
        # Gather all data sources
        market_data, industry_data = self.get_tam_sam_som_analysis(brief)
        competitive_data = self.get_competitive_intelligence(brief, industry_data)
        trend_data = self.get_macro_trend_analysis(brief, industry_data)
        funding_data = self.get_funding_and_investment_analysis(brief, industry_data)
        regulatory_data = self.get_regulatory_and_compliance_analysis(brief, industry_data)
        
        # Compile all research data
        all_research_data = {
            "market_analysis": market_data,
            "competitive_intelligence": competitive_data,
            "macro_trends": trend_data,
            "funding_analysis": funding_data,
            "regulatory_analysis": regulatory_data,
            "industry_classification": industry_data
        }
        if brief.find("- Output Format: Detailed Report") != -1:
            # Generate comprehensive analysis
            comprehensive_analysis_prompt = f"""
            You are a senior strategy consultant preparing a comprehensive marketing intelligence report.
            
            Business Brief: {brief}
            
            Industry Classification: {json.dumps(industry_data, indent=2)}
            
            Research Data Summary:
            - Market Analysis: {len(market_data)} sources
            - Competitive Intelligence: {len(competitive_data)} sources  
            - Macro Trends: {len(trend_data)} sources
            - Funding Analysis: {len(funding_data)} sources
            - Regulatory Analysis: {len(regulatory_data)} sources
            
            Based on this comprehensive research, provide a strategic marketing intelligence report with the following sections:
            
            # EXECUTIVE SUMMARY
            - Key strategic insights and recommendations
            - Critical success factors and market opportunities
            - Top 3 strategic priorities
            
            # MARKET OPPORTUNITY ANALYSIS
            - Total Addressable Market (TAM) sizing and growth projections
            - Serviceable Addressable Market (SAM) analysis
            - Serviceable Obtainable Market (SOM) opportunity
            - Market segment analysis and customer personas
            - Revenue potential and business model validation
            
            # COMPETITIVE LANDSCAPE
            - Competitive positioning matrix
            - Direct and indirect competitor analysis
            - Competitive advantages and differentiation opportunities
            - Market share analysis and competitive threats
            - Strategic partnerships and ecosystem analysis
            
            # MARKET DYNAMICS AND TRENDS
            - Industry growth drivers and headwinds
            - Technology disruption and innovation trends
            - Regulatory and compliance landscape
            - Consumer behavior and demographic shifts
            - Economic and macro-environmental factors
            
            # INVESTMENT AND FUNDING LANDSCAPE
            - Venture capital and private equity activity
            - Valuation benchmarks and funding trends
            - Strategic investor interest and corporate venture activity
            - M&A activity and consolidation trends
            - IPO and exit opportunities
            
            # STRATEGIC RECOMMENDATIONS
            - Go-to-market strategy recommendations
            - Product-market fit validation approach
            - Partnership and alliance opportunities
            - Investment and funding strategy
            - Risk mitigation and contingency planning
            
            # FINANCIAL PROJECTIONS AND BENCHMARKS
            - Revenue growth projections and scenarios
            - Unit economics and profitability analysis
            - Key performance indicators and benchmarks
            - Financial modeling assumptions and sensitivities
            
            Use specific data points, market sizing numbers, and quantitative insights from the research.
            Provide actionable recommendations with clear rationale.
            Focus on strategic decision-making and competitive advantage.
            """
            
            comprehensive_report = self.call_openai_agent(comprehensive_analysis_prompt, temperature=0.2)
            executive_summary = 'NA'
        else:     
            # Generate executive summary
            executive_summary_prompt = f"""
            Based on the comprehensive marketing intelligence analysis, create a concise executive summary 
            that a C-level executive could read in 3-5 minutes:
            
            Business Brief: {brief}
            
            Focus on:
            1. Market opportunity size and growth potential
            2. Competitive positioning and differentiation
            3. Key success factors and strategic priorities
            4. Investment requirements and expected returns
            5. Major risks and mitigation strategies
            
            Provide specific numbers, market sizing, and quantitative insights.
            Make clear recommendations with supporting rationale.
            """
            
            executive_summary = self.call_openai_agent(executive_summary_prompt, temperature=0.1)
            comprehensive_report = 'NA'
            
        # Generate data source summary
        data_source_summary = self._generate_data_source_summary(all_research_data)
        
        # Compile final report
        final_report = {
            "executive_summary": executive_summary,
            "comprehensive_analysis": comprehensive_report,
            "data_source_summary": data_source_summary,
            "research_metadata": {
                "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "industry_classification": industry_data,
                "data_sources_analyzed": {
                    "market_analysis": len(market_data),
                    "competitive_intelligence": len(competitive_data),
                    "macro_trends": len(trend_data),
                    "funding_analysis": len(funding_data),
                    "regulatory_analysis": len(regulatory_data)
                },
                "total_sources": len(market_data) + len(competitive_data) + len(trend_data) + len(funding_data) + len(regulatory_data)
            }
        }
        
        return final_report
    
    def _generate_data_source_summary(self, research_data):
        """Generate a summary of data sources used in the analysis"""
        source_summary = {
            "high_credibility_sources": [],
            "industry_specific_sources": [],
            "quantitative_data_sources": [],
            "recent_sources": [],
            "sec_filing_sources": []
        }
        
        # Analyze all data sources
        for category, data_list in research_data.items():
            if category == "industry_classification":
                continue
                
            for item in data_list:
                if isinstance(item, dict) and "source" in item:
                    source_info = {
                        "source": item.get("source", "Unknown"),
                        "category": category,
                        "relevance_score": item.get("relevance_score", 0),
                        "data_quality": item.get("data_quality", "Unknown")
                    }
                    
                    # Categorize sources
                    if item.get("relevance_score", 0) >= 8:
                        source_summary["high_credibility_sources"].append(source_info)
                    
                    if "SEC" in item.get("source", ""):
                        source_summary["sec_filing_sources"].append(source_info)
                    
                    if item.get("data_quality") == "High":
                        source_summary["quantitative_data_sources"].append(source_info)
                    
                    if item.get("publication_indicators", {}).get("has_date", False):
                        source_summary["recent_sources"].append(source_info)
        
        return source_summary
    
    def save_report(self, report, filename=None):
        """Save the comprehensive report to a JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"marketing_intelligence_report_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"📊 Report saved to: {filename}")
            return filename
        except Exception as e:
            print(f"❌ Error saving report: {str(e)}")
            return None
        
def marketing_agent(brief: str):
    agent = MarketingAgent()
    report_dict = agent.generate_comprehensive_report(brief)
    if brief.find("- Output Format: Detailed Report") != -1:
        formatted_report = f"""{report_dict.get('comprehensive_analysis', 'Comprehensive analysis not available')}"""
    else:
        formatted_report = f"""{report_dict.get('executive_summary', 'Executive summary not available')}"""
    formatted_report += f"""

        **Analysis Date:** {report_dict.get('research_metadata', {}).get('analysis_date', 'Not available')}

        **Industry Classification:** {report_dict.get('research_metadata', {}).get('industry_classification', {}).get('primary_industry', 'Not specified')}

        **Total Sources Analyzed:** {report_dict.get('research_metadata', {}).get('total_sources', 0)}

        ### Data Sources Breakdown:
        """
    
    # Add data sources breakdown
    data_sources = report_dict.get('research_metadata', {}).get('data_sources_analyzed', {})
    for source_type, count in data_sources.items():
        formatted_report += f"- **{source_type.replace('_', ' ').title()}:** {count} sources\n"
    
    # Add data source summary if available
    data_source_summary = report_dict.get('data_source_summary', {})
    if data_source_summary:
        formatted_report += f"\n### 🔍 DATA SOURCE QUALITY ASSESSMENT\n"
        
        high_cred_sources = len(data_source_summary.get('high_credibility_sources', []))
        sec_sources = len(data_source_summary.get('sec_filing_sources', []))
        quant_sources = len(data_source_summary.get('quantitative_data_sources', []))
        recent_sources = len(data_source_summary.get('recent_sources', []))
        
        formatted_report += f"- **High Credibility Sources:** {high_cred_sources}\n"
        formatted_report += f"- **SEC Filing Sources:** {sec_sources}\n"
        formatted_report += f"- **Quantitative Data Sources:** {quant_sources}\n"
        formatted_report += f"- **Recent Sources (2024-2025):** {recent_sources}\n"
    
    formatted_report += f"""

            This comprehensive analysis leverages {report_dict.get('research_metadata', {}).get('total_sources', 0)} data sources including:
            - Industry-specific consultancy reports
            - SEC filing analysis from relevant public companies
            - Competitive intelligence and market research
            - Macro trend analysis and regulatory insights
            - Investment and funding landscape analysis

            **Recommended Next Steps:**
            1. Review the executive summary for immediate strategic priorities
            2. Analyze the competitive positioning recommendations
            3. Evaluate the market sizing and revenue opportunity
            4. Consider the regulatory and compliance requirements
            5. Develop implementation roadmap based on strategic recommendations

            ---

            *This report was generated using advanced AI-powered market research and analysis. The insights are based on publicly available data and should be validated with additional primary research as needed.*
            """
    return formatted_report

