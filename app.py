import streamlit as st
import google.generativeai as genai
import requests
import json
from datetime import date, timedelta
import pandas as pd

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Travel Planner Pro",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- API Configuration ---
try:
    # Configure Gemini API
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Google Maps API for Places
    GOOGLE_MAPS_API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    # OpenWeatherMap API
    OPENWEATHER_API_KEY = st.secrets["OPENWEATHER_API_KEY"]
except KeyError:
    st.error("API keys not found! Please add GEMINI_API_KEY, GOOGLE_MAPS_API_KEY, and OPENWEATHER_API_KEY to your Streamlit secrets.", icon="🚨")
    st.stop()

# --- Helper Functions ---

def get_place_details(place_name, destination):
    search_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={place_name} in {destination}&key={GOOGLE_MAPS_API_KEY}"
    try:
        response = requests.get(search_url)
        response.raise_for_status()
        results = response.json().get('results', [])

        if not results:
            return None

        place_id = results[0]['place_id']
        details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,rating,formatted_address,photos,geometry&key={GOOGLE_MAPS_API_KEY}"
        
        details_response = requests.get(details_url)
        details_response.raise_for_status()
        place_data = details_response.json().get('result', {})

        details = {
            'name': place_data.get('name'),
            'rating': place_data.get('rating', 'N/A'),
            'address': place_data.get('formatted_address'),
            'lat': place_data.get('geometry', {}).get('location', {}).get('lat'),
            'lon': place_data.get('geometry', {}).get('location', {}).get('lng'),
            'photos': []
        }

        if 'photos' in place_data:
            for photo in place_data['photos'][:3]:
                photo_reference = photo['photo_reference']
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_reference}&key={GOOGLE_MAPS_API_KEY}"
                details['photos'].append(photo_url)
        
        if not details['photos']:
             details['photos'].append(f"https://placehold.co/400x300/E0E0E0/000000?text={place_name.replace(' ', '+')}")

        return details
    except requests.exceptions.RequestException as e:
        st.warning(f"Could not fetch details for '{place_name}': {e}", icon="⚠️")
        return None

def get_weather_forecast(lat, lon, start_date, duration):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        response.raise_for_status()
        weather_data = response.json()

        daily_forecasts = {}
        for item in weather_data['list']:
            day = item['dt_txt'].split(' ')[0]
            if day not in daily_forecasts:
                daily_forecasts[day] = {'temps': [], 'weather': []}
            daily_forecasts[day]['temps'].append(item['main']['temp'])
            daily_forecasts[day]['weather'].append(item['weather'][0])
        
        processed_forecast = []
        for day, data in daily_forecasts.items():
            avg_temp = sum(data['temps']) / len(data['temps'])
            main_weather = max(data['weather'], key=data['weather'].count)
            processed_forecast.append({
                'date': day,
                'avg_temp': round(avg_temp, 1),
                'condition': main_weather['main'],
                'icon': f"http://openweathermap.org/img/wn/{main_weather['icon']}@2x.png"
            })
        
        return processed_forecast[:duration]
    except requests.exceptions.RequestException as e:
        st.warning(f"Could not fetch weather data: {e}", icon="🌦️")
        return None

def get_local_info(destination):
    info = {
        'currency': "Local Currency (e.g., EUR, JPY)",
        'airport': "Nearest Major Airport (e.g., CDG, HND)",
        'transport_apps': "Local transport apps (e.g., Uber, Grab, DB Navigator)"
    }
    return info

def generate_itinerary_with_gemini(user_input):
    prompt = f"""
    You are an expert travel planner AI. Your task is to create a detailed and structured travel itinerary based on the user's request.
    
    **User Request:**
    - Destination: {user_input['destination']}
    - Duration: {user_input['duration']} days, starting on {user_input['start_date']}
    - Traveler Name: {user_input['name']}
    - Budget: {user_input['budget']}
    - Travel Style: {user_input['travel_style']}
    - Interests: {', '.join(user_input['interests'])}
    - Dietary Needs: {', '.join(user_input['dietary'])}
    - Special Requirements: {user_input['requirements']}

    **Output Format Instructions:**
    - Provide output as a valid JSON object with a root key: "trip".
    - "trip" must contain: "trip_title", "summary", "itinerary", "local_food_suggestions", "safety_tips".
    - "itinerary" array contains day objects with "day", "theme", "activities".
    - Each activity: "time_of_day", "poi_name", "description".

    Please generate the complete JSON output now.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_response)
    except (json.JSONDecodeError, Exception) as e:
        st.error(f"Error processing AI response: {e}", icon="🤖")
        st.error("The AI returned an invalid format. Please try generating again.", icon="🔄")
        return None

# --- Streamlit UI ---
with st.sidebar:
    st.image("https://placehold.co/300x100/3498db/ffffff?text=Travel+Planner&font=roboto", use_container_width=True)
    st.title("Trip Configuration ⚙️")
    st.markdown("---")
    name = st.text_input("Traveler Name", placeholder="E.g., Ruthik")
    travel_style = st.selectbox(
        "Travel Style",
        ["🏖️ Relaxing", "🧗 Adventure", "🏛️ Cultural", "🍜 Foodie", "👨‍👩‍👧‍👦 Family"]
    )
    num_days = st.slider("Trip Duration (Days)", 1, 21, 7)
    budget = st.select_slider(
        "Budget Level",
        options=["💰 Budget", "💵 Mid-range", "💎 Luxury"]
    )
    start_date = st.date_input("Start Date", date.today() + timedelta(days=14))

st.title("🌍 AI Travel Planner Pro")
st.markdown("Craft your next unforgettable journey with the power of AI.")
st.markdown("---")

st.header("Tell Us About Your Dream Trip ✨")
col1, col2 = st.columns(2)

with col1:
    destination = st.text_input("📍 Destination", placeholder="Country or City, e.g., Japan")
    interests = st.multiselect(
        "Your Interests",
        ["🏰 Historical Sites", "🍣 Local Cuisine", "🌳 Nature & Parks", "🎨 Art & Museums", "🛍️ Shopping", "🌃 Nightlife"],
        default=["🏰 Historical Sites", "🍣 Local Cuisine"]
    )

with col2:
    dietary = st.multiselect(
        "Dietary Needs",
        ["🍃 Vegetarian", "🌱 Vegan", "🌾 Gluten-Free", "🚫 Nut Allergy"]
    )
    requirements = st.text_area(
        "Special Requirements",
        placeholder="E.g., wheelchair accessibility, prefer ground floor, etc."
    )

if st.button("🚀 Generate My Itinerary!", use_container_width=True, type="primary"):
    if not destination or not name:
        st.warning("Please fill in the Traveler Name and Destination fields.", icon="✍️")
    else:
        user_input = {
            "name": name,
            "destination": destination,
            "budget": budget,
            "duration": num_days,
            "travel_style": travel_style,
            "dietary": dietary,
            "requirements": requirements,
            "interests": interests,
            "start_date": str(start_date)
        }
        with st.spinner("🧭 AI is crafting your personalized itinerary..."):
            itinerary_json = generate_itinerary_with_gemini(user_input)

        if itinerary_json:
            st.balloons()
            trip_data = itinerary_json.get('trip', {})
            itinerary_days = trip_data.get('itinerary', [])

            with st.spinner("Fetching location data and weather forecasts..."):
                map_points = []
                first_location = None
                for day in itinerary_days:
                    for activity in day.get('activities', []):
                        place_details = get_place_details(activity['poi_name'], destination)
                        if place_details and place_details.get('lat'):
                            activity['details'] = place_details
                            map_points.append({
                                'lat': place_details['lat'],
                                'lon': place_details['lon'],
                                'name': place_details['name']
                            })
                            if not first_location:
                                first_location = place_details
                        else:
                            activity['details'] = {
                                'photos': [f"https://placehold.co/400x300/E0E0E0/000000?text={activity['poi_name'].replace(' ', '+')}"]
                            }

            st.header(trip_data.get('trip_title', f"Your Trip to {destination}"))
            st.markdown(f"_{trip_data.get('summary', '')}_")
            st.markdown("---")

            info_col, map_col = st.columns([1, 2])
            with info_col:
                st.subheader("Quick Info ⚡")
                if first_location:
                    weather_forecast = get_weather_forecast(first_location['lat'], first_location['lon'], start_date, num_days)
                    if weather_forecast:
                        st.write("**Weather Forecast:**")
                        for day_weather in weather_forecast:
                            st.image(day_weather['icon'], width=30)
                            st.write(f"_{day_weather['date'][-5:]}_: {day_weather['avg_temp']}°C, {day_weather['condition']}")
                    else:
                        st.write("_Weather data not available._")
                local_info = get_local_info(destination)
                st.write(f"**Currency:** {local_info['currency']}")
                st.write(f"**Airport:** {local_info['airport']}")
                st.write(f"**Transport:** {local_info['transport_apps']}")

            with map_col:
                st.subheader("Trip Hotspots 🗺️")
                if map_points:
                    df = pd.DataFrame(map_points)
                    st.map(df, zoom=10)
                else:
                    st.write("No location data to display on map.")

            st.header("Your Day-by-Day Adventure 🗓️")
            for day in itinerary_days:
                with st.expander(f"**Day {day['day']}: {day['theme']}**", expanded=day['day']==1):
                    for activity in day.get('activities', []):
                        st.markdown(f"#### {activity['time_of_day']}: {activity['poi_name']}")
                        st.markdown(activity['description'])
                        
                        details = activity.get('details')
                        if details and details.get('photos'):
                            cols = st.columns(len(details['photos']))
                            for i, photo_url in enumerate(details['photos']):
                                with cols[i]:
                                    st.image(photo_url, use_container_width=True)

                            if details:
                                caption_parts = []
                                if details.get('address'):
                                    caption_parts.append(f"📍 {details['address']}")
                                if details.get('rating') != 'N/A':
                                    caption_parts.append(f"⭐ Rating: {details['rating']}")
                                if caption_parts:
                                    st.caption(" | ".join(caption_parts))

                        st.markdown("---")

            st.header("Local Delights & Tips 🍽️")
            food_col, safety_col = st.columns(2)
            with food_col:
                st.subheader("Local Foods to Try")
                foods = trip_data.get('local_food_suggestions', [])
                if foods:
                    st.markdown("\n".join([f"- {food}" for food in foods]))
                else:
                    st.write("No specific food suggestions available.")
            
            with safety_col:
                st.subheader("Safety & Cultural Notes")
                st.info(trip_data.get('safety_tips', "Always be aware of your surroundings and respect local customs."), icon="🛡️")
        else:
            st.error("Failed to generate itinerary. The AI may be busy or the request could not be processed. Please try again.", icon="❌")
