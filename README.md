# 🚦 SafeRoute Finder

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Streamlit App](https://img.shields.io/badge/Streamlit-App-red.svg)](https://streamlit.io/)
[![Folium](https://img.shields.io/badge/Folium-Mapping-green.svg)](https://python-visualization.github.io/folium/)
[![OSMnx](https://img.shields.io/badge/OSMnx-Network_Analysis-orange.svg)](https://osmnx.readthedocs.io/)

SafeRoute Finder is a risk-aware route planner (for walking or driving). Instead of calculating only the shortest path, it integrates spatial datasets containing safety factors (such as streetlights, CCTV coverage, and police stations) and risk factors (such as crime locations and nightlife activity) to recommend the **safest route** between any two locations. 

The project pre-calculates safety-weighted road networks for both daytime and nighttime conditions, allowing users to compare the **Fastest Route** vs. the **Safest Route** in real time via an interactive, user-friendly Streamlit web application.

---

## 🔍 Core Methodology

The project models the city’s road or path infrastructure as a street network graph. To find the safest route, edge weights (originally representing physical distance in meters) are adjusted using a risk-penalty and safety-reward algorithm:

$$\text{Modified Length} = \max(\text{Length} + \text{Penalties} - \text{Rewards}, 0)$$

### Safety & Risk Factors Evaluated:
- 🔴 **Crime Density (Penalty)**: Adds weight to road segments close to historical crime incidents.
- 🔴 **Nightlife Venues (Night Penalty)**: Adds weight to segments close to pubs/night clubs during nighttime travel.
- 🟢 **CCTV Cameras (Reward)**: Reduces weight for segments under active surveillance.
- 🟢 **Police Stations (Reward)**: Reduces weight for segments in close proximity to law enforcement.
- 🟢 **Street Lighting (Night Reward)**: Reduces weight for segments with public streetlights during nighttime travel.

Because safety conditions change after dark, the model generates separate **Daytime** and **Nighttime** safety graphs.

---

## ✨ Web App Key Features

Our interactive Streamlit app (`app.py`) offers a premium navigation interface loaded with the following optimizations:

- 🚀 **Curve-Aware Routing**: Extracts and renders actual road geometry curves (`geometry` attribute in OpenStreetMap edges) rather than connecting network intersections with simple straight lines.
- ⚡ **Multi-Layer Session Caching**: 
  - Uses a global Nominatim geocoding instance to prevent socket exhaustion.
  - Caches geocoded locations in `st.session_state` to avoid redundant external API calls.
  - Caches pathfinding requests using `@st.cache_data` for instant route recalculations.
- 🗺️ **Interactive Multi-Tile Map**:
  - Lets users toggle between OpenStreetMap, CartoDB Light, and CartoDB Dark tile layers.
  - Controls route layers (Fastest vs. Safest) using an interactive LayerControl menu.
  - Auto-adjusts viewports with `fit_bounds` to display entire route spans and start/end pins instantly.
- 📊 **Dual-Unit Metrics**: Displays route distances in both meters and kilometers in high-visibility columns.
- 🛡️ **Robust Error Handling**: Gracefully catches Nominatim timeouts, offline states, and NetworkX disconnects, presenting descriptive, user-friendly warnings.

---

## 📁 Repository Structure

```files
├── app.py                      # Main Streamlit web application (DC-default)
├── app2.py                     # Older Streamlit iteration (Basic)
├── app3.py                     # Older Streamlit iteration (Geocode caching)
├── saferoute_dc.py             # Preprocessing script for Washington D.C.
├── saferoute_bengaluru.py      # Preprocessing script for Bengaluru (Bangalore)
├── saferoute_bang.py           # Alternate preprocessor for Bengaluru
├── graph_preprocess.py         # General helper preprocessing script
├── saferoute_html.py           # Standalone HTML map exporter
├── safest_route_map.html       # Exported static Leaflet HTML map
│
├── washington/                 # Geospatial data for Washington D.C.
│   ├── crime_incidents_in_2024_geometry_only.geojson
│   ├── Closed_Circuit_TV_Street_Cameras_geometry_only.geojson
│   ├── Street_Lights_Geometry_Only.geojson
│   ├── Night_Club_geometry_only.geojson
│   └── Police_Stations_cleaned.geojson
│
├── bengaluru/                  # Geospatial data for Bengaluru
│   ├── crimes.geojson
│   ├── cctv.geojson
│   ├── streetlights.geojson
│   ├── pubs.geojson
│   └── police.geojson
│
├── road_network.graphml        # Washington D.C. base road network
├── day_graph.graphml           # Washington D.C. daytime safety-weighted graph
├── night_graph.graphml         # Washington D.C. nighttime safety-weighted graph
│
├── bangalore.graphml           # Bengaluru base road network
├── bd.graphml                  # Bengaluru daytime safety-weighted graph
└── bn.graphml                  # Bengaluru nighttime safety-weighted graph
```

---

## 🛠️ Setup & Installation

### 1. Prerequisites
Ensure you have Python 3.8 or higher installed on your system.

### 2. Install Required Packages
Install the required packages using pip:
```bash
pip install streamlit folium streamlit-folium osmnx networkx geopy geopandas shapely tqdm
```

*Note: On some systems, installing `geopandas` and `osmnx` may require binary dependencies. We recommend using Conda if you experience installation issues:*
```bash
conda install -c conda-forge osmnx geopandas
```

---

## ⚙️ How to Run

### Option A: Running the Web App (Washington D.C.)
By default, the Streamlit app loads the precomputed Washington D.C. graphs (`road_network.graphml`, `day_graph.graphml`, `night_graph.graphml`).

To start the local server:
```bash
streamlit run app.py
```
This opens the web app in your default browser at `http://localhost:8501`.

### Option B: Running the Web App (Bengaluru)
To run the Streamlit app using the Bengaluru datasets, simply rename the Bengaluru graph files:
1. Rename `bangalore.graphml` to `road_network.graphml`
2. Rename `bd.graphml` to `day_graph.graphml`
3. Rename `bn.graphml` to `night_graph.graphml`
4. Launch the application:
```bash
streamlit run app.py
```

### Precomputing Safety Graphs
If you edit the risk formulas, radius boundaries, or add new safety datasets, you can re-generate the safety-weighted Day/Night graphs by executing the preprocessor scripts:

- **For Washington D.C.**:
  ```bash
  python saferoute_dc.py
  ```
- **For Bengaluru**:
  ```bash
  python saferoute_bengaluru.py
  ```

---

## 💡 Customization & Tuning

You can tune how safety factors influence travel routing distances in the preprocessor files (`saferoute_dc.py` or `saferoute_bengaluru.py`). The parameters are located in the `compute_edge_length` function:

```python
# Adjust multipliers to increase/decrease influence of features
length += 400 * count_nearby_features(edge_midpoint, crime_data)       # Penalty
length -= 400 * count_nearby_features(edge_midpoint, cctv_data)        # Reward
length -= 450 * count_nearby_features(edge_midpoint, police_stations)  # Reward

if is_night:
    length -= 75  * count_nearby_features(edge_midpoint, street_lights) # Night Reward
    length += 350 * count_nearby_features(edge_midpoint, night_clubs)    # Night Penalty
```

---

## 📜 License
This project is open-source and available under the MIT License.
