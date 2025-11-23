import googlemaps
from datetime import datetime

gmaps = googlemaps.Client(key='AIzaSyC8rYABHda_kA9MqFU7TMeHbEwB_7VEpUw')

# Define origin and destination coordinates
origin = ("2247 Hurontario")  # Example: New York City
destination = ("Toronto General Hospital, Toronto, ON")  # Example: Los Angeles

# Get distance matrix
result = gmaps.distance_matrix(origin, destination, mode='driving')

# Extract distance and duration
distance = result['rows'][0]['elements'][0]['distance']['text']
duration = result['rows'][0]['elements'][0]['duration']['text']

print(f"Distance: {distance}")
print(f"Duration: {duration}")

# Define the address you want to convert
address_to_geocode = "1200 Fourth Avenue, St. Catharines, ON, Canada"

# --- Geocoding Function ---
def geocode_address(address):
    # Call the Geocoding API
    try:
        geocode_result = gmaps.geocode(address)
    except Exception as e:
        print(f"An error occurred during geocoding: {e}")
        return None

    # Check if a result was returned
    if geocode_result:
        # The result is a list, typically we take the first match (index 0)
        first_result = geocode_result[0]
        
        # Extract the location data (latitude and longitude)
        location = first_result['geometry']['location']
        
        latitude = location['lat']
        longitude = location['lng']
        
        # Get the full formatted address and place ID for confirmation
        formatted_address = first_result.get('formatted_address', 'N/A')
        place_id = first_result.get('place_id', 'N/A')
        
        print(f"--- Geocoding Successful ---")
        print(f"Address: {formatted_address}")
        print(f"Place ID: {place_id}")
        print(f"Latitude: {latitude}")
        print(f"Longitude: {longitude}")
        
        return latitude, longitude
    else:
        print(f"Could not find coordinates for the address: {address}")
        return None

# Run the function with the example address
geocode_address(address_to_geocode)