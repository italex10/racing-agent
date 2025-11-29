import streamlit as st
import google.generativeai as genai
import datetime
import json

# --- PAGE CONFIGURATION ---
# 'layout="centered"' looks better on mobile than 'wide'
st.set_page_config(page_title="Gemini Racing", page_icon="🏇", layout="centered")

# --- CUSTOM CSS FOR MOBILE CARDS ---
# This forces the metrics to have a card-like background
st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 14px; 
    }
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚡ Agent Settings")
    # Try to get key from Cloud Secrets first, otherwise ask user
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("API Key loaded from Cloud Secrets ☁️")
    else:
        api_key = st.text_input("Google API Key", type="password")
    
# --- MAIN INPUTS ---
st.title("🏇 Racing Agent")

col1, col2 = st.columns(2)
with col1:
    race_time = st.time_input("Time", datetime.time(15, 35))
    meeting = st.text_input("Meeting", placeholder="Newbury")
with col2:
    race_date = st.date_input("Date", datetime.date.today())
    bet_type = st.radio("Mode", ["Win", "Each-Way"], horizontal=True)

start_btn = st.button("Analyze Race", type="primary", use_container_width=True)

# --- AGENT LOGIC ---
if start_btn and api_key and meeting:
    genai.configure(api_key=api_key)
    
    with st.status("🚀 Agent Working...", expanded=True) as status:
        
        tools = [{"google_search_retrieval": {}}]

        # 1. DEFINE THE OUTPUT SCHEMA (JSON)
        # We force the model to fill in this specific form
        generation_config = genai.types.GenerationConfig(
            response_mime_type="application/json"
        )

        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash-001',
            tools=tools,
            generation_config=generation_config,
            system_instruction=f"""
            You are a Racing Analyst. You MUST output strictly compliant JSON.
            
            YOUR GOAL:
            1. Search for the racecard: {meeting} {race_time} on {race_date}.
            2. Analyze based on Going, Class, and Jockey.
            3. Return JSON with these exact keys:
               - "conditions": "e.g. Soft, 2m 4f"
               - "selection": "Name of horse"
               - "selection_odds": "e.g. 4/1"
               - "danger": "Name of danger horse"
               - "danger_odds": "e.g. 7/2"
               - "jockey_alert": "Any top jockey booking or null"
               - "logic": "Concise reasoning for the selection."
            """
        )
        
        status.write("🔍 Finding racecard & checking going...")
        
        try:
            # The prompt is simple because the System Instruction handles the structure
            response = model.generate_content(
                f"Analyze the {race_time} race at {meeting} ({race_date}) for a {bet_type} bet."
            )
            
            # Parse the JSON response
            data = json.loads(response.text)
            
            status.update(label="Analysis Complete", state="complete", expanded=False)
            
            # --- MOBILE OPTIMIZED DISPLAY ---
            
            # 1. Jockey Alert Banner (if exists)
            if data.get("jockey_alert") and data["jockey_alert"] != "null":
                st.error(f"🚨 **JOCKEY ALERT:** {data['jockey_alert']}")
            
            # 2. The Conditions
            st.caption(f"📍 {meeting} • {data['conditions']}")
            
            # 3. Big Stats Cards (st.metric)
            # On mobile, these will stack beautifully
            c1, c2 = st.columns(2)
            with c1:
                st.metric(
                    label="🏆 THE SELECTION",
                    value=data['selection'],
                    delta=data['selection_odds']
                )
            with c2:
                st.metric(
                    label="⚠️ THE DANGER",
                    value=data['danger'],
                    delta=data['danger_odds'],
                    delta_color="inverse" # Makes the danger red/gray
                )

            # 4. The Logic Section
            st.divider()
            st.subheader("📝 The Logic")
            st.info(data['logic'])

        except Exception as e:
            status.update(label="Error", state="error")
            st.error(f"Oops: {e}")

elif start_btn and not api_key:
    st.warning("Please enter your API Key.")
  
