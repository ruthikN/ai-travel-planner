import streamlit as st
import google.generativeai as genai
from datetime import date
import json
import time

# Configure Gemini API with proper endpoint
genai.configure(
    api_key=st.secrets["GEMINI_API_KEY"],
    transport="rest",
    client_options={
        "api_endpoint": "generativelanguage.googleapis.com/v1beta/models/gemini-1.0-pro:generateContent"
    }
)

def generate_itinerary(user_input):
    """Generate travel itinerary using Google Gemini 1.0 Pro"""
    try:
        # Structured prompt template
        prompt = f"""
        **Travel Planning Request**
        Create a detailed {user_input['duration']}-day itinerary for {user_input['name']} visiting {user_input['destination']}.
        
        **Travel Details:**
        - Budget Level: {user_input['budget']}
        - Travel Style: {user_input['travel_style']}
        - Start Date: {user_input['start_date']}
        - Dietary Needs: {user_input['dietary']}
        - Special Requirements: {user_input['requirements']}
        - Interests: {', '.join(user_input['interests'])}

        **Format Requirements:**
        1. Day-by-day schedule with time blocks
        2. Morning/Afternoon/Evening sections
        3. Specific attraction/restaurant recommendations
        4. Transportation tips between locations
        5. Budget estimates per category
        6. Safety/cultural notes
        
        Use markdown formatting with emojis for better readability.
        """
        
        model = genai.GenerativeModel('gemini-1.0-pro')
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.9,
                "max_output_tokens": 2048
            }
        )
        
        # Add slight delay for better streaming simulation
        time.sleep(1)
        return response.text
        
    except Exception as e:
        st.error(f"⚠️ Error generating itinerary: {str(e)}")
        return None

# Streamlit UI Configuration
st.set_page_config(
    page_title="AI Travel Planner Pro",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar Configuration
with st.sidebar:
    st.title("⚙️ Settings")
    st.markdown("---")
    travel_style = st.selectbox(
        "Travel Style",
        ["🏖️ Relaxing", "🧗 Adventure", "🏛️ Cultural", "🍜 Foodie", "👨👩👧👦 Family"]
    )
    num_days = st.slider("Trip Duration (Days)", 1, 21, 7)
    pace = st.select_slider(
        "Daily Pace",
        options=["🐢 Leisurely", "🚶 Moderate", "🏃 Fast-paced"]
    )

# Main Interface
st.title("🌍 AI Travel Planner Pro")
st.markdown("---")

# Input Section
col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Traveler Name", placeholder="Enter your name...")
    destination = st.text_input("Destination", placeholder="Country/City...")
    budget = st.selectbox(
        "Budget Level",
        ["💰 Budget", "💵 Mid-range", "💎 Luxury"]
    )

with col2:
    start_date = st.date_input("Start Date", date.today() + timedelta(days=7))
    dietary = st.multiselect(
        "Dietary Needs",
        ["🍃 Vegetarian", "🌱 Vegan", "🌾 Gluten-free", "🕊️ Halal"]
    )
    requirements = st.text_area(
        "Special Requirements",
        placeholder="Mobility needs, allergies, etc..."
    )

# Interests Section
interests = st.multiselect(
    "Select Your Interests",
    options=[
        "🏰 Historical Sites", "🍣 Local Food", "🌳 Nature",
        "🎨 Art & Museums", "🛍️ Shopping", "🌃 Nightlife"
    ],
    default=["🏰 Historical Sites", "🍣 Local Food"]
)

# Generate Button
if st.button("✨ Generate Travel Plan", use_container_width=True):
    if not destination or not name:
        st.warning("Please fill in required fields: Name and Destination")
    else:
        user_input = {
            "name": name,
            "destination": destination,
            "budget": budget,
            "duration": num_days,
            "travel_style": travel_style,
            "pace": pace,
            "dietary": dietary,
            "requirements": requirements,
            "interests": interests,
            "start_date": str(start_date)
        }
        
        with st.spinner("🧭 Crafting your perfect itinerary..."):
            itinerary = generate_itinerary(user_input)
        
        if itinerary:
            # Display Results
            st.success("✅ Itinerary Generated Successfully!")
            st.markdown("---")
            st.subheader(f"🗺️ {destination} Itinerary Overview")
            st.markdown(itinerary, unsafe_allow_html=True)
            
            # Additional Features
            with st.expander("📌 Travel Safety Tips"):
                safety_tips = genai.GenerativeModel('gemini-1.0-pro').generate_content(
                    f"Generate safety tips for {destination} considering: {requirements}"
                ).text
                st.markdown(safety_tips)
            
            # Download Options
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📥 Download as Text",
                    data=itinerary,
                    file_name=f"{destination}_itinerary.txt",
                    mime="text/plain"
                )
            with col2:
                st.button(
                    "🔄 Generate Alternative Version",
                    help="Generate a different version of this itinerary"
                )
        else:
            st.error("❌ Failed to generate itinerary. Please try again.")

# Requirements File
requirements.txt:
