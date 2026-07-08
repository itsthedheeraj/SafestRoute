import streamlit as st
import folium
from streamlit_folium import st_folium
import osmnx as ox
import networkx as nx
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import os

# Set page config
st.set_page_config(page_title="SafeRoute Finder", layout="wide")
st.title("🚦 SafeRoute Finder")
st.markdown("Compare the **fastest** and **safest** routes between two places.")

# -----------------------------
# Graph loading (cached)
# -----------------------------
@st.cache_resource
def load_graphs():
    # Load base road network (for fastest route)
    G = ox.load_graphml("road_network.graphml")
    
    # Load day safety graph if exists, fallback to G
    if os.path.exists("day_graph.graphml"):
        day_graph = ox.load_graphml("day_graph.graphml")
    else:
        day_graph = G
        
    # Load night safety graph if exists, fallback to day_graph
    if os.path.exists("night_graph.graphml"):
        night_graph = ox.load_graphml("night_graph.graphml")
    else:
        night_graph = day_graph
        
    return G, day_graph, night_graph

# Load the graphs
try:
    G, day_graph, night_graph = load_graphs()
except Exception as e:
    st.error(f"❌ Failed to load graph files: {e}. Please ensure 'road_network.graphml' is present in the directory.")
    st.stop()

# -----------------------------
# Geocoding helper (Global instance)
# -----------------------------
# Uses a single global Nominatim instance instead of creating one every request
geolocator = Nominatim(user_agent="saferoute_finder_application_v1")

# Initialize geocoding cache in session state
if "geocoding_cache" not in st.session_state:
    st.session_state.geocoding_cache = {}

def geocode_place(place_name):
    query = place_name.strip().lower()
    if not query:
        return None
    
    # Return from cache if available
    if query in st.session_state.geocoding_cache:
        return st.session_state.geocoding_cache[query]
    
    try:
        # Handles both GeocoderTimedOut and GeocoderUnavailable
        location = geolocator.geocode(place_name, timeout=5)
        if location:
            coords = (location.latitude, location.longitude)
            st.session_state.geocoding_cache[query] = coords
            return coords
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        st.warning(f"⚠️ Geocoding service error: {e}. Retrying might help.")
        return None
    return None

# -----------------------------
# Route finding (cached with @st.cache_data)
# -----------------------------
# We pass an identifier string instead of the graph object to avoid caching overhead/errors
@st.cache_data
def compute_route(start_coords, end_coords, graph_type):
    # Retrieve the correct graph globally based on graph_type
    if graph_type == "fastest":
        graph = G
    elif graph_type == "day_safe":
        graph = day_graph
    elif graph_type == "night_safe":
        graph = night_graph
    else:
        graph = G
        
    # Find nearest nodes
    start_node = ox.distance.nearest_nodes(graph, start_coords[1], start_coords[0])
    end_node = ox.distance.nearest_nodes(graph, end_coords[1], end_coords[0])
    
    # Compute shortest path
    route = nx.shortest_path(graph, start_node, end_node, weight="length")
    return route

# -----------------------------
# Route distance calculator
# -----------------------------
def calculate_length(graph, route):
    return sum(graph.get_edge_data(u, v)[0]["length"] for u, v in zip(route[:-1], route[1:]))

# -----------------------------
# Route coordinate extractor (actual street geometry)
# -----------------------------
def route_to_coords(graph, route):
    coords = []
    for u, v in zip(route[:-1], route[1:]):
        edge = graph.get_edge_data(u, v)[0]
        if "geometry" in edge:
            line = edge["geometry"]
            coords.extend([(lat, lon) for lon, lat in line.coords])
        else:
            coords.append((graph.nodes[u]["y"], graph.nodes[u]["x"]))
            coords.append((graph.nodes[v]["y"], graph.nodes[v]["x"]))
    return coords

# -----------------------------
# Folium map generator
# -----------------------------
def make_map(routes_info, start_coords, end_coords):
    # Initialize Map with multiple tile layers
    m = folium.Map(location=start_coords, zoom_start=15)
    
    # Add tile options
    folium.TileLayer('openstreetmap', name='OpenStreetMap').add_to(m)
    folium.TileLayer('cartodbpositron', name='CartoDB Light').add_to(m)
    folium.TileLayer('cartodbdark_matter', name='CartoDB Dark').add_to(m)
    
    # Add FeatureGroups for each route type so they can be toggled via LayerControl
    for route, color, label, graph in routes_info:
        fg = folium.FeatureGroup(name=label).add_to(m)
        coords = route_to_coords(graph, route)
        folium.PolyLine(coords, color=color, weight=5, opacity=0.8, tooltip=label).add_to(fg)
        
    # Markers for Start and End
    folium.Marker(start_coords, popup="Start Location", icon=folium.Icon(color='green', icon='play', prefix='fa')).add_to(m)
    folium.Marker(end_coords, popup="End Location", icon=folium.Icon(color='red', icon='stop', prefix='fa')).add_to(m)
    
    # Fit bounds so map automatically zooms to show the entire route
    all_coords = [start_coords, end_coords]
    for route, _, _, graph in routes_info:
        all_coords.extend(route_to_coords(graph, route))
        
    if all_coords:
        min_lat = min(c[0] for c in all_coords)
        max_lat = max(c[0] for c in all_coords)
        min_lon = min(c[1] for c in all_coords)
        max_lon = max(c[1] for c in all_coords)
        m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])
        
    # Add LayerControl to allow users to toggle layers
    folium.LayerControl(collapsed=False).add_to(m)
    
    return m

