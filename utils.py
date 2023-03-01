from math import radians, cos, sin, asin, sqrt
import requests
import json
import folium
import pandas as pd

def pull_directions_api(lat1, lon1, lat2, lon2, route_api_key):
    url = "https://route-and-directions.p.rapidapi.com/v1/routing"
    host = "route-and-directions.p.rapidapi.com"
    headers = {"X-RapidAPI-Key": route_api_key, "X-RapidAPI-Host": host}
    querystring = {"waypoints": f"{str(lat1)},{str(lon1)}|{str(lat2)},{str(lon2)}", "mode": 'drive'}
    response = requests.request("GET", url, headers=headers, params=querystring)
    res = json.loads(response.text)
    return res


def time_calculator(lat1, lon1, lat2, lon2, route_api_key=None):
    """ Calculate travel time between two locations using
        - Haversine Distance and Average Speed of 60km/h if Route API Key is not passed
        - Using Route and directions API, mode drive
            (https://rapidapi.com/geoapify-gmbh-geoapify/api/route-and-directions)
    """
    if route_api_key is None:
        speed = 60
        R = 6372.8
        dLat = radians(lat2 - lat1)
        dLon = radians(lon2 - lon1)
        lat1 = radians(lat1)
        lat2 = radians(lat2)
        a = sin(dLat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dLon / 2) ** 2
        c = 2 * asin(sqrt(a))
        km = R * c
        time_hours = km / speed
    else:
        res = pull_directions_api(lat1, lon1, lat2, lon2, route_api_key)
        time_hours = res['features'][0]['properties']['time'] / (60 * 60)
    return time_hours


def create_map(responses, lat_lons):
    m = folium.Map()
    df = pd.DataFrame()
    for point in lat_lons:
        folium.Marker(point).add_to(m)
    for response in responses:
        mls = response['features'][0]['geometry']['coordinates']
        points = [(i[1], i[0]) for i in mls[0]]
        folium.PolyLine(points, weight=5, opacity=1).add_to(m)
        temp = pd.DataFrame(mls[0]).rename(columns={0: 'Lon', 1: 'Lat'})[['Lat', 'Lon']]
        df = pd.concat([df, temp])
    sw = df[['Lat', 'Lon']].min().values.tolist()
    sw = [sw[0] - 0.0005, sw[1] - 0.0005]
    ne = df[['Lat', 'Lon']].max().values.tolist()
    ne = [ne[0] + 0.0005, ne[1] + 0.0005]
    m.fit_bounds([sw, ne])
    return m