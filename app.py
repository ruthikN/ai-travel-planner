import streamlit as st
import google.generativeai as genai
from datetime import date
import json

# Configure Gemini API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def generate_itinerary(user_input):
    """Generate travel itinerary using Google Gemini with enhanced prompt engineering"""
    try:
        # Structured prompt template
        prompt = f"""
        **Travel Planning Request**
        Create a detailed {user_input['duration']}-day itinerary for {user_input['name']} visiting {user_input['destination']}.
        
        **Traveler Preferences:**
        - Budget: {user_input['budget']}
        - Travel Style: {user_input['travel_style']}
        - Dietary Preferences: {user_input['dietary']}
        - Special Requirements: {user_input['requirements']}
        - Interests: {user_input['interests']}
        
        **Itinerary Requirements:**
        1. Include daily schedules with time allocations
        2. Recommend specific restaurants with local cuisine
        3. Suggest accommodation options matching the budget
        4. Include transportation options between locations
        5. Add cultural tips and safety advice
        6. Provide estimated costs for each day
        
        Format the response in Markdown with clear section headers.
        """
        
        model = genai.GenerativeModel('gemini-pro',
                                    generation_config={
                                        "temperature": 0.7,
                                        "max_output_tokens": 2000
                                    })
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        st.error(f"Error generating itinerary: {str(e)}")
        return None

# Streamlit UI
st.set_page_config(page_title="AI Travel Planner", page_icon="✈️", layout="wide")

# Sidebar for settings
with st.sidebar:
    st.header("Settings")
    travel_style = st.selectbox("Travel Style", ["Relaxing", "Adventure", "Cultural", "Foodie", "Family-Friendly"])
    num_days = st.slider("Trip Duration (Days)", 1, 14, 5)
    pace = st.select_slider("Daily Pace", ["Leisurely", "Moderate", "Fast-paced"])

# Main content
st.title("🌍 AI-Powered Travel Planner")
st.subheader("Craft Your Perfect Journey")

# Input columns
col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Traveler Name", placeholder="John Doe")
    destination = st.text_input("Destination", placeholder="Tokyo, Japan")
    budget = st.selectbox("Budget Level", ["Budget", "Mid-range", "Luxury"])
    
with col2:
    start_date = st.date_input("Start Date", date.today())
    dietary = st.multiselect("Dietary Preferences", ["None", "Vegetarian", "Vegan", "Gluten-free", "Halal"])
    requirements = st.text_area("Special Requirements", placeholder="Mobility needs, allergies, etc.")

# Interests section
interests = st.multiselect("Select Your Interests",
                          ["Historical Sites", "Local Food", "Nature", "Art & Museums",
                           "Shopping", "Nightlife", "Adventure Sports"])

# Generate button
if st.button("✨ Create My Travel Plan", use_container_width=True):
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
        
        with st.spinner("🧭 Crafting your personalized adventure..."):
            itinerary = generate_itinerary(user_input)
        
        if itinerary:
            st.success("🎉 Your Custom Travel Plan is Ready!")
            
            # Display itinerary
            st.subheader(f"Your {destination} Itinerary")
            st.markdown(itinerary, unsafe_allow_html=True)
            
            # Additional features
            with st.expander("📌 Travel Tips & Safety"):
                safety_tips = genai.GenerativeModel('gemini-pro').generate_content(
                    f"Generate safety tips for {destination} considering: {requirements}"
                ).text
                st.markdown(safety_tips)
            
            # Download options
            col1, col2 = st.columns(2)
            with col1:
                st.download_button("📥 Download Itinerary (TXT)",
                                  data=itinerary,
                                  file_name=f"{destination}_itinerary.txt")
            with col2:
                st.button("🗺️ Show Destination Map", 
                          help="Coming soon: Interactive map integration!")
        else:
            st.error("Failed to generate itinerary. Please try again.")
