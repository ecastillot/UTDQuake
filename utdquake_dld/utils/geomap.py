import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, box

def load_world_shapefile(path: str) -> gpd.GeoDataFrame:
    """Load shapefile and fix France/French Guiana piece"""
    world = gpd.read_file(path)
    world = world.explode(index_parts=True).reset_index(drop=True)

    world['centroid'] = world.geometry.centroid
    mask = (
        (world['NAME'] == 'France') &
        (world['centroid'].y.between(2, 6)) &
        (world['centroid'].x.between(-55, -50))
    )
    world.loc[mask, 'NAME'] = 'French Guiana'
    world = world.drop(columns=['centroid'])
    return world

def split_russia(world: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Split Russia into European and Asian parts"""
    russia = world[world['NAME'] == 'Russia'].copy()
    split_line = LineString([(60, -90), (60, 90)])
    west_box = box(-170, -90, 60, 90)
    east_box = box(60, -90, 181, 90)

    russia['geometry_west'] = russia.geometry.intersection(west_box)
    russia['geometry_east'] = russia.geometry.intersection(east_box)

    russia_europe = russia.copy()
    russia_europe['geometry'] = russia_europe['geometry_west']
    russia_europe['NAME'] = 'European Russia'

    russia_asia = russia.copy()
    russia_asia['geometry'] = russia_asia['geometry_east']
    russia_asia['NAME'] = 'Asian Russia'

    world = world[world['NAME'] != 'Russia']
    world = pd.concat([world, russia_europe, russia_asia], ignore_index=True)
    return world.drop(columns=['geometry_west', 'geometry_east'])

def define_regions(world: gpd.GeoDataFrame) -> dict:
    """Return region definitions and colors"""
    middle_east = [
        'Akrotiri and Dhekelia','Bahrain','Cyprus','Iran','Iraq','Israel','Jordan',
        'Kuwait','Lebanon','Oman','Palestine','Qatar','Saudi Arabia','Syria',
        'Turkey','United Arab Emirates','Yemen'
    ]
    south_america = [
        'Argentina', 'Bolivia', 'Brazil', 'Chile', 'Colombia', 'Ecuador',
        'Guyana', 'Paraguay', 'Peru', 'Suriname', 'Uruguay', 'Venezuela',
        'French Guiana'
    ]
    regions = {
        'North America': ['United States of America', 'Canada', 'Mexico', 'Greenland'],
        'Central America': ['Guatemala', 'Belize', 'Honduras', 'El Salvador', 'Nicaragua', 'Costa Rica', 'Panama'],
        'Caribbean': ['Cuba', 'Haiti', 'Dominican Rep.', 'Bahamas', 'Jamaica', 'Puerto Rico', 'Trinidad and Tobago', 'Barbados'],
        'South America': south_america,
        'Europe': ['European Russia'] + [c for c in world[world['CONTINENT'] == 'Europe']['NAME'] if c not in south_america],
        'Middle East': middle_east,
        'Africa': [c for c in world[world['CONTINENT'] == 'Africa']['NAME'] if c not in middle_east],
        'Asia': ['Asian Russia'] + [c for c in world[world['CONTINENT'] == 'Asia']['NAME'] if c not in middle_east and c != 'Russia'],
        'Australia & Oceania': ['Australia', 'New Zealand', 'Papua New Guinea'],
        'Antarctica': ['Antarctica'],
    }
    region_colors = {
        'North America': 'gold',
        'Central America': 'darkblue',
        'Caribbean': 'crimson',
        'South America': 'red',
        'Europe': 'green',
        'Middle East': 'orange',
        'Africa': 'mediumpurple',
        'Asia': 'wheat',
        'Australia & Oceania': 'violet',
        'Antarctica': 'lightgrey',
    }
    return regions, region_colors

def plot_world_map(world: gpd.GeoDataFrame, regions: dict, region_colors: dict, output_path: str):
    """Plot the map with colored regions"""
    fig = plt.figure(figsize=(12, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_global()
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.STATES, linestyle=':')
    ax.add_feature(cfeature.LAND, edgecolor='black')
    ax.add_feature(cfeature.OCEAN)

    for region, countries in regions.items():
        region_data = world[world['NAME'].isin(countries)]
        region_data.plot(
            ax=ax,
            transform=ccrs.PlateCarree(),
            color=region_colors[region],
            edgecolor='black',
            linewidth=0.5,
            label=region
        )

    ax.set_aspect('equal', adjustable='box')

    handles = [plt.Rectangle((0, 0), 1, 1, color=color) for color in region_colors.values()]
    plt.legend(handles, region_colors.keys(), loc='lower left')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)


if __name__ == "__main__":
    shapefile_path = r"/groups/igonin/ecastillo/UTDQuake/data/geomap/ne_110m_admin_0_countries.shp"
    output_image = r"/groups/igonin/ecastillo/UTDQuake/test/plots/geomap.png"

    world = load_world_shapefile(shapefile_path)
    world = split_russia(world)
    regions, region_colors = define_regions(world)
    plot_world_map(world, regions, region_colors, output_image)