# -----------------------------
# Streamlit Sidebar & Options
# -----------------------------
with st.sidebar:
    st.header("📍 Route Settings")
    
    # Place inputs with defaults
    start_place = st.text_input("Start Location", value="L'Enfant Plaza, Washington DC")
    end_place = st.text_input("End Location", value="Capitol Hill, Washington DC")
    
    # Choose travel time (Daytime vs Nighttime)
    time_of_travel = st.selectbox(
        "Time of Travel", 
        ["Daytime (Use Day Safety Graph)", "Nighttime (Use Night Safety Graph)"]
    )
    
    # Checkboxes side-by-side to save height
    col1, col2 = st.columns(2)
    with col1:
        show_fastest = st.checkbox("Show Fastest", value=True)
    with col2:
        show_safest = st.checkbox("Show Safest", value=True)
    
    st.markdown(" ") # Minimal spacing
    compute = st.button("🚀 Compute Routes", use_container_width=True)

# Initialize routes data in session state if not already
if "routes_data" not in st.session_state:
    st.session_state.routes_data = None

# -----------------------------
# Computation Logic
# -----------------------------
if compute:
    with st.spinner("Calculating routes... Please wait ⏳"):
        # 1. Geocode locations
        start_coords = geocode_place(start_place)
        end_coords = geocode_place(end_place)
        
        if not start_coords:
            st.error(f"❌ Could not locate the start address: '{start_place}'. Please check spelling or try another location.")
        elif not end_coords:
            st.error(f"❌ Could not locate the end address: '{end_place}'. Please check spelling or try another location.")
        else:
            routes_info = []
            metrics = []
            
            # Map safety graph depending on traveler's selection
            is_night = "Nighttime" in time_of_travel
            safety_graph_type = "night_safe" if is_night else "day_safe"
            safety_graph = night_graph if is_night else day_graph
            safety_label = "Safest Route (Night)" if is_night else "Safest Route (Day)"
            
            # Calculate fastest route
            fastest_success = False
            if show_fastest:
                try:
                    fastest_route = compute_route(start_coords, end_coords, "fastest")
                    length_m = calculate_length(G, fastest_route)
                    routes_info.append((fastest_route, "red", "Fastest Route", G))
                    metrics.append(("Fastest Route", length_m))
                    fastest_success = True
                except nx.NetworkXNoPath:
                    st.error("❌ No path could be found for the Fastest Route. The locations might be disconnected on the map.")
                except Exception as e:
                    st.error(f"❌ Error computing Fastest Route: {e}")
            
            # Calculate safest route
            safest_success = False
            if show_safest:
                try:
                    safest_route = compute_route(start_coords, end_coords, safety_graph_type)
                    length_m = calculate_length(safety_graph, safest_route)
                    routes_info.append((safest_route, "blue", safety_label, safety_graph))
                    metrics.append((safety_label, length_m))
                    safest_success = True
                except nx.NetworkXNoPath:
                    st.error(f"❌ No path could be found for the {safety_label}. The locations might be disconnected on the safety map.")
                except Exception as e:
                    st.error(f"❌ Error computing {safety_label}: {e}")
                    
            if fastest_success or safest_success:
                st.session_state.routes_data = {
                    "routes_info": routes_info,
                    "metrics": metrics,
                    "start_coords": start_coords,
                    "end_coords": end_coords
                }
            else:
                st.session_state.routes_data = None

# -----------------------------
# Main Display Panel
# -----------------------------
if st.session_state.routes_data:
    data = st.session_state.routes_data
    
    # Display distance metrics first in columns
    st.subheader("📏 Route Details")
    cols = st.columns(len(data["metrics"]))
    for col, (label, length_m) in zip(cols, data["metrics"]):
        with col:
            length_km = length_m / 1000.0
            st.metric(
                label=label,
                value=f"{length_m:.1f} m",
                delta=f"{length_km:.3f} km",
                delta_color="off"
            )
            
    # Render map
    st.subheader("🗺️ Interactive Map")
    route_map = make_map(data["routes_info"], data["start_coords"], data["end_coords"])
    st_folium(route_map, width=1100, height=600)
else:
    # Instructions panel
    st.info("👈 Enter your start and end locations in the sidebar and click **Compute Routes** to begin!")
