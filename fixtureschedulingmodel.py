import gurobipy as grb
import pandas as pd
from datetime import timedelta
from utils import pull_directions_api, create_map


class FixtureSchedulingModel:
    """ Build the mixed integer programming for the match routing problem
        The Match Routing Problem can be stated as the following: given the set of matches (fixtures) of a league,
        build a trip schedule starting and ending at the same point, making sure to:
            - Watch exactly one match of each team of the league
            - Respect travel times between stadiums
            - Respect minimum allowed time between two matches
        While minimizing the difference between the last watched and first match watched (objective 1) and
              minimizing the total travel time (objective 2)
    """
    def __init__(self, Fixtures):
        self.opt_model = grb.Model(name="MIP Model")
        self.fixture = Fixtures

    def _define_variables(self):
        """ Define model variables
        """
        """ Binary variable: 1 if match k is visited right before k2. 0 otherwise """
        self.x = {(k, k2): self.opt_model.addVar(vtype=grb.GRB.BINARY, name="x_{0}_{1}".format(k, k2))
                  for k in self.fixture.matches_id for k2 in self.fixture.possible_successor[k]}

    def _define_constraints(self):
        """ Define model constraints
        """
        """ Constraint 1 - the trip must start at a dummy match called Start """
        c1 = self.opt_model.addConstr(
            grb.quicksum(self.x['Start', k2] for k2 in self.fixture.possible_successor['Start']) == 1, name="c1")

        """ Constraint 2 - the trip must end at a dummy match called End """
        c2 = self.opt_model.addConstr(grb.quicksum(self.x[k2, 'End'] for k2 in self.fixture.matches_id if
                                                   k2 not in ('Start', 'End') and 'End' in
                                                   self.fixture.possible_successor[k2]) == 1, name="c2")

        """ Constraint 3 - Flow conservation constraint - a trip consists on a sequence of matches """
        c3 = {k: self.opt_model.addConstr(
            grb.quicksum(self.x[k2, k] for k2 in self.fixture.matches_id if k in self.fixture.possible_successor[k2]) ==
            grb.quicksum(self.x[k, k2] for k2 in self.fixture.possible_successor[k]),
            name="c3_{0}".format(k))
            for k in self.fixture.matches_id if k not in ('Start', 'End')}

        """ Constraint 4 - No more than 1 outbound match from a match """
        c4 = {k: self.opt_model.addConstr(
            grb.quicksum(
                self.x[k, k2] for k2 in self.fixture.possible_successor[k] if k2 not in ('Start', 'End')) <= 1,
            name="c4_{0}".format(k))
            for k in self.fixture.matches_id if k not in ('Start', 'End')}

        """ Constraint 5 - No more than 1 inbound to from a match """
        c5 = {k2: self.opt_model.addConstr(
            grb.quicksum(
                self.x[k, k2] for k in self.fixture.matches_id if
                k2 in self.fixture.possible_successor[k] and k not in ('Start', 'End')) <= 1, name="c5_{0}".format(k2))
            for k2 in self.fixture.matches_id if k2 not in ('Start', 'End')}

        """ Constraint 6 - All stadiums must be visited exactly once"""
        c6 = {i: self.opt_model.addConstr(
            grb.quicksum(self.x['Start', k2] for k2 in self.fixture.matches_team[i] if
                         k2 in self.fixture.possible_successor['Start']) +
            grb.quicksum(
                self.x[k, k2] for k in self.fixture.matches_id for k2 in self.fixture.possible_successor[k] if
                k2 in self.fixture.matches_team[i] and k != 'Start') == 1, name="c6_{0}".format(i))
            for i in self.fixture.teams_id if i != self.fixture.airport_origin}

    def _define_objective_function(self):
        """ Define objective function
        """
        """ Objective function 1 - minimize difference between first and last match of the trip """
        self.objective_travel_duration = grb.quicksum(
            self.fixture.fixtures_dict['start hours'][k] * self.x[k, 'End'] for k in self.fixture.matches_id if
            'End' in self.fixture.possible_successor[k]) - grb.quicksum(
            self.fixture.fixtures_dict['start hours'][k2] * self.x['Start', k2] for k2 in
            self.fixture.possible_successor['Start'])

        """ Objective function 2 - minimize total travel time """
        self.objective_travel_time = grb.quicksum(
            self.fixture.travel_times[
                (self.fixture.fixtures_dict['home team'][k], self.fixture.fixtures_dict['home team'][k2])] *
            self.x[k, k2] for k in self.fixture.matches_id for k2 in self.fixture.possible_successor[k])

    def _set_objective_function(self):
        """ Set objective function - minimization
        """
        objs = [self.objective_travel_duration, self.objective_travel_time]
        priorities = [1, 2]  # higher priority, higher importance
        names = ['travel_duration', 'travel_time']
        reltols = [0.2, 0.1]  # relative tolerance of each objective
        weights = [1, 1]  # 1 is for minimization and -1 for maximization
        self.opt_model.ModelSense = grb.GRB.MINIMIZE
        for i, (obj, p, n, rel, w) in enumerate(zip(objs, priorities, names, reltols, weights)):
            self.opt_model.setObjectiveN(obj, index=i, priority=p, reltol=rel, name=n, weight=w)

    def _solve_model(self):
        """ Call routine classes
        """
        self._define_variables()
        self._define_constraints()
        self._define_objective_function()
        self._set_objective_function()
        self.opt_model.optimize()

    def _get_outputs(self):
        """ Sort matches chosen by mathematical model by date
        """
        schedule_dict = {'Match': [], 'Stadium Name': [], 'Stadium City': [], 'Stadium Lat' : [], 'Stadium Lon': [],
                         'Home Team': [], 'Away Team': [], 'Match Date': []}
        for k in self.fixture.matches_id:
            for k2 in self.fixture.possible_successor[k]:
                if self.x[k, k2].X > 0.1:
                    if k != 'Start':
                        schedule_dict['Match'].append(k)
                        schedule_dict['Home Team'].append(self.fixture.fixtures_dict['home team'][k])
                        schedule_dict['Away Team'].append(self.fixture.fixtures_dict['away team'][k])
                        schedule_dict['Stadium Name'].append(self.fixture.fixtures_dict['stadium name'][k])
                        schedule_dict['Stadium City'].append(self.fixture.fixtures_dict['stadium city'][k])
                        schedule_dict['Stadium Lat'].append(self.fixture.fixtures_dict['stadium lat'][k])
                        schedule_dict['Stadium Lon'].append(self.fixture.fixtures_dict['stadium lon'][k])
                        schedule_dict['Match Date'].append(
                            self.fixture.fixtures_dict['date'][k].strftime('%Y-%m-%d %H:%M'))
                        if k2 == 'End':
                            schedule_dict['Match'].append(k2)
                            schedule_dict['Home Team'].append(self.fixture.fixtures_dict['home team'][k2])
                            schedule_dict['Away Team'].append(self.fixture.fixtures_dict['away team'][k2])
                            schedule_dict['Stadium Name'].append(self.fixture.fixtures_dict['stadium name'][k2])
                            schedule_dict['Stadium City'].append(self.fixture.fixtures_dict['stadium city'][k2])
                            schedule_dict['Stadium Lat'].append(self.fixture.fixtures_dict['stadium lat'][k2])
                            schedule_dict['Stadium Lon'].append(self.fixture.fixtures_dict['stadium lon'][k2])
                            schedule_dict['Match Date'].append(
                                (self.fixture.fixtures_dict['date'][k] + timedelta(days=1)).strftime('%Y-%m-%d %H:%M'))
                    else:
                        first_match = k2
        schedule_dict['Match'].append('Start')
        schedule_dict['Home Team'].append(self.fixture.fixtures_dict['home team']['Start'])
        schedule_dict['Away Team'].append(self.fixture.fixtures_dict['away team']['Start'])
        schedule_dict['Stadium Name'].append(self.fixture.fixtures_dict['stadium name']['Start'])
        schedule_dict['Stadium City'].append(self.fixture.fixtures_dict['stadium city']['Start'])
        schedule_dict['Stadium Lat'].append(self.fixture.fixtures_dict['stadium lat']['Start'])
        schedule_dict['Stadium Lon'].append(self.fixture.fixtures_dict['stadium lon']['Start'])
        schedule_dict['Match Date'].append(
            (self.fixture.fixtures_dict['date'][first_match] - timedelta(days=1)).strftime('%Y-%m-%d %H:%M'))
        self.output_schedule = pd.DataFrame.from_dict(schedule_dict)
        self.output_schedule = self.output_schedule.sort_values(by='Match Date', ascending=True)
        self.output_schedule.to_csv("Output Schedule.csv", index=False)

    def _plot_maps(self):
        responses = []
        lat_lons = list(zip(self.output_schedule['Stadium Lat'], self.output_schedule['Stadium Lon']))
        for n in range(len(lat_lons) - 1):
            lat1, lon1, lat2, lon2 = lat_lons[n][0], lat_lons[n][1], lat_lons[n + 1][0], lat_lons[n + 1][1]
            response = pull_directions_api(lat1, lon1, lat2, lon2, self.fixture.route_api_key)
            responses.append(response)
        m = create_map(responses, lat_lons)
        m.save('./route_map.html')