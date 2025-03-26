import streamlit as st
import openai
import requests
from datetime import datetime

# OpenAI API Key (Replace with your own key)
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
openai.api_key = OPENAI_API_KEY

def get_travel_recommendations(destination):
    """Fetch travel recommendations from an external API (placeholder)."""
    url = f"https://api.example.com/travel?location={destination}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return {"error": "Unable to fetch travel data."}

def generate_itinerary(user_input):
    """Generate a personalized travel itinerary using OpenAI's GPT model."""
    prompt = f"""
    You are an AI travel planner. Based on the user's input:
    {user_input}
    Create a detailed day-by-day travel itinerary including accommodation, sightseeing, and local cuisine.
    """
    
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful AI travel planner."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# Streamlit UI
st.title("AI-Powered Travel Planner")

# User Inputs
name = st.text_input("Your Name")
destination = st.text_input("Destination")
budget = st.selectbox("Budget", ["Low", "Medium", "High"])
travel_dates = st.date_input("Travel Dates", value=(datetime.today(), datetime.today()))
preferences = st.text_area("Preferences (e.g., adventure, food, culture)")

if st.button("Generate Itinerary"):
    user_input = {
        "name": name,
        "destination": destination,
        "budget": budget,
        "travel_dates": str(travel_dates),
        "preferences": preferences,
    }
    itinerary = generate_itinerary(user_input)
    st.subheader("Your Personalized Itinerary")
    st.write(itinerary)
