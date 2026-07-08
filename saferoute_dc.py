import osmnx as ox
import networkx as nx
import geopandas as gpd
from shapely.geometry import Point
from datetime import datetime
import os
from tqdm import tqdm  

# File path for the road network
graph_file = "road_network.graphml"
day_graph_file = "day_graph.graphml"
night_graph_file = "night_graph.graphml"

# Check if the road network file exists, otherwise download and save it
if os.path.exists(graph_file):
    # Load the saved road network if it exists
    G = ox.load_graphml(graph_file)
    print("Loaded road network from file!")
else:
    # Otherwise, download and save the road network
    print("Loading road network...")
    G = ox.graph_from_place("Washington, D.C., USA", network_type="walk")
    ox.save_graphml(G, graph_file)
    print("Downloaded and saved road network!")

# --- Step 2: Load Safety Parameters ---
print("Loading safety parameters...")
crime_data = gpd.read_file(r"washington\crime_incidents_in_2024_geometry_only.geojson")
cctv_data = gpd.read_file(r"washington\Closed_Circuit_TV_Street_Cameras_geometry_only.geojson")
street_lights = gpd.read_file(r"washington\Street_Lights_Geometry_Only.geojson")
night_clubs = gpd.read_file(r"washington\Night_Club_geometry_only.geojson")
police_stations = gpd.read_file(r"washington\Police_Stations_cleaned.geojson")



target_crs = "EPSG:26918" 
crime_data = crime_data.to_crs(target_crs)
cctv_data = cctv_data.to_crs(target_crs)
street_lights = street_lights.to_crs(target_crs)
night_clubs = night_clubs.to_crs(target_crs)
police_stations = police_stations.to_crs(target_crs)

crime_data.sindex
cctv_data.sindex
street_lights.sindex
night_clubs.sindex
police_stations.sindex

# --- Step 3: Utility Functions ---
def is_night():
    """Check if the current time is night."""
    now = datetime.now()
    return now.hour < 6 or now.hour > 18  

def count_nearby_features_with_sindex(edge_midpoint, gdf, radius=80, target_crs="EPSG:26918"):

    midpoint_gdf = gpd.GeoDataFrame(geometry=[edge_midpoint], crs="EPSG:4326")

    midpoint_gdf = midpoint_gdf.to_crs(target_crs)
    \
    buffer = midpoint_gdf.geometry.iloc[0].buffer(radius)
    
    return gdf.sindex.query(buffer, predicate="intersects").size


def compute_edge_length(u, v, data, crime_data, cctv_data, street_lights, night_clubs, police_stations, is_night):
    """
    Compute and modify the edge length based on various factors.
    """
    edge_midpoint = Point((data["geometry"].centroid.x, data["geometry"].centroid.y))
    length = float(data["length"]) 

   
    length += 400 * count_nearby_features_with_sindex(edge_midpoint, crime_data)
    length -= 400 * count_nearby_features_with_sindex(edge_midpoint, cctv_data)
    length -= 450 * count_nearby_features_with_sindex(edge_midpoint, police_stations)

    if is_night:
        length -= 75* count_nearby_features_with_sindex(edge_midpoint, street_lights)
        length += 350 * count_nearby_features_with_sindex(edge_midpoint, night_clubs)

    
    return max(length, 0)


def modify_edge_lengths(G, is_night, crime_data, cctv_data, street_lights, night_clubs, police_stations):
    """
    Modify the 'length' data of edges in the graph based on safety considerations.
    """
    edges = list(G.edges(data=True))  
    for u, v, data in tqdm(edges, desc="Modifying edge lengths", unit="edges"):  # Add tqdm for progress bar
        if "geometry" in data and "length" in data:
           
            modified_length = compute_edge_length(u, v, data, crime_data, cctv_data, street_lights, night_clubs, police_stations, is_night)
         
            data["length"] = modified_length
    return G


# --- Step 5: Check if Graph Files Already Exist ---
if os.path.exists(day_graph_file):
    print("DAY Graph already precomputed and saved. Loading the appropriate graph...")
else:
  
    print("Precomputing and saving graphs for day...")
    day_graph = modify_edge_lengths(G, is_night=False, crime_data=crime_data, cctv_data=cctv_data, street_lights=street_lights, night_clubs=night_clubs, police_stations=police_stations)
    ox.save_graphml(day_graph, day_graph_file)

if os.path.exists(night_graph_file):
    print("NIGHT Graph already precomputed and saved. Loading the appropriate graph...")
else:
  
    print("Precomputing and saving graphs for night...")   
    night_graph = modify_edge_lengths(G, is_night=True, crime_data=crime_data, cctv_data=cctv_data, street_lights=street_lights, night_clubs=night_clubs, police_stations=police_stations)
    ox.save_graphml(night_graph, night_graph_file)



print("Loading the appropriate graph...")
if is_night():
    F = ox.load_graphml(night_graph_file)
else:
    F = ox.load_graphml(day_graph_file)

G = ox.load_graphml(graph_file)
print("Loaded road network from file!")

def find_route(G, start_coords, end_coords, weight):

    start_node = ox.distance.nearest_nodes(G, start_coords[1], start_coords[0])
    end_node = ox.distance.nearest_nodes(G, end_coords[1], end_coords[0])
    route = nx.shortest_path(G, start_node, end_node, weight=weight)
    return route

def print_route_edges(G, route, route_type="Route"):
  
    total_length = 0
    print(f"{route_type} Route Edges:")
    for u, v in zip(route[:-1], route[1:]):  
        edge_data = G.get_edge_data(u, v)[0] 
        length = edge_data.get("length", 0)  
        total_length += length
        print(f"Edge from {u} to {v}, Length: {length:.2f} meters")
    print(f"Total {route_type} Route Length: {total_length:.2f} meters\n")


def visualize_routes(G, routes, colors, labels):

    fig, ax = ox.plot_graph_routes(
        G,
        routes=routes,
        route_colors=colors,
        route_linewidth=3,
        node_size=0,
        figsize=(12, 8)
    )
    ax.legend(labels)
    print("Routes visualized.")


start_coords =   (38.864255,-77.013708	)  # Example: White House
end_coords = (38.868215,-77.009415	)
# Compute the fastest route (minimizing length)
print("Computing the fastest route...")
fastest_route = find_route(G, start_coords, end_coords, weight="length")
print_route_edges(G, fastest_route, route_type="Fastest")
print("\nAfter weighting :")
print_route_edges(F, fastest_route, route_type="Fastest")
print("========================================================================")
# Compute the safest route (replace 'length' with your safety metric if available)
print("Computing the safest route...")
safest_route = find_route(F, start_coords, end_coords, weight="length")
print_route_edges(G, safest_route, route_type="Safest")
print("\nAfter weighting :")
print_route_edges(F, safest_route, route_type="Safest")

# --- Step 8: Visualize Safest Route ---
print("Visualizing routes...")
visualize_routes(
    G,
    routes=[fastest_route, safest_route],
    colors=["red", "blue"],  # Red for fastest, blue for safest
    labels=["Fastest Route", "Safest Route"]
)




