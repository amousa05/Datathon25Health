import pandas as pd
import streamlit as st
import plotly.express as px
from numpy.random import default_rng as rng

# Generate sample data with additional values to display
rng_gen = rng(0)
df = pd.DataFrame(
    rng_gen.standard_normal((1000, 2)) / [50, 50] + [37.76, -122.4],
    columns=["lat", "lon"],
)

# Add some extra values that will be shown on hover/click
df['location_id'] = range(1, len(df) + 1)
df['population'] = rng_gen.integers(100, 10000, size=len(df))
df['hospital_rating'] = rng_gen.uniform(1, 5, size=len(df)).round(1)
df['facility_type'] = rng_gen.choice(['Hospital', 'Clinic', 'Urgent Care', 'Pharmacy'], size=len(df))

st.title("Interactive Health Facilities Map")

# Create interactive map using Plotly
fig = px.scatter_mapbox(
    df,
    lat="lat",
    lon="lon",
    hover_name="facility_type",
    hover_data={
        "location_id": True,
        "population": True,
        "hospital_rating": True,
        "lat": ":.4f",
        "lon": ":.4f"
    },
    color="facility_type",
    size="population",
    size_max=15,
    zoom=10,
    height=600,
    title="Click on any point to see detailed information"
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
    selected_row = df.iloc[point_index]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Location ID", selected_row['location_id'])
    with col2:
        st.metric("Population Served", f"{selected_row['population']:,}")
    with col3:
        st.metric("Rating", f"{selected_row['hospital_rating']}/5")
    with col4:
        st.metric("Facility Type", selected_row['facility_type'])
    
    st.write(f"**Coordinates:** {selected_row['lat']:.4f}, {selected_row['lon']:.4f}")
    
    # Show additional details in an info box
    st.info(f"You selected {selected_row['facility_type']} at location {selected_row['location_id']} with a rating of {selected_row['hospital_rating']}/5")
else:
    st.info("👆 Click on any point on the map to see detailed information about that location.")

# Display data table
if st.checkbox("Show raw data"):
    st.dataframe(df)