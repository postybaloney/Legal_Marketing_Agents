import streamlit as st
from legal_agent import legal_agent
from marketing_agent import marketing_agent
import time
import json
from datetime import datetime

st.set_page_config(
    page_title="Legal and Marketing Assistance",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        text-align: center;
        margin-bottom: 2rem;
    }
    .agent-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 0.75rem;
        color: white;
        margin: 1rem 0;
    }
    .legal-card {
        # background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    .marketing-card {
        # background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }
    .feature-list {
        font-size: 0.9rem;
        margin-top: 1rem;
    }
    .stProgress .st-bo {
        background-color: #e5e7eb;
    }
    .analysis-section {
        background-color: #f8fafc;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 4px solid #3b82f6;
    }
</style>
""", unsafe_allow_html=True)

def typewriter_output(text, delay=0.01):
    """Enhanced typewriter effect with progress indication"""
    container = st.empty()
    progress_bar = st.progress(0)
    full_output = ""
    
    for i, char in enumerate(text):
        full_output += char
        container.markdown(full_output, unsafe_allow_html=True)
        progress_bar.progress((i + 1) / len(text))
        time.sleep(delay)
    
    progress_bar.empty()
    return full_output

def display_analysis_results(output, agent_type):
    """Display results with professional formatting"""
    st.markdown("---")
    st.markdown(f"<div class='analysis-section'>", unsafe_allow_html=True)
    
    if agent_type == "Legal & Compliance":
        st.markdown("### Legal & Compliance Analysis")
        st.markdown("*Comprehensive legal risk assessment and compliance roadmap*")
    else:
        st.markdown("### Strategic Market Analysis")
        st.markdown("*Provide expert-level market intelligence and strategic recommendations*")
    
    # Add analysis timestamp
    st.markdown(f"**Analysis Date:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
    
    # Display the output with typewriter effect
    with st.expander("Full Analysis Report", expanded=True):
        typewriter_output(output, delay=0.003)
    
    st.markdown("</div>", unsafe_allow_html=True)

def main():
    # Header
    st.markdown('<h1 class="main-header"> Legal and Marketing Assistance </h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">World-class legal and marketing intelligence powered by AI</p>', unsafe_allow_html=True)
    
    # Sidebar configuration
    with st.sidebar:
        st.header("Configuration")
        
        # Agent selection
        agent_type = st.selectbox(
            "Select Advisory Service",
            ["Legal & Compliance", "Strategic Marketing & Analysis"],
            help="Choose the type of analysis you need"
        )
        
        # Analysis depth
        analysis_depth = st.selectbox(
            "Analysis Depth",
            ["Standard", "Deep Dive", "Executive Summary"],
            index=1,
            help="Select the depth of analysis required"
        )
        
        # Output format
        output_format = st.selectbox(
            "Output Format",
            ["Detailed Report", "Executive Summary"],
            # Action Items can be later added
            help="Choose how you want the results formatted"
        )
        
        st.markdown("---")
        st.markdown("### Information Sources")
        st.markdown("Legal Case Databases")
        st.markdown("Regulatory Intelligence")
        st.markdown("Market Research Platforms")
        st.markdown("Competitive Intelligence")
        st.markdown("Financial Analysis Tools")
        st.markdown("Industry Expert Insights")
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if agent_type == "Legal & Compliance":
            st.markdown("""
            <div class="agent-card legal-card">
                <h3> Legal & Compliance Advisory</h3>
                <p>Comprehensive legal risk assessment and compliance strategy development</p>
                <div class="feature-list">
                    <strong>Key Features:</strong><br>
                    • Multi-jurisdictional legal research<br>
                    • Regulatory compliance mapping<br>
                    • Risk assessment matrix<br>
                    • Compliance roadmap development<br>
                    • International legal considerations<br>
                    • Executive-ready recommendations
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="agent-card marketing-card">
                <h3>Strategic Marketing & Analysis</h3>
                <p> Provide expert-level market intelligence and strategic business analysis</p>
                <div class="feature-list">
                    <strong>Key Features:</strong><br>
                    • TAM/SAM/SOM market sizing<br>
                    • Competitive intelligence analysis<br>
                    • Porter's Five Forces framework<br>
                    • Financial projections & modeling<br>
                    • Go-to-market strategy<br>
                    • Strategic recommendations
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        # Input section
        st.markdown("### Business Brief")
        brief = st.text_area(
            "Describe your business idea, product, or service:",
            height=200,
            placeholder="Enter a detailed description of your business concept, target market, key features, and any specific questions you have...",
            help="The more detailed your brief, the more comprehensive and actionable the analysis will be."
        )
        
        # Additional context
        with st.expander(" Additional Context (Optional)"):
            industry = st.text_input("Industry/Sector", placeholder="e.g., FinTech, Healthcare, E-commerce")
            geography = st.text_input("Target Geography", placeholder="e.g., United States, European Union, Global")
            stage = st.selectbox("Business Stage", ["Concept", "Pre-Launch", "Launch", "Growth", "Scale"])
            funding = st.text_input("Funding Status", placeholder="e.g., Bootstrapped, Seed, Series A")
    
    # Analysis button
    if st.button("Generate Strategic Analysis", type="primary", use_container_width=True):
        if brief:
            # Prepare enhanced brief with context
            enhanced_brief = f"""
            Business Brief: {brief}
            
            Additional Context:
            - Industry: {industry if industry else 'Not specified'}
            - Geography: {geography if geography else 'Not specified'}
            - Stage: {stage}
            - Funding: {funding if funding else 'Not specified'}
            - Analysis Depth: {analysis_depth}
            - Output Format: {output_format}
            """
            
            # Display analysis progress
            with st.spinner("🔍 Conducting comprehensive analysis..."):
                progress_text = st.empty()
                progress_bar = st.progress(0)
                
                # Simulate analysis stages
                stages = [
                    "Initializing research modules...",
                    "Gathering market intelligence...",
                    "Analyzing competitive landscape...",
                    "Processing regulatory data...",
                    "Generating strategic frameworks...",
                    "Compiling executive summary...",
                    "Finalizing recommendations..."
                ]
                
                for i, stage in enumerate(stages):
                    progress_text.text(stage)
                    progress_bar.progress((i + 1) / len(stages))
                    time.sleep(43)
                
                # Run the appropriate agent
                try:
                    if agent_type == "Legal & Compliance":
                        output = legal_agent(enhanced_brief)
                    else:
                        output = marketing_agent(enhanced_brief)
                    
                    progress_text.empty()
                    progress_bar.empty()
                    
                    # Display results
                    display_analysis_results(output, agent_type)
                    
                    # Add download option
                    st.download_button(
                        label=" Download Analysis Report",
                        data=output,
                        file_name=f"{agent_type.lower().replace(' & ', '_').replace(' ', '_')}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"Analysis failed: {str(e)}")
                    st.info("Please check your API keys and network connection.")
        else:
            st.warning("Please enter a business brief to proceed with the analysis.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #6b7280; font-size: 0.9rem;">
        <p> Legal and Marketing Assistance | Powered by Advanced AI Research & Analysis</p>
        <p>For best results, ensure your business brief is detailed and specific.</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()