import streamlit as st
import asyncio
import threading
import time
from datetime import datetime
from queue import Queue
import json

# Enhanced streaming UI components
class StreamingAnalysisUI:
    def __init__(self):
        self.progress_queue = Queue()
        self.results_queue = Queue()
        self.analysis_complete = False
        
    def create_real_time_progress(self):
        """Create real-time progress display"""
        progress_container = st.empty()
        status_container = st.empty()
        results_container = st.empty()
        
        return progress_container, status_container, results_container
    
    def update_progress(self, message, progress_value):
        """Update progress callback"""
        self.progress_queue.put({"message": message, "progress": progress_value})
    
    def display_streaming_results(self, brief, agent_type):
        """Display results with real-time streaming"""
        
        # Create containers for dynamic updates
        progress_container, status_container, results_container = self.create_real_time_progress()
        
        # Initialize progress
        progress_bar = progress_container.progress(0)
        status_text = status_container.empty()
        
        # Start analysis in background thread
        analysis_thread = threading.Thread(
            target=self.run_analysis_thread,
            args=(brief, agent_type)
        )
        analysis_thread.start()
        
        # Real-time progress updates
        partial_results = ""
        while not self.analysis_complete:
            try:
                # Check for progress updates
                if not self.progress_queue.empty():
                    progress_data = self.progress_queue.get_nowait()
                    status_text.text(progress_data["message"])
                    progress_bar.progress(progress_data["progress"])
                
                # Check for partial results
                if not self.results_queue.empty():
                    result_data = self.results_queue.get_nowait()
                    partial_results += result_data
                    
                    # Display partial results as they come in
                    with results_container.container():
                        st.markdown("### Analysis in Progress...")
                        st.markdown(partial_results)
                        st.markdown("---")
                        st.markdown("*Analysis continuing...*")
                
                time.sleep(0.1)  # Small delay to prevent overwhelming the UI
                
            except Exception as e:
                st.error(f"Error in streaming: {str(e)}")
                break
        
        # Wait for thread to complete
        analysis_thread.join()
        
        # Clear progress indicators
        progress_container.empty()
        status_container.empty()
        
        # Display final results
        if hasattr(self, 'final_result'):
            self.display_final_results(self.final_result, agent_type, results_container)
    
    def run_analysis_thread(self, brief, agent_type):
        """Run analysis in background thread"""
        try:
            if agent_type == "Legal & Compliance":
                from legal_agent import legal_agent_optimized
                result = legal_agent_optimized(brief)
            else:
                from marketing2 import get_agent
                # from marketing_agent import marketing_agent
                agent = get_agent()
                if agent is None:
                    raise ValueError("Marketing agent not initialized")
                    result = marketing_agent(brief)
                else:
                    agent = agent.set_knowledge_base(agent)
                    result = agent.get_consultation(brief)
            
            self.final_result = result
            self.analysis_complete = True
            
        except Exception as e:
            self.final_result = f"Analysis failed: {str(e)}"
            self.analysis_complete = True
    
    def display_final_results(self, output, agent_type, container):
        """Display final results with enhanced formatting"""
        with container.container():
            st.markdown("---")
            st.markdown("## ✅ Analysis Complete")
            
            if agent_type == "Legal & Compliance":
                st.markdown("### 🏛️ Legal & Compliance Analysis")
                st.markdown("*Comprehensive legal risk assessment and compliance roadmap*")
            else:
                st.markdown("### 📊 Strategic Market Analysis")
                st.markdown("*Expert-level market intelligence and strategic recommendations*")
            
            # Add analysis timestamp
            st.markdown(f"**Analysis Date:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
            
            # Split output into sections for better readability
            sections = self.parse_analysis_sections(output)
            
            for section_title, section_content in sections.items():
                with st.expander(section_title, expanded=True):
                    st.markdown(section_content)
            
            # Add download button
            st.download_button(
                label="📥 Download Analysis Report",
                data=output,
                file_name=f"{agent_type.lower().replace(' & ', '_').replace(' ', '_')}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
                use_container_width=True
            )
    
    def parse_analysis_sections(self, output):
        """Parse analysis output into logical sections"""
        sections = {}
        
        # Split by common headers
        lines = output.split('\n')
        current_section = "Executive Summary"
        current_content = []
        
        for line in lines:
            if line.startswith('##') or line.startswith('###'):
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                
                # Start new section
                current_section = line.strip('#').strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Add final section
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections

# Enhanced main function with streaming
def main_with_streaming():
    st.set_page_config(
        page_title="Legal and Marketing Assistance - Optimized",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better performance indicators
    st.markdown("""
    <style>
        .streaming-header {
            font-size: 2.5rem;
            font-weight: 700;
            color: #1f2937;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        .performance-badge {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-block;
            margin: 0.5rem;
        }
        .quick-analysis {
            background: #000000;
            border: 1px solid #0ea5e9;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 1rem 0;
        }
        .streaming-indicator {
            background: linear-gradient(45deg, #3b82f6, #1d4ed8);
            color: white;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 1rem 0;
            text-align: center;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header with performance indicators
    st.markdown('<h1 class="streaming-header">🚀 Legal & Marketing Assistance - Optimized</h1>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    # Sidebar with optimized settings
    with st.sidebar:
        st.header("⚙️ Optimized Settings")
        
        agent_type = st.selectbox(
            "Select Advisory Service",
            ["Legal & Compliance", "Strategic Marketing & Analysis"]
        )
        
        # Analysis speed settings
        st.markdown("### 🚀 Performance Settings")
        
        analysis_speed = st.selectbox(
            "Analysis Speed",
            ["Ultra Fast (1-2 min)", "Balanced (2-3 min)", "Comprehensive (3-5 min)"],
            index=0,
            help="Ultra Fast: Core insights only, Balanced: Key analysis, Comprehensive: Full research"
        )
        
        streaming_enabled = st.checkbox(
            "Enable Real-time Streaming",
            value=True,
            help="Show results as they're generated"
        )
        
        concurrent_research = st.checkbox(
            "Parallel Research",
            value=True,
            help="Run multiple research queries simultaneously"
        )
        
        st.markdown("---")
        st.markdown("### 📊 Analysis Scope")
        
        max_sources = st.slider(
            "Max Sources per Category",
            min_value=2,
            max_value=10,
            value=3,
            help="Fewer sources = faster analysis"
        )
        
        depth_level = st.selectbox(
            "Analysis Depth",
            ["Essential", "Standard", "Detailed"],
            index=0
        )
    
    # Main content area
    st.markdown("### 📝 Business Brief")
    
    # Enhanced input with templates
    col1, col2 = st.columns([3, 1])
    
    with col1:
        brief = st.text_area(
            "Describe your business:",
            height=150,
            placeholder="Enter your business description...",
            help="Be specific about your business model, target market, and key concerns"
        )
    
    with col2:
        st.markdown("### 🎯 Quick Templates")
        
        templates = {
            "SaaS Startup": "B2B SaaS platform for small businesses providing...",
            "E-commerce": "Online marketplace connecting buyers and sellers of...",
            "FinTech": "Financial technology solution that enables...",
            "Healthcare": "Healthcare technology platform that helps...",
            "Custom": ""
        }
        
        template_choice = st.selectbox("Use Template", list(templates.keys()))
        
        if template_choice != "Custom" and st.button("Use Template"):
            brief = templates[template_choice]
            st.rerun()
    
    # Quick analysis section
    # if brief:
    #     st.markdown("""
    #     <div class="quick-analysis">
    #         <h4>🔍 Quick Analysis Preview</h4>
    #         <p>Based on your brief, we'll analyze:</p>
    #         <ul>
    #             <li><strong>Regulatory Requirements:</strong> Key compliance areas</li>
    #             <li><strong>Legal Risks:</strong> Primary liability concerns</li>
    #             <li><strong>Market Opportunities:</strong> Growth potential</li>
    #             <li><strong>Competitive Landscape:</strong> Key players and positioning</li>
    #         </ul>
    #     </div>
    #     """, unsafe_allow_html=True)
    
    # Analysis execution
    if st.button("Start Analysis", type="primary", use_container_width=True):
        if brief:
            streaming_ui = StreamingAnalysisUI()
            
            if streaming_enabled:
                st.markdown("""
                <div class="streaming-indicator">
                    <h4> Analysis in Progres s</h4>
                    <p>Results will appear below as they're generated...</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Run streaming analysis
                streaming_ui.display_streaming_results(brief, agent_type)
            else:
                # Traditional analysis with progress bar
                with st.spinner("Analyzing..."):
                    progress_bar = st.progress(0)
                    
                    def progress_callback(message, progress):
                        progress_bar.progress(progress)
                        st.write(f"Status: {message}")
                    
                    if agent_type == "Legal & Compliance":
                        from legal_agent import legal_agent_optimized
                        result = legal_agent_optimized(brief)
                    else:
                        from marketing_agent import marketing_agent
                        result = marketing_agent(brief)
                    
                    progress_bar.progress(1.0)
                    st.success("Analysis complete!")
                    
                    # Display results
                    streaming_ui.display_final_results(result, agent_type, st.empty())
        else:
            st.warning("Please enter a business brief to proceed.")
    
    # Performance tips
    # with st.expander("🚀 Performance Tips"):
    #     st.markdown("""
    #     **For fastest results:**
    #     - Use "Ultra Fast" mode for core insights
    #     - Enable parallel research
    #     - Limit sources to 2-3 per category
    #     - Use specific, focused business briefs
        
    #     **For comprehensive analysis:**
    #     - Use "Comprehensive" mode
    #     - Increase max sources to 5-8
    #     - Provide detailed business context
    #     - Allow 3-5 minutes for complete analysis
    #     """)

if __name__ == "__main__":
    main_with_streaming()