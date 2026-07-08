import osmnx as ox
import networkx as nx
import geopandas as gpd
from shapely.geometry import Point
from datetime import datetime
import os
from tqdm import tqdm  # For displaying progress bars in loops
import folium  # For interactive map rendering

# Load or Download Road Network ---
graph_file = "bangalore.graphml"
day_graph_file = "bd.graphml"
night_graph_file = "bn.graphml"

# If the road network is already saved, load it. Otherwise, download and save it.
if os.path.exists(graph_file):
    G = ox.load_graphml(graph_file)
    print("Loaded road network from file!")
else:
    print("Downloading road network...")
    G = ox.graph_from_place("Bangalore, India", network_type="walk")
    ox.save_graphml(G, graph_file)
    print("Downloaded and saved road network!")

def is_night():
    """Return True if the current time is considered night (6 PM - 6 AM)."""
    now = datetime.now()
    return now.hour < 6 or now.hour > 18

# Load the Appropriate Graph
if is_night():
    G = ox.load_graphml(night_graph_file)
else:
    G = ox.load_graphml(day_graph_file)

# Routing Functions ---

def find_safest_route(G, start_coords, end_coords):
    """Find the safest route between two points using the modified edge weights."""
    start_node = ox.distance.nearest_nodes(G, start_coords[1], start_coords[0])
    end_node = ox.distance.nearest_nodes(G, end_coords[1], end_coords[0])
    route = nx.shortest_path(G, start_node, end_node, weight="weight")
    return route

def get_route_coordinates(G, route):
    """
    Convert a route from graph nodes to a list of (lat, lon) coordinates.
    Useful for plotting the route on a map.
    """
    return [(G.nodes[node]['y'], G.nodes[node]['x']) for node in route]

# Compute the Safest Route Between Two Locations ---

start_coords = (12.99310, 77.55318)  # Start location (lat, lon)
end_coords = (12.99507, 77.55345)    # End location (lat, lon)

print("Computing the safest route...")
route = find_safest_route(G, start_coords, end_coords)

# Visualize the Route on Folium ---

print("Visualizing the safest route on Folium...")
route_coords = get_route_coordinates(G, route)
m = folium.Map(location=start_coords[::-1], zoom_start=15)

# Draw the route line
folium.PolyLine(route_coords, color="blue", weight=5, opacity=0.8).add_to(m)

# (Optional) Add start and end markers
start_node = ox.distance.nearest_nodes(G, start_coords[::-1][0], start_coords[::-1][1])
end_node = ox.distance.nearest_nodes(G, end_coords[::-1][0], end_coords[::-1][1])

# Save map as an HTML file
output_map_file = "safest_route_map.html"
m.save(output_map_file)
print(f"Map saved to {output_map_file}. Open this file to view the route.")
