# The-Match-Routing-Problem

Imports matches of a specific league and season from API football https://api-football-v1.p.rapidapi.com and solves the Match Routing Problem using Gurobipy.

The Match Routing Problem can be stated as the following: given the set of matches (fixtures) of a league, build a trip schedule starting and ending at the same point, making sure to:
            - Watch exactly one match of each team of the league
            - Respect travel times between stadiums
            - Respect minimum allowed time between two matches
            
While minimizing:
            - The Time difference between the last watched and first match watched (objective 1) and
            - Total travel time (objective 2)
