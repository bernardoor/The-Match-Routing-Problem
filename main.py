from fixtures import Fixtures
from fixtureschedulingmodel import FixtureSchedulingModel

if __name__ == '__main__':
    API_football_key = "dfBKQ8FAqumshq3FcwgNIEP2MqQnp1GIP0CjsnWEvyIY3KMQsc"
    """ Football API key 
        Refer to https://www.api-football.com/
    """

    API_Route_Directions = "dfBKQ8FAqumshq3FcwgNIEP2MqQnp1GIP0CjsnWEvyIY3KMQsc"
    """ Route and Directions API key 
        Refer to https://rapidapi.com/geoapify-gmbh-geoapify/api/route-and-directions
    """

    min_int_match = 12
    """ Minimum number of hours between two consecutive matches visited """

    year = 2022
    """ Year of Championship """

    league_id = 39
    """ League id from Football API
        For all leagues and countries available refer to:
        https://www.api-football.com/documentation-v3#tag/Leagues/operation/get-leagues
        Examples: 
            - Premier League UK: 39
            - Serie A Brazil: 71
            - Serie B Brazil: 72
            - La Liga Spain: 140
            - Ligue 1 France: 61
            - Bundesliga Germany: 78
    """

    origin_airport = 'Heathrow Airport'
    """ Airport or point of interest where trip begins 
        Examples:
            - United Kingdom: Heathrow Airport
            - Brazil: Guarulhos Airport
            - Spain: Madrid Barajas Airport
            - France: Charles de Gaulle International Airport
            - Germany: Frankfurt Airport
    """

    league_country = 'United Kingdom'
    """ Country League 
        Examples:
            - United Kingdom
            - Brazil
            - Spain
            - France
            - Germany 
    """

    fix = Fixtures(API_football_key, API_Route_Directions, league_id, year, origin_airport, league_country, min_int_match)
    fix._pull_fixtures()
    """ Get all fixtures for a given league and season """

    model = FixtureSchedulingModel(fix)
    model._solve_model()
    """ Solve Mathematical model """

    model._get_outputs()
    """ Get outputs of model"""
    print(model.output_schedule)

    model._plot_maps()
    """ Plot trip flow map"""
