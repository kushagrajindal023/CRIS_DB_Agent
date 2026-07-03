import sqlite3
import json

def generate_station_map():
    print("🔍 Connecting to the Railway Database...")
    conn = sqlite3.connect('railway.db')
    cursor = conn.cursor()

    station_dict = {}

    print("🚂 Extracting station codes...")
    
    # 1. Grab all the 'Starting' stations
    cursor.execute("SELECT DISTINCT from_station_name, from_station_code FROM trains WHERE from_station_name IS NOT NULL")
    for row in cursor.fetchall():
        name, code = row
        # Save it in lowercase so our filter catches it easily
        station_dict[name.lower()] = code

    # 2. Grab all the 'Destination' stations (to ensure we don't miss any)
    cursor.execute("SELECT DISTINCT to_station_name, to_station_code FROM trains WHERE to_station_name IS NOT NULL")
    for row in cursor.fetchall():
        name, code = row
        station_dict[name.lower()] = code

    conn.close()

    # 3. Save it as a clean JSON file
    print("📝 Writing to stations.json...")
    with open('stations.json', 'w') as f:
        json.dump(station_dict, f, indent=4)

    print(f"✅ Success! Created stations.json with {len(station_dict)} unique stations.")

if __name__ == "__main__":
    generate_station_map()