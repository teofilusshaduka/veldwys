import pandas as pd
import numpy as np
import random

regions = ["Omaheke", "Otjozondjupa", "Kunene", "Erongo", "Hardap", "Karas", "Khomas", "Oshikoto", "Oshana", "Omusati", "Ohangwena", "Kavango East", "Kavango West", "Zambezi"]
tenures = ["communal", "conservancy", "commercial"]

data = []
for i in range(1200):
    region = random.choice(regions)
    site_id = f"SITE_{i:04d}"
    lat = np.random.uniform(-28.0, -17.0)
    lon = np.random.uniform(11.0, 21.0)
    
    veg_cover = np.random.uniform(10.0, 80.0) # %
    ndvi = np.random.uniform(0.1, 0.7)
    grass_biomass = np.random.uniform(100, 2000) # kg/ha
    bush_biomass = np.random.uniform(500, 5000) # kg/ha
    bush_encroachment = random.choice(["Low", "Moderate", "High", "Severe"])
    livestock_density = np.random.uniform(5, 50) # ha/LSU
    carrying_capacity = np.random.uniform(10, 45) # ha/LSU (Namibia typical)
    
    grazing_pressure = "High" if livestock_density < carrying_capacity else "Normal"
    tenure = random.choice(tenures)

    data.append([
        region, site_id, lat, lon, veg_cover, ndvi, grass_biomass, bush_biomass, 
        bush_encroachment, livestock_density, carrying_capacity, grazing_pressure, tenure
    ])

df = pd.DataFrame(data, columns=[
    "region", "site_id", "lat", "lon", "veg_cover_pct", "ndvi", "grass_biomass_kg_ha",
    "bush_biomass_kg_ha", "bush_encroachment", "livestock_density_ha_lsu", 
    "carrying_capacity_ha_lsu", "grazing_pressure", "tenure"
])

df.to_csv("data/rangeland.csv", index=False)
print("Generated data/rangeland.csv with", len(df), "rows.")
