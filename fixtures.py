import pandas as pd
from datetime import timedelta
import requests
import json
from geopy.geocoders import Nominatim
from utils import time_calculator


class Fixtures:
    """ Class Fixtures, generate the list of matches and dates for a given league and season
    """
    def __init__(self, foot_api_key, route_api_key, league_id, year, airport_origin, league_country, min_int_match):
        self.foot_api_key = foot_api_key
        self.route_api_key = route_api_key
        self.league_id = str(league_id)
        self.year = str(year)
        self.airport_origin = airport_origin
        self.min_int_match = min_int_match
        self.league_country = league_country
        self.geolocator = Nominatim(user_agent="match routing")

    def _get_fixtures(self):
        """ Pull all matches for the league from API Football and geocode each of the locations
        """
        url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
        headers = {"X-RapidAPI-Key": self.foot_api_key, "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"}
        querystring = {"league": self.league_id, "season": self.year}
        response = requests.request("GET", url, headers=headers, params=querystring)
        all_responses = response.text
        res = json.loads(all_responses)

        geocode_result = self.geolocator.geocode(self.airport_origin, timeout=2)
        self.airport_lat = geocode_result.latitude
        self.airport_lon = geocode_result.longitude
        self.matches_team = {}

        teams_stadiums = {}
        fixtures_dict = {'date': [], 'home team': [], 'away team': [], 'match id': [], 'stadium name': [],
                         'stadium city': [], 'stadium lat': [], 'stadium lon': []}
        teams_dict = {'Team': [], 'Lat': [], 'Lon': [], 'City': [], 'Stadium': []}
        if 'response' in res:
            for i in res['response']:
                team_home = i["teams"]["home"]["name"]
                team_away = i["teams"]["away"]["name"]
                stadium_name = i['fixture']['venue']['name'] + "," + i['fixture']['venue']['city']
                stadium_city = i['fixture']['venue']['city'] + "," + self.league_country
                place_name = stadium_name + "," + self.league_country
                if stadium_name in teams_stadiums:
                    stadium_lat = teams_stadiums[stadium_name][0]
                    stadium_lon = teams_stadiums[stadium_name][1]
                    stadium_city = teams_stadiums[stadium_name][2]
                else:
                    geocode_result = self.geolocator.geocode(place_name, timeout=2)
                    if geocode_result is None:
                        geocode_result = self.geolocator.geocode(stadium_city, timeout=2)
                        if geocode_result is None:
                            geocode_result = self.geolocator.geocode(stadium_city.split(", ")[1], timeout=2)
                    stadium_lat = geocode_result.latitude
                    stadium_lon = geocode_result.longitude
                    teams_stadiums[stadium_name] = (stadium_lat, stadium_lon, stadium_city)
                match_id = team_home + " x " + team_away
                fixtures_dict['date'].append(pd.to_datetime(i['fixture']['date']))
                fixtures_dict['home team'].append(team_home)
                fixtures_dict['away team'].append(team_away)
                fixtures_dict['match id'].append(match_id)
                fixtures_dict['stadium name'].append(i['fixture']['venue']['name'])
                fixtures_dict['stadium city'].append(stadium_city)
                fixtures_dict['stadium lat'].append(stadium_lat)
                fixtures_dict['stadium lon'].append(stadium_lon)
                if team_home in self.matches_team:
                    self.matches_team[team_home].append(match_id)
                else:
                    self.matches_team[team_home] = [match_id]
                if team_home not in teams_dict['Team']:
                    teams_dict['Team'].append(team_home)
                    teams_dict['Lat'].append(stadium_lat)
                    teams_dict['Lon'].append(stadium_lon)
                    teams_dict['City'].append(stadium_city)
                    teams_dict['Stadium'].append(stadium_name)
        self.start_league = min(fixtures_dict['date'])
        self.end_league = max(fixtures_dict['date'])
        fixtures_dict['date'].append(self.start_league - timedelta(days=5))
        fixtures_dict['home team'].append(self.airport_origin)
        fixtures_dict['away team'].append(self.airport_origin)
        fixtures_dict['match id'].append("Start")
        fixtures_dict['stadium name'].append('')
        fixtures_dict['stadium city'].append('')
        fixtures_dict['stadium lat'].append(self.airport_lat)
        fixtures_dict['stadium lon'].append(self.airport_lon)
        self.matches_team[self.airport_origin] = ["Start", "End"]
        fixtures_dict['date'].append(self.end_league + timedelta(days=5))
        fixtures_dict['home team'].append(self.airport_origin)
        fixtures_dict['away team'].append(self.airport_origin)
        fixtures_dict['match id'].append("End")
        fixtures_dict['stadium name'].append('')
        fixtures_dict['stadium city'].append('')
        fixtures_dict['stadium lat'].append(self.airport_lat)
        fixtures_dict['stadium lon'].append(self.airport_lon)
        self.fixtures = pd.DataFrame.from_dict(fixtures_dict)
        self.fixtures_dict = self.fixtures.set_index('match id').to_dict()
        self.matches_id = self.fixtures['match id'].unique()
        self.teams = pd.DataFrame.from_dict(teams_dict).drop_duplicates(subset=['Team'])
        self.teams_dict = self.teams.set_index('Team').to_dict()
        self.teams_id = self.teams['Team'].unique()

    def _get_travel_times(self):
        """ Calculates travel times from a stadium to another
        """
        self.travel_times = {}
        for team in self.teams_id:
            time_to_origin = time_calculator(self.teams_dict['Lat'][team], self.teams_dict['Lon'][team],
                                             self.airport_lat, self.airport_lon)
            time_from_origin = time_calculator(self.airport_lat, self.airport_lon,
                                               self.teams_dict['Lat'][team], self.teams_dict['Lon'][team])
            self.travel_times[(team, self.airport_origin)] = time_to_origin
            self.travel_times[(self.airport_origin, team)] = time_from_origin

            for team2 in self.teams_id:
                time = time_calculator(self.teams_dict['Lat'][team], self.teams_dict['Lon'][team],
                                       self.teams_dict['Lat'][team2], self.teams_dict['Lon'][team2])
                self.travel_times[(team, team2)] = time
        self.travel_times[(self.airport_origin, self.airport_origin)] = 0

    def _get_time_between_matches(self):
        """ Define the list of successors of a match - if it happens after it
        """
        self.possible_successor = {}
        self.fixtures_dict['start hours'] = {}
        for m1 in self.matches_id:
            self.possible_successor[m1] = []
            t1 = self.fixtures_dict['home team'][m1]
            s1 = (self.fixtures_dict['date'][m1] - self.start_league).total_seconds() / (60 * 60)
            self.fixtures_dict['start hours'][m1] = s1
            for m2 in self.matches_id:
                t2 = self.fixtures_dict['home team'][m2]
                s2 = (self.fixtures_dict['date'][m2] - self.start_league).total_seconds() / (60 * 60)
                """ A match m2 is a possible successor of m1 if:
                    - starting time of m2 is after starting time of m1 plus travel time from m1 to m2 and
                    - difference of starting time of m2 and m1 is higher than min_int_match"""
                if m1 != m2 and s1 + max(self.travel_times[(t1, t2)], self.min_int_match) <= s2:
                    self.possible_successor[m1].append(m2)

    def _pull_fixtures(self):
        """ Executes all the routines of the class
        """
        self._get_fixtures()
        self._get_travel_times()
        self._get_time_between_matches()
