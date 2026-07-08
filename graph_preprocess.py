import networkx as nx
from shapely.geometry import LineString
import osmnx as ox
from tqdm import tqdm

def add_missing_geometries(graph):
    """
    Add missing 'geometry' data to edges that lack it.
    """
    edges = list(graph.edges(data=True))
    for u, v, data in tqdm(edges, desc="Processing edges", unit="edge"):
        # Check if 'geometry' is missing
        if "geometry" not in data or data["geometry"] is None:
            # Get source and target node coordinates
            if u in graph.nodes and v in graph.nodes:
                source_node = graph.nodes[u]
                target_node = graph.nodes[v]
                
                try:
                    # Extract coordinates
                    source_coords = (float(source_node["x"]), float(source_node["y"]))
                    target_coords = (float(target_node["x"]), float(target_node["y"]))
                    
                    # Create a LineString for the edge
                    line_geometry = LineString([source_coords, target_coords])
                    
                    # Add the LineString to the edge's geometry
                    data["geometry"] = line_geometry
                except KeyError:
                    print(f"Missing 'x' or 'y' coordinate for nodes {u} or {v}, unable to create geometry.")
            else:
                print(f"Source or target node {u}, {v} not found in the graph.")

# Load the GraphML file
graphml_file = "bang_network.graphml"
G = ox.load_graphml(graphml_file)

# Add missing geometries only for edges lacking them
add_missing_geometries(G)

# Save the updated graph back to a GraphML file
updated_graphml_file = "updated_graph_file.graphml"
ox.save_graphml(G, updated_graphml_file)
print(f"Updated graph saved to {updated_graphml_file}")
