import pandas as pd
import streamlit as st
import plotly.express as px
from numpy.random import default_rng as rng

# Generate sample data with additional values to display
rng_gen = rng(0)
df = pd.read_csv('mockdata.csv')

# Sidebar for user inputs
st.sidebar.header("User Input Parameters")
long = st.sidebar.number_input("Longitude", value=-77.0)
lat = st.sidebar.number_input("Latitude", value=41.0)
urgent = st.sidebar.checkbox("Urgent", value=True)
admitted = st.sidebar.checkbox("Admitted", value=False)
max_wait_time = st.sidebar.number_input("Max Wait Time (minutes)", value=0, min_value=0)


st.title("Interactive Health Facilities Map")

# Create interactive map using Plotly
fig = px.scatter_mapbox(
    df,
    lat="lat",
    lon="long",
    hover_name="name",
    hover_data={
        "general_time": True,
        "high_time": True,
        "low_time": True,
        "admitted_time": True,
        "lat": False,
        "long": False
    },
    color_discrete_sequence=["blue"],
    size_max=15,
    zoom=10,
    height=600,
    title="Click on any point to see detailed information"
)

# Add user input point as red marker
user_point = pd.DataFrame({
    'lat': [lat],
    'long': [long],
    'name': ['Your Location']
})
fig.add_trace(
    px.scatter_mapbox(
        user_point,
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

if clicked_data and 'selection' in clicked_data and clicked_data['selection']['points']:
    # Get the clicked point data
    clicked_point = clicked_data['selection']['points'][0]
    point_index = clicked_point['point_index']
    
    # Check if the clicked point is not the user's location (red marker is the second trace)
    if clicked_point.get('curve_number') == 0:  # Only show details for facility points (first trace)
        selected_row = df.iloc[point_index]
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Name", selected_row['name'])
        with col2:
            st.metric("General Waiting Time", f"{selected_row['general_time']}")
        with col3:
            st.metric("High Urgent Waiting Time", f"{selected_row['high_time']}")
        with col4:
            st.metric("Low Urgent Waiting Time", f"{selected_row['low_time']}")
        with col5:
            st.metric("Waiting Time for Admitted Patients", f"{selected_row['admitted_time']}")
        
        # Show additional details in an info box
        st.info(f"You selected {selected_row['name']}")
    else:
        st.info("👆 Click on any facility point (blue) on the map to see detailed information.")
else:
    st.info("👆 Click on any point on the map to see detailed information about that location.")

# Display data table
if st.checkbox("Show raw data"):
    st.dataframe(df)