import pandas as pd
from numpy.random import default_rng as rng
import matplotlib.pyplot as plt
from math import radians, sin, cos, sqrt, atan2

import streamlit as st
import plotly.express as px

# Preprocessing
from sklearn.preprocessing import MinMaxScaler

# KNN Neighbors
from sklearn.neighbors import NearestNeighbors

# API Library
import googlemaps
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
if api_key:
    print("API key loaded successfully.")

else:
    print("Error: GOOGLE_MAPS_API_KEY not found in .env file.")

# Google Map API
# gmaps = googlemaps.Client(key='AIzaSyC8rYABHda_kA9MqFU7TMeHbEwB_7VEpUw')
gmaps = googlemaps.Client(key=api_key)


# Generate sample data with additional values to display
rng_gen = rng(0)
df = pd.read_csv('hospital_ed_merged_with_geo.csv')

# Sidebar for user inputs
st.sidebar.header("User Input Parameters")
# long = st.sidebar.slider("Longitude", min_value=-86.0, max_value=-70.0, value=-77.0)
# lat = st.sidebar.slider("Latitude", min_value=38.0, max_value=48.0, value=41.0)
address = st.sidebar.text_input("Enter your address:", "2247 Hurontario, Mississauga, ON, Canada")
urgent = st.sidebar.checkbox("Urgent", value=True)
admitted = st.sidebar.checkbox("Admitted", value=False)
max_wait_time = st.sidebar.slider("Max Wait Time (minutes)", min_value=0, max_value=180, value=0)/60 # in hours


st.title("Ontario Swift ER")

######## BACK END DATA PROCESSING ########
# Geocode user address to get lat/long
geocode_result = gmaps.geocode(address)
if geocode_result:
    location = geocode_result[0]['geometry']['location']
    lat = location['lat']
    long = location['lng']
else:
    st.error("Could not geocode the provided address. Please check the address and try again.")
    st.stop()

# if urgent and not admitted:
#     wait_col = 'LS_E_HU_NA'
# elif not urgent and not admitted:
#     wait_col = 'LS_E_LU_NA'
# elif admitted:
#     wait_col = 'LS_E_A'
# else:
#     wait_col = 'WT_FA_E'
wait_col = 'WT_FA_E'  # Always use First Assessment wait time for simplicity

# Add wait time with travel time buffer
# Define origin and destination coordinates
# Calculate total wait time (hospital wait + travel time) for each hospital

def parse_travel_time(duration_text):
    """Parse travel duration text and convert to hours"""
    try:
        duration_text = duration_text.lower()
        total_hours = 0
        
        # Handle hours
        if 'hour' in duration_text:
            hours_part = duration_text.split('hour')[0].strip()
            if hours_part:
                total_hours += float(hours_part.split()[-1])
        
        # Handle minutes
        if 'min' in duration_text:
            # Extract the minutes part
            if 'hour' in duration_text:
                # Format like "1 hour 30 mins"
                mins_part = duration_text.split('hour')[1].split('min')[0].strip()
            else:
                # Format like "30 mins"
                mins_part = duration_text.split('min')[0].strip()
            
            if mins_part:
                minutes = float(mins_part.split()[-1])
                total_hours += minutes / 60
        
        return total_hours
    except:
        return 0

# Initialize session state for caching travel times
if 'travel_times_cache' not in st.session_state:
    st.session_state.travel_times_cache = {}
if 'last_address' not in st.session_state:
    st.session_state.last_address = ""

# Check if address has changed
address_changed = st.session_state.last_address != address

if address_changed or f"{address}_travel_times" not in st.session_state:
    st.info("🚗 Calculating travel times for new address...")
    
    # Show progress bar for API calls
    progress_bar = st.progress(0)
    status_text = st.empty()

    total_wait_times = []
    travel_times_cache = {}  # Cache to avoid duplicate API calls

    for idx, row in df.iterrows():
        # Update progress
        progress = (idx + 1) / len(df)
        progress_bar.progress(progress)
        status_text.text(f"Calculating travel times... {idx + 1}/{len(df)} hospitals")
        
        origin = address
        destination = row['ADDRESS']
        
        # Check cache first
        cache_key = f"{origin}|{destination}"
        
        if cache_key in travel_times_cache:
            travel_time_hours = travel_times_cache[cache_key]
        else:
            try:
                result = gmaps.distance_matrix(origin, destination, mode='driving', units='metric')
                
                if (result['rows'] and 
                    result['rows'][0]['elements'] and 
                    result['rows'][0]['elements'][0]['status'] == 'OK'):
                    
                    travel_duration_text = result['rows'][0]['elements'][0]['duration']['text']
                    travel_time_hours = parse_travel_time(travel_duration_text)
                    
                    # Store in cache
                    travel_times_cache[cache_key] = travel_time_hours
                    
                    # Add small delay to avoid rate limiting
                    import time
                    time.sleep(0.1)
                else:
                    travel_time_hours = 0
                    travel_times_cache[cache_key] = 0
                    
            except Exception as e:
                st.warning(f"Error calculating travel time to {row['HOSPITAL']}: {str(e)}")
                travel_time_hours = 0
                travel_times_cache[cache_key] = 0
        
        # Calculate total wait time
        total_wait = row[wait_col] + travel_time_hours
        total_wait_times.append(total_wait)

    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
    
    # Store results in session state
    st.session_state[f"{address}_travel_times"] = travel_times_cache
    st.session_state[f"{address}_total_wait_times"] = total_wait_times
    st.session_state.last_address = address
    
    st.success("✅ Travel times calculated successfully!")
    
else:
    # Use cached results
    travel_times_cache = st.session_state[f"{address}_travel_times"]
    total_wait_times = st.session_state[f"{address}_total_wait_times"]

df['wait_time'] = total_wait_times
df['travel_time'] = [travel_times_cache.get(f"{address}|{row['ADDRESS']}", 0) for _, row in df.iterrows()]

# Display some statistics for debugging
st.write(f"📊 Travel times for {len(df)} hospitals from your location:")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Minimum travel time", f"{min(df['travel_time']):.2f} hrs")
with col2:
    st.metric("Maximum travel time", f"{max(df['travel_time']):.2f} hrs")  
with col3:
    st.metric("Average travel time", f"{df['travel_time'].mean():.2f} hrs")


# Function to calculate Haversine distance
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance

# Column for distance calculation
df["distance"] = df.apply(
    lambda row: haversine(lat, long, row["LATITUDE"], row["LONGITUDE"]),
    axis=1
)

# Normalize distance and wait time
scaler = MinMaxScaler()
df[["norm_distance", "norm_wait_time"]] = scaler.fit_transform(df[["distance", "wait_time"]])

# Weight distances more heavily
df["knn_distance"] = df["norm_distance"] * 3   # weight distance ×3
df["knn_wait"] = df["norm_wait_time"] * 1      # wait time normal weight

# User point (0 distance, max wait)
user_point = [[0, max_wait_time]]
user_point_scaled = scaler.transform(user_point)

user_point_knn = [[
    user_point_scaled[0][0] * 3,   # weighted distance
    user_point_scaled[0][1] * 1    # weighted wait
]]

# KNN to find nearest facilities based on combined metric
try:
    knn = NearestNeighbors(n_neighbors=5, metric='euclidean')
    knn.fit(df[["knn_distance", "knn_wait"]])
    distances, indices = knn.kneighbors(user_point_knn)
    
    # Create color mapping for recommended facilities
    df['color'] = 'blue'  # default color for all facilities
    df.loc[indices[0], 'color'] = 'green'  # recommended facilities in green
except Exception as e:
    st.error("Data not available. Unable to calculate recommendations.")
    st.stop()

# Create interactive map using Plotly
fig = px.scatter_mapbox(
    df,
    lat="LATITUDE",
    lon="LONGITUDE",
    hover_name="HOSPITAL",
    hover_data={
        # "ADDRESS": True,
        "LATITUDE": False,
        "LONGITUDE": False,
        "color": False
    },
    color="color",
    color_discrete_map={"blue": "blue", "green": "green"},
    size_max=15,
    zoom=6,
    height=800,
    title="Click on any point to see detailed information"
)

# Add user input point as red marker
user_location_df = pd.DataFrame({
    'lat': [lat],
    'long': [long],
    'name': ['Your Location']
})
fig.add_trace(
    px.scatter_mapbox(
        user_location_df,
        hover_name='name',
        hover_data={'lat': False, 'long': False},
        lat='lat',
        lon='long',
        color_discrete_sequence=['red']
    ).data[0]
)

# Set the map style
fig.update_layout(mapbox_style="open-street-map")
fig.update_layout(margin={"r":0,"t":50,"l":0,"b":0})

# Display the interactive map with click events
clicked_data = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")

# Handle map click events
st.subheader("Selected Location Details")
st.write("Click on any point on the map above to see its details")

if clicked_data and clicked_data.selection and clicked_data.selection.points:
    
    # Get the selected point's name from the hover_name
    selected_point = clicked_data.selection.points[0]
    hospital_name = selected_point.get('hovertext') or selected_point.get('customdata')
    
    if hospital_name and hospital_name != 'Your Location':
        # Find the hospital by name
        hospital_matches = df[df['HOSPITAL'] == hospital_name]
        
        if len(hospital_matches) > 0:
            selected_hospital = hospital_matches.iloc[0]
            
            # Using Google Map API to find Travel Time from user location to selected hospital
            origin = address 
            destination = selected_hospital['ADDRESS']

            try:
                result = gmaps.distance_matrix(origin, destination, mode='driving')
                
                # Display hospital name
                st.markdown(f"### {selected_hospital['HOSPITAL']}")
                    
                # Display Address and Travel Time
                st.markdown(f"**Address:** {selected_hospital['ADDRESS']}")
                
                if result['rows'][0]['elements'][0]['status'] == 'OK':
                    travel_duration = result['rows'][0]['elements'][0]['duration']['text']
                    travel_distance = result['rows'][0]['elements'][0]['distance']['text']
                    st.markdown(f"**Estimated Travel Time:** {travel_duration}")
                    st.markdown(f"**Travel Distance:** {travel_distance}")
                    
                    # Get the cached travel time from the dataframe
                    travel_time_hours = selected_hospital['travel_time']
                else:
                    st.warning("Could not calculate travel time to this location.")
                    travel_time_hours = 0
                
                # Display waiting times with First Assessment prominent
                st.markdown("**Waiting Times:**")
                
                # First Assessment - Large display on its own row
                st.markdown("#### 🏥 First Assessment")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Wait Time", 
                        f"{selected_hospital['WT_FA_E']:.2f} hrs",
                        help="Time to first assessment at the hospital"
                    )
                with col2:
                    st.metric(
                        "Total Time (Wait + Travel)", 
                        f"{selected_hospital['WT_FA_E'] + travel_time_hours:.2f} hrs",
                        help="Including travel time to the hospital"
                    )
                
                st.markdown("---")  # Separator line
                
                # Other waiting times - Smaller display on second row
                st.markdown("##### Other Emergency Department Wait Times")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**High Urgency (Not Admitted)**")
                    st.write(f"Wait: {selected_hospital['LS_E_HU_NA']:.2f} hrs")
                    st.write(f"Total: {selected_hospital['LS_E_HU_NA'] + travel_time_hours:.2f} hrs")
                    
                with col2:
                    st.markdown("**Low Urgency (Not Admitted)**")
                    st.write(f"Wait: {selected_hospital['LS_E_LU_NA']:.2f} hrs")
                    st.write(f"Total: {selected_hospital['LS_E_LU_NA'] + travel_time_hours:.2f} hrs")
                    
                with col3:
                    st.markdown("**Admitted Patients**")
                    st.write(f"Wait: {selected_hospital['LS_E_A']:.2f} hrs")
                    st.write(f"Total: {selected_hospital['LS_E_A'] + travel_time_hours:.2f} hrs")
                
                # Show if this is a recommended hospital
                if selected_hospital['color'] == 'green':
                    st.success("✅ This is one of our top 5 recommended hospitals based on your criteria!")
                    
            except Exception as e:
                st.error(f"Error getting travel information: {str(e)}")
                # Still show basic hospital info even if travel API fails
                st.markdown(f"### {selected_hospital['HOSPITAL']}")
                st.markdown(f"**Address:** {selected_hospital['ADDRESS']}")
                st.write(f"- Distance from your location: {selected_hospital['distance']:.2f} km")
        else:
            st.warning(f"Could not find hospital information for: {hospital_name}")
    elif hospital_name == 'Your Location':
        st.info("You clicked on your location (red marker). Click on a hospital point (blue/green) to see details.")
    else:
        st.warning("Could not identify the selected point.")
else:
    st.info("👆 Click on any hospital point (blue/green) on the map to see detailed information.")

    # Display top 5 recommended hospitals
    st.subheader("Top 5 Recommended Hospitals")

    # Get the recommended hospitals (indices from KNN)
    top_5_hospitals = df.iloc[indices[0]].copy()

    # Add rank column
    top_5_hospitals.insert(0, 'Rank', range(1, 6))

    # Select relevant columns for display
    display_columns = ['Rank', 'HOSPITAL', 'ADDRESS', 'distance', 'wait_time']
    top_5_display = top_5_hospitals[display_columns].copy()

    # Rename columns for better presentation
    top_5_display.columns = ['Rank', 'Hospital Name', 'Address', 'Distance (km)', 'Total Time (hrs)']
    # Format numeric columns
    top_5_display['Distance (km)'] = top_5_display['Distance (km)'].apply(lambda x: f"{x:.2f}")
    top_5_display['Total Time (hrs)'] = top_5_display['Total Time (hrs)'].apply(lambda x: f"{x:.2f}")

    # Display the table
    st.dataframe(top_5_display, use_container_width=True, hide_index=True)

