import json
import sqlite3
import urllib.request

print("1. Downloading raw JSON data from GitHub...")
# This automatically fetches the data directly from the source repository
urllib.request.urlretrieve(
    'https://raw.githubusercontent.com/datameet/railways/master/trains.json',
    'trains.json'
)
urllib.request.urlretrieve(
    'https://raw.githubusercontent.com/datameet/railways/master/stations.json',
    'stations.json'
)

print("2. Loading data into memory...")
with open('trains.json') as f:   
    trains = json.load(f)['features']
with open('stations.json') as f: 
    stations = json.load(f)['features']

print("3. Building SQLite database schema...")
# This creates the railway.db file locally
conn = sqlite3.connect('railway.db')
c = conn.cursor()

# Create the 'trains' table with all necessary columns
c.execute('''CREATE TABLE IF NOT EXISTS trains (
  number TEXT PRIMARY KEY, name TEXT, type TEXT, zone TEXT,
  from_station_code TEXT, from_station_name TEXT,
  to_station_code TEXT,   to_station_name TEXT,
  departure TEXT, arrival TEXT, duration_h INT, duration_m INT,
  distance INT, first_ac INT, second_ac INT, third_ac INT,
  sleeper INT, chair_car INT, first_class INT, return_train TEXT
)''')

# Create the 'stations' table
c.execute('''CREATE TABLE IF NOT EXISTS stations (
  code TEXT PRIMARY KEY, name TEXT, zone TEXT, state TEXT, address TEXT
)''')

print("4. Inserting data into tables (this might take a few seconds)...")
# Loop through the JSON data and insert it into the SQL tables
for f in trains:
    p = f['properties']
    c.execute('INSERT OR REPLACE INTO trains VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
      (p.get('number'), p.get('name'), p.get('type'), p.get('zone'),
       p.get('from_station_code'), p.get('from_station_name'),
       p.get('to_station_code'),   p.get('to_station_name'),
       p.get('departure'), p.get('arrival'),
       p.get('duration_h',0), p.get('duration_m',0), p.get('distance',0),
       p.get('first_ac',0), p.get('second_ac',0), p.get('third_ac',0),
       p.get('sleeper',0), p.get('chair_car',0), p.get('first_class',0),
       p.get('return_train')))

for f in stations:
    p = f['properties']
    c.execute('INSERT OR REPLACE INTO stations VALUES (?,?,?,?,?)',
      (p.get('code'), p.get('name'), p.get('zone'), p.get('state'), p.get('address')))

# Save the changes and close the connection
conn.commit()

print('\nSuccess! Database is built and ready.')
print('Total Trains Inserted:', c.execute('SELECT COUNT(*) FROM trains').fetchone()[0])
print('Total Stations Inserted:', c.execute('SELECT COUNT(*) FROM stations').fetchone()[0])
conn.close()