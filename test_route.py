import requests
import json

# 1. The Endpoint
# This points to the Docker container running on your machine
VALHALLA_URL = "http://localhost:8002/route"

# 2. The Request Data (Andorra Coordinates)
# We are asking for a route between two points in Andorra la Vella
payload = {
    "locations": [
        {"lat": 42.5063, "lon": 1.5218, "type": "break"},  # Start
        {"lat": 42.5101, "lon": 1.5231, "type": "break"}   # End
    ],
    "costing": "auto",  # Drive mode (try "pedestrian" too!)
    "directions_options": {
        "units": "miles",
        "language": "en-US"
    }
}

# 3. Send the Request
try:
    response = requests.get(VALHALLA_URL, json=payload)
    
    # Check if it worked (Status 200 means OK)
    if response.status_code == 200:
        data = response.json()
        
        # 4. Parse and Print the Result
        trip = data['trip']
        print(f"✅ Success! Found a route.")
        print(f"🚗 Total Distance: {trip['summary']['length']} miles")
        print(f"⏱️  Total Time: {trip['summary']['time']} seconds")
        print("\n--- Directions ---")
        
        for maneuver in trip['legs'][0]['maneuvers']:
            print(f"• {maneuver['instruction']}")
            
    else:
        print(f"❌ Error {response.status_code}: {response.text}")

except requests.exceptions.ConnectionError:
    print("❌ Could not connect to Docker! Is the container running?")