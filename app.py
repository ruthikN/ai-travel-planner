# app.py
import streamlit as st
import google.generativeai as genai
import requests
import json
from datetime import date, timedelta
import pandas as pd
import pydeck as pdk

# --- Page Configuration ---
st.set_page_config(
    page_title="Odyssey AI Travel Planner",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- API Key Configuration ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    GOOGLE_MAPS_API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    OPENWEATHER_API_KEY = st.secrets["OPENWEATHER_API_KEY"]
except KeyError:
    st.error("🚨 API keys not found! Please add GEMINI_API_KEY, GOOGLE_MAPS_API_KEY, and OPENWEATHER_API_KEY to your Streamlit secrets.", icon="🚨")
    st.stop()

# --- Session State Initialization ---
if "itinerary_data" not in st.session_state:
    st.session_state.itinerary_data = None
if "map_data" not in st.session_state:
    st.session_state.map_data = None
if "center_lat" not in st.session_state:
    st.session_state.center_lat = 35.6895
if "center_lon" not in st.session_state:
    st.session_state.center_lon = 139.6917 # Default to Tokyo

# --- Helper Functions for API Calls ---

def get_place_details(place_name, destination):
    """Fetches rich details for a place using Google Places API."""
    search_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={place_name} in {destination}&key={GOOGLE_MAPS_API_KEY}"
    try:
        response = requests.get(search_url)
        response.raise_for_status()
        results = response.json().get('results', [])
        if not results: return None

        place_id = results[0]['place_id']
        details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,rating,formatted_address,photos,geometry,website,url&key={GOOGLE_MAPS_API_KEY}"
        details_response = requests.get(details_url)
        details_response.raise_for_status()
        place_data = details_response.json().get('result', {})

        details = {
            'name': place_data.get('name'),
            'rating': place_data.get('rating', 'N/A'),
            'address': place_data.get('formatted_address'),
            'lat': place_data.get('geometry', {}).get('location', {}).get('lat'),
            'lon': place_data.get('geometry', {}).get('location', {}).get('lng'),
            'website': place_data.get('website'),
            'map_url': place_data.get('url'),
            'photos': []
        }

        if 'photos' in place_data:
            for photo in place_data['photos'][:3]:
                photo_ref = photo['photo_reference']
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_ref}&key={GOOGLE_MAPS_API_KEY}"
                details['photos'].append(photo_url)
        
        if not details['photos']:
            details['photos'].append(f"https://placehold.co/400x300/E0E0E0/000000?text={place_name.replace(' ', '+')}")
            
        return details
    except requests.exceptions.RequestException as e:
        st.warning(f"⚠️ Could not fetch details for '{place_name}': {e}")
        return None

def get_directions_and_route(origin_lat, origin_lon, dest_lat, dest_lon, mode='transit'):
    """Fetches directions and decodes the route polyline using Google Directions API."""
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin_lat},{origin_lon}&destination={dest_lat},{dest_lon}&mode={mode}&key={GOOGLE_MAPS_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data['status'] != 'OK' or not data['routes']: return None, "N/A"

        route = data['routes'][0]['legs'][0]
        duration = route['duration']['text']
        
        # Decode polyline
        polyline_str = data['routes'][0]['overview_polyline']['points']
        
        # This is a basic decoding algorithm. For production, a library like `polyline` is better.
        def decode_polyline(polyline_str):
            index, lat, lng = 0, 0, 0
            coordinates = []
            changes = {'latitude': 0, 'longitude': 0}
            while index < len(polyline_str):
                for unit in ['latitude', 'longitude']:
                    shift, result = 0, 0
                    while True:
                        byte = ord(polyline_str[index]) - 63
                        index += 1
                        result |= (byte & 0x1f) << shift
                        shift += 5
                        if not byte >= 0x20:
                            break
                    if result & 1:
                        changes[unit] = ~(result >> 1)
                    else:
                        changes[unit] = (result >> 1)
                lat += changes['latitude']
                lng += changes['longitude']
                coordinates.append((lng / 1e5, lat / 1e5))
            return coordinates

        path = decode_polyline(polyline_str)
        return path, duration
    except requests.exceptions.RequestException as e:
        st.warning(f"⚠️ Could not fetch directions: {e}")
        return None, "N/A"

def get_weather_forecast(lat, lon, start_date, duration):
    """Fetches weather forecast for the trip duration (up to 5 days free)."""
    # ... (Your existing get_weather_forecast function can be used here without change) ...
    # For brevity, I'll keep it as is.
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        response.raise_for_status()
        weather_data = response.json()
        daily_forecasts = {}
        for item in weather_data['list']:
            day = item['dt_txt'].split(' ')[0]
            if day not in daily_forecasts: daily_forecasts[day] = {'temps': [], 'weather': []}
            daily_forecasts[day]['temps'].append(item['main']['temp'])
            daily_forecasts[day]['weather'].append(item['weather'][0])
        processed_forecast = []
        for day, data in daily_forecasts.items():
            avg_temp = sum(data['temps']) / len(data['temps'])
            main_weather = max(data['weather'], key=data['weather'].count)
            processed_forecast.append({
                'date': day, 'avg_temp': round(avg_temp, 1),
                'condition': main_weather['main'],
                'icon': f"http://openweathermap.org/img/wn/{main_weather['icon']}@2x.png"
            })
        return processed_forecast[:duration]
    except requests.exceptions.RequestException:
        return None
        
def find_hotels_nearby(lat, lon):
    """Finds hotels near a given coordinate using Google Places API Nearby Search."""
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lon}&radius=2000&type=lodging&key={GOOGLE_MAPS_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        results = response.json().get('results', [])
        hotels = []
        for place in results[:10]: # Get top 10
            hotels.append({
                "name": place.get('name'),
                "rating": place.get('rating', 'N/A'),
                "vicinity": place.get('vicinity')
            })
        return hotels
    except requests.exceptions.RequestException:
        return []

def get_destination_coords(destination):
    """Gets the central coordinates of a destination using Geocoding API."""
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={destination}&key={GOOGLE_MAPS_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
    except requests.exceptions.RequestException:
        return None, None

def generate_itinerary_with_gemini(user_input):
    """Generates a structured travel itinerary using Gemini 1.5 Pro."""
    prompt = f"""
    You are an expert travel planner AI. Create a detailed, exciting, and logical travel itinerary.
    Your output MUST be a valid JSON object, with no markdown formatting before or after.

    **User Request:**
    - Destination: {user_input['destination']}
    - Duration: {user_input['duration']} days, starting on {user_input['start_date']}
    - Budget: {user_input['budget']}
    - Travel Style: {user_input['travel_style']}
    - Interests: {', '.join(user_input['interests'])}
    - Dietary Needs: {', '.join(user_input['dietary'])}

    **JSON Output Structure:**
    {{
      "trip": {{
        "trip_title": "A creative title for the trip.",
        "summary": "An engaging 2-3 sentence summary of the trip.",
        "itinerary": [ 
          {{
            "day": 1,
            "theme": "A theme for the day (e.g., 'Historical Heart & Culinary Kickstart').",
            "activities": [
              {{
                "time_of_day": "Morning",
                "poi_name": "Specific Name of a Place of Interest (e.g., 'Tokyo National Museum').",
                "category": "Museum",
                "description": "A 2-3 sentence description of the activity.",
                "estimated_duration_mins": 180
              }},
              {{
                "time_of_day": "Afternoon",
                "poi_name": "Specific Name of a Restaurant or Cafe (e.g., 'Ichiran Ramen Ueno').",
                "category": "Restaurant",
                "description": "Why this place is a good choice for lunch, fitting the user's needs.",
                "estimated_duration_mins": 60
              }},
              {{
                "time_of_day": "Evening",
                "poi_name": "Specific Name of an evening activity (e.g., 'Tokyo Skytree').",
                "category": "Viewpoint",
                "description": "Description of the evening experience.",
                "estimated_duration_mins": 120
              }}
            ]
          }}
          // ... more day objects
        ],
        "local_food_suggestions": ["List of local dishes to try."],
        "safety_tips": "Essential safety and cultural tips for the destination."
      }}
    }}

    Generate the complete JSON object now based on the user request.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_response)
    except (json.JSONDecodeError, Exception) as e:
        st.error(f"🤖 Error processing AI response: {e}. Please try again.")
        st.code(response.text) # For debugging
        return None


# --- Streamlit UI ---

# --- Sidebar ---
with st.sidebar:
    st.image("https://placehold.co/300x100/3498db/ffffff?text=Odyssey+AI&font=roboto", use_column_width=True)
    st.title("🚀 Trip Configuration")
    st.markdown("---")
    
    name = st.text_input("Traveler Name", placeholder="E.g., Alex")
    destination = st.text_input("📍 Destination", placeholder="Country or City, e.g., Tokyo")
    
    col1, col2 = st.columns(2)
    with col1:
        num_days = st.slider("Trip Duration (Days)", 1, 14, 5)
    with col2:
        start_date = st.date_input("Start Date", date.today() + timedelta(days=14))

    budget = st.select_slider(
        "Budget Level",
        options=["💰 Budget", "💵 Mid-range", "💎 Luxury"]
    )
    travel_style = st.selectbox(
        "Travel Style",
        ["🏖️ Relaxing", "🧗 Adventure", "🏛️ Cultural", "🍜 Foodie", "👨‍👩‍👧‍👦 Family"]
    )
    interests = st.multiselect(
        "Your Interests",
        ["🏰 History", "🍣 Cuisine", "🌳 Nature", "🎨 Art & Museums", "🛍️ Shopping", "🌃 Nightlife"],
        default=["🏰 History", "🍣 Cuisine"]
    )
    dietary = st.multiselect(
        "Dietary Needs",
        ["🍃 Vegetarian", "🌱 Vegan", "🌾 Gluten-Free", "🚫 Nut Allergy"]
    )

    if st.button("✨ Generate My Epic Trip!", use_container_width=True, type="primary"):
        if not destination or not name:
            st.warning("Please fill in the Traveler Name and Destination.", icon="✍️")
        else:
            with st.spinner("🧠 AI is brainstorming your itinerary..."):
                user_input = {
                    "name": name, "destination": destination, "budget": budget,
                    "duration": num_days, "travel_style": travel_style,
                    "dietary": dietary, "interests": interests, "start_date": str(start_date)
                }
                itinerary_json = generate_itinerary_with_gemini(user_input)
                st.session_state.itinerary_data = itinerary_json

            if st.session_state.itinerary_data:
                with st.spinner("🌍 Fetching location data and calculating routes..."):
                    # Enrich data with details and routes
                    trip_data = st.session_state.itinerary_data.get('trip', {})
                    itinerary_days = trip_data.get('itinerary', [])
                    
                    st.session_state.center_lat, st.session_state.center_lon = get_destination_coords(destination)

                    all_points = []
                    route_layers = []
                    
                    for day_index, day in enumerate(itinerary_days):
                        day_points = []
                        for activity in day.get('activities', []):
                            details = get_place_details(activity['poi_name'], destination)
                            activity['details'] = details
                            if details and details.get('lat'):
                                point = {'lat': details['lat'], 'lon': details['lon'], 'name': details['name'], 'day': day['day']}
                                day_points.append(point)
                                all_points.append(point)

                        # Calculate routes between activities for the day
                        for i in range(len(day_points) - 1):
                            origin = day_points[i]
                            dest = day_points[i+1]
                            path, duration = get_directions_and_route(origin['lat'], origin['lon'], dest['lat'], dest['lon'])
                            # Find the corresponding activity and add duration
                            day['activities'][i+1]['travel_from_previous'] = f"~ {duration} by transit"
                            if path:
                                route_layers.append(pdk.Layer(
                                    "PathLayer",
                                    data=pd.DataFrame([{'path': path}]),
                                    get_path='path',
                                    width_scale=20,
                                    width_min_pixels=2,
                                    get_color=[255, 0, 0, 200] if day['day'] == 1 else [0, 0, 255, 200] if day['day'] == 2 else [0, 255, 0, 200], # Simple color coding
                                    pickable=True
                                ))

                    st.session_state.map_data = {"points": all_points, "routes": route_layers}
                    st.balloons()


# --- Main Interface ---
st.title("🗺️ Odyssey AI Travel Planner")
st.markdown("Your intelligent guide to crafting the perfect, personalized adventure.")
st.markdown("---")

if not st.session_state.itinerary_data:
    st.info("Fill out your trip details in the sidebar to generate your personalized itinerary!")

if st.session_state.itinerary_data:
    trip_data = st.session_state.itinerary_data.get('trip', {})
    st.header(trip_data.get('trip_title', f"Your Trip to {destination}"))
    st.markdown(f"_{trip_data.get('summary', '')}_")

    tab1, tab2, tab3 = st.tabs(["**📅 Itinerary**", "**📍 Routes & Map**", "**🏨 Hotels & Logistics**"])

    with tab1:
        st.header("Your Day-by-Day Adventure")
        for day in trip_data.get('itinerary', []):
            with st.expander(f"**Day {day['day']}: {day['theme']}**", expanded=day['day']==1):
                for activity in day.get('activities', []):
                    st.subheader(f"{activity['time_of_day']}: {activity['poi_name']}")
                    
                    if 'travel_from_previous' in activity:
                        st.caption(f"🚗 **Travel:** {activity['travel_from_previous']}")

                    st.markdown(activity['description'])
                    
                    details = activity.get('details')
                    if details:
                        if details.get('photos'):
                            st.image(details['photos'][0], use_column_width=True, caption=f"⭐ Rating: {details.get('rating', 'N/A')}")
                        st.caption(f"📍 [{details.get('address')}]({details.get('map_url')})")
                    
                    st.markdown("---")

    with tab2:
        st.header("Trip Hotspots & Daily Routes")
        if st.session_state.map_data and st.session_state.map_data['points']:
            df = pd.DataFrame(st.session_state.map_data['points'])
            
            view_state = pdk.ViewState(
                latitude=st.session_state.center_lat,
                longitude=st.session_state.center_lon,
                zoom=11,
                pitch=50,
            )

            point_layer = pdk.Layer(
                "ScatterplotLayer",
                data=df,
                get_position='[lon, lat]',
                get_color='[200, 30, 0, 160]',
                get_radius=100,
                pickable=True,
                tooltip={"text": "{name}\nDay: {day}"}
            )

            st.pydeck_chart(pdk.Deck(
                map_style='mapbox://styles/mapbox/light-v9',
                initial_view_state=view_state,
                layers=[point_layer] + st.session_state.map_data.get('routes', [])
            ))
        else:
            st.warning("No map data available. Please generate an itinerary first.")

    with tab3:
        st.header("Logistics & Local Tips")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🏨 Hotel Suggestions")
            st.info("These are hotels near the city center. You can use these as a starting point for your search.")
            if st.session_state.center_lat:
                hotels = find_hotels_nearby(st.session_state.center_lat, st.session_state.center_lon)
                if hotels:
                    for hotel in hotels:
                        st.write(f"**{hotel['name']}** - ⭐ {hotel['rating']}\n\n*_{hotel['vicinity']}_*")
                else:
                    st.write("Could not find hotels.")
            
            st.subheader("🌦️ Weather Forecast")
            if st.session_state.center_lat:
                weather = get_weather_forecast(st.session_state.center_lat, st.session_state.center_lon, start_date, num_days)
                if weather:
                    for day_weather in weather:
                        col_icon, col_text = st.columns([1, 4])
                        with col_icon:
                            st.image(day_weather['icon'], width=40)
                        with col_text:
                            st.write(f"**{date.fromisoformat(day_weather['date']).strftime('%b %d')}**: {day_weather['avg_temp']}°C, {day_weather['condition']}")
                else:
                    st.write("Weather data not available.")

        with col2:
            st.subheader("🍽️ Local Foods to Try")
            foods = trip_data.get('local_food_suggestions', [])
            if foods:
                st.markdown("\n".join([f"- {food}" for food in foods]))
            
            st.subheader("🛡️ Safety & Cultural Notes")
            st.warning(trip_data.get('safety_tips', "Always be aware of your surroundings and respect local customs."))
