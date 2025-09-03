"""
HR Sentiment Analysis - Streamlit Web Application
Clean UI with context-aware AI analysis
"""

import streamlit as st
import os
import plotly.express as px
import plotly.graph_objects as go
from main import HRAnalyzer

# === PAGE CONFIGURATION ===
st.set_page_config(
    page_title="HR Sentiment Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === INITIALIZATION ===
@st.cache_resource
def initialize_analyzer():
    """Create HRAnalyzer and load data from MySQL"""
    try:
        analyzer = HRAnalyzer()
        loaded = analyzer.load_data()
        if loaded:
            st.sidebar.success("✅ Data loaded from MySQL successfully")
            return analyzer, True
        else:
            st.sidebar.info("ℹ️ No data found in MySQL database")
            return analyzer, False
    except Exception as e:
        st.sidebar.error(f"❌ Failed to initialize: {e}")
        return None, False

# === HELPER FUNCTIONS ===
def get_employees_by_quadrant(analyzer, quadrant_name):
    """Return list of employees filtered by quadrant_name"""
    if not analyzer or not hasattr(analyzer, "data") or not analyzer.data:
        return []
    return [emp for emp in analyzer.data if emp.get('quadrant') == quadrant_name]

def display_employees(employees):
    """Display employees in a formatted table"""
    if not employees:
        st.info("No employees found in this category.")
        return
        
    for emp in employees:
        cols = st.columns([1, 2, 1, 6])
        cols[0].markdown(f"**ID:** {emp.get('id','-')}")
        cols[1].markdown(f"**Role:** {emp.get('role','-')}")
        cols[2].markdown(f"**Sentiment:** {emp.get('sentiment_score',0):.1f}%")
        cols[3].write(emp.get('content','-'))

def extract_ai_text(response):
    """Safely extract text from Gemini response or HRAnalyzer output"""
    try:
        if not response:
            return None
        if isinstance(response, str):
            return response
        if hasattr(response, "candidates") and response.candidates:
            parts = response.candidates[0].content.parts
            if parts and hasattr(parts[0], "text"):
                return parts[0].text
        if hasattr(response, "text"):
            return response.text
        return None
    except Exception as e:
        return f"⚠️ Extraction failed: {e}"

def build_context(analyzer):
    """Build structured context from analyzer data for better AI responses"""
    summary = analyzer.get_analytics_summary()
    
    quadrant_info = ", ".join([f"{k}: {v}" for k, v in summary["quadrant_distribution"].items()])
    role_info = ", ".join([f"{role}: {sent:.1f}%" for role, sent in summary["sentiment_by_role"].items()])

    context = f"""
    Total Employees: {summary['total_employees']}
    Average Sentiment: {summary['average_sentiment']:.1f}%
    Quadrant Distribution: {quadrant_info}
    Sentiment by Role: {role_info}

    Example Employee Records:
    """
    for emp in analyzer.data[:21]:
        context += f"\n- {emp.get('employee_name','Unknown')} ({emp.get('role','-')}): {emp.get('sentiment_score',0):.1f}%, {emp.get('quadrant','-')}"
    
    return context

# === SIDEBAR STATUS ===
def show_environment_status():
    with st.sidebar:
        st.subheader("🔧 System Status")

        analyzer = st.session_state.get("analyzer", None)
        if analyzer:
            st.success("✅ Environment configured")

            if getattr(analyzer, "gemini_client", None):
                st.success("✅ Gemini AI connected")
            #else:
                #st.error("❌ Gemini AI unavailable")

            if getattr(analyzer, "qdrant_client", None):
                st.success("✅ Vector database connected")
            else:
                st.info("ℹ️ Vector database offline (optional)")
        else:
            st.warning("ℹ️ Analyzer not initialized")

# === DATA MANAGEMENT SECTION ===
def data_management_section():
    st.header("📂 Data Management")

    analyzer = st.session_state.get("analyzer", None)

    if analyzer and analyzer.data:
        data_count = len(analyzer.data)
        avg_sentiment = analyzer.get_average_sentiment()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Records Loaded", data_count)
        with col2:
            st.metric("😊 Average Sentiment", f"{avg_sentiment:.1f}%")
        with col3:
            quadrants = analyzer.get_quadrant_distribution()
            at_risk = quadrants.get("At Risk", 0)
            st.metric("⚠️ At Risk Employees", at_risk)

    st.subheader("🔄 Refresh Data from MySQL")
    if st.button("🔄 Reload Data", type="primary", use_container_width=True):
        if analyzer:
            try:
                reloaded = analyzer.load_data()
                if reloaded:
                    st.session_state.data_loaded = True
                    st.success("✅ Data reloaded successfully from MySQL!")
                    st.rerun()
                else:
                    st.warning("⚠️ No data returned from MySQL or reload failed.")
            except Exception as e:
                st.error(f"❌ Failed to reload: {e}")
        else:
            st.error("❌ Analyzer not initialized")

# === ANALYTICS DASHBOARD ===
def analytics_dashboard():
    analyzer = st.session_state.get("analyzer", None)
    if not analyzer or not analyzer.data:
        st.info("📊 Load data from MySQL to see analytics dashboard")
        return

    summary = analyzer.get_analytics_summary()
    st.header("📊 Analytics Dashboard")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 Total Employees", summary['total_employees'])
    col2.metric("😊 Average Sentiment", f"{summary['average_sentiment']:.1f}%", 
               "Healthy" if summary['average_sentiment']>60 else "Needs Attention")
    col3.metric("🏆 Champions", summary['quadrant_distribution'].get('Champion', 0))
    col4.metric("⚠️ At Risk", summary['quadrant_distribution'].get('At Risk', 0))

    # Charts
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🥧 Employee Quadrant Distribution")
        quadrant_data = summary['quadrant_distribution']
        if quadrant_data:
            fig = px.pie(
                values=list(quadrant_data.values()),
                names=list(quadrant_data.keys()),
                color_discrete_map={
                    'Champion': '#28a745',
                    'Concerned but active': '#ffc107',
                    'Potentially Isolated': '#fd7e14',
                    'At Risk': '#dc3545'
                },
                hole=0.4
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
            
    with col2:
        st.subheader("📊 Sentiment by Role")
        role_data = summary['sentiment_by_role']
        if role_data:
            roles = list(role_data.keys())
            sentiments = list(role_data.values())
            colors = ['#28a745' if s>70 else '#ffc107' if s>50 else '#dc3545' for s in sentiments]
            fig = go.Figure([go.Bar(
                x=roles, 
                y=sentiments, 
                marker_color=colors,
                text=[f"{s:.1f}%" for s in sentiments],
                textposition='auto'
            )])
            fig.update_layout(yaxis=dict(range=[0,100]), height=400)
            st.plotly_chart(fig, use_container_width=True)

# === AI ANALYSIS INTERFACE ===
def ai_analysis_interface():
    analyzer = st.session_state.get("analyzer", None)
    if not analyzer or not analyzer.data:
        st.info("🤖 Load data from MySQL to enable AI analysis")
        return  

    st.header("🤖 AI-Powered Analysis")

    context = build_context(analyzer)

    # Quick Analysis Buttons
    button_cols = st.columns(4)
    
    show_champions = button_cols[0].button("🏆 Show Champions", key="qa_champions")
    show_at_risk = button_cols[1].button("⚠️ Show At Risk", key="qa_at_risk")
    show_engagement = button_cols[2].button("📈 Engagement Summary", key="qa_engagement")
    show_retention = button_cols[3].button("🎯 Retention Insights", key="qa_retention")

    if show_champions:
        employees = get_employees_by_quadrant(analyzer, "Champion")
        st.subheader(f"🏆 Champion Employees ({len(employees)})")
        display_employees(employees)
        
    if show_at_risk:
        employees = get_employees_by_quadrant(analyzer, "At Risk")
        st.subheader(f"⚠️ At Risk Employees ({len(employees)})")
        display_employees(employees)
        
    if show_engagement:
        with st.spinner("🧠 Analyzing engagement..."):
            query = "What is the overall employee engagement status and key factors affecting it?"
            try:
                response = analyzer.analyze_with_ai(query, context)
                result = extract_ai_text(response)
                st.subheader("📈 Engagement Analysis")
                if result:
                    st.markdown(result)
                else:
                    st.error("❌ AI analysis returned no content.")
            except Exception as e:
                st.subheader("📈 Engagement Analysis")
                st.error(f"❌ AI analysis failed: {e}")

    if show_retention:
        with st.spinner("🧠 Analyzing retention factors..."):
            query = "What factors might affect employee retention and what are your recommendations?"
            try:
                response = analyzer.analyze_with_ai(query, context)
                result = extract_ai_text(response)
                st.subheader("🎯 Retention Analysis")
                if result:
                    st.markdown(result)
                else:
                    st.error("❌ AI analysis returned no content.")
            except Exception as e:
                st.subheader("🎯 Retention Analysis")
                st.error(f"❌ AI analysis failed: {e}")

    # Custom Query Section
    st.subheader("💬 Ask Custom Questions")
    query = st.text_area("Enter your question:", height=100)
    if query and st.button("🤖 Analyze", key="custom_analysis"):
        quadrant_keywords = {
            "champion": "Champion",
            "at risk": "At Risk",
            "concerned": "Concerned but active",
            "isolated": "Potentially Isolated"
        }
        quadrant_found = False
        for kw, quad in quadrant_keywords.items():
            if kw.lower() in query.lower():
                employees = get_employees_by_quadrant(analyzer, quad)
                st.subheader(f"📌 {quad} Employees ({len(employees)})")
                display_employees(employees)
                quadrant_found = True
                break
                
        if not quadrant_found:
            with st.spinner("🤖 Generating AI insights..."):
                try:
                    response = analyzer.analyze_with_ai(query, context)
                    result = extract_ai_text(response)
                    st.subheader("🎯 AI Analysis Results")
                    if result:
                        st.markdown(result)
                    else:
                        st.error("❌ AI analysis returned no content.")
                except Exception as e:
                    st.subheader("🎯 AI Analysis Results")
                    st.error(f"❌ AI analysis failed: {e}")

# === MAIN APPLICATION ===
def main():
    st.title("📊 HR Sentiment Analysis with AI")
    st.markdown("**Advanced employee feedback analysis using AI-powered insights**")

    # Initialize analyzer if not in session state
    if 'analyzer' not in st.session_state:
        analyzer, data_loaded = initialize_analyzer()
        st.session_state.analyzer = analyzer
        st.session_state.data_loaded = data_loaded

    show_environment_status()

    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📂 Data Management", "📊 Analytics Dashboard", "🤖 AI Analysis"])
    
    with tab1:
        data_management_section()
    with tab2:
        analytics_dashboard()
    with tab3:
        ai_analysis_interface()

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666; padding: 20px;'>"
        "💡 Load SQL • 📊 View Analytics • 🤖 Get AI Insights • 🎯 Make Data-Driven Decisions"
        "</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
