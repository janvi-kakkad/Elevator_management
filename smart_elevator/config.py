"""Configuration constants for the Smart Elevator Management System."""

# Startup input bounds
MIN_ELEVATORS = 2
MAX_ELEVATORS = 5
MIN_FLOORS = 5
MAX_FLOORS = 20

# Runtime-configured building values (set in main.py before GUI starts)
NUM_ELEVATORS = None
NUM_FLOORS = None

# Common direction labels
DIRECTION_UP = "UP"
DIRECTION_DOWN = "DOWN"
DIRECTION_IDLE = "IDLE"

# Time constants
FLOOR_TRAVEL_TIME = 3
DOOR_OPEN_TIME = 2
DOOR_CLOSE_TIME = 1
DOOR_HOLD_MAX_TIME = 3

# Capacity
MAX_CAPACITY = 8

# Genetic Algorithm
GA_POPULATION_SIZE = 20
GA_GENERATIONS = 50
GA_MUTATION_RATE = 0.15
GA_TOURNAMENT_SIZE = 3
GA_ELITISM_COUNT = 2

# Fuzzy membership boundaries
FUZZY_NEAR_MAX = 5
FUZZY_FAR_MIN = 7

# Fuzzy output scores
SCORE_VERY_HIGH = 95
SCORE_HIGH = 75
SCORE_MEDIUM = 50
SCORE_LOW = 30
SCORE_VERY_LOW = 10

# Simulation
SIM_TICK_INTERVAL_MS = 500


def set_building_config(num_elevators, num_floors):
    """
    Store validated runtime building size in module constants.

    Args:
        num_elevators: Number of elevators as int.
        num_floors: Number of floors as int.

    Returns:
        bool: True when values are valid and stored, else False.
    """
    global NUM_ELEVATORS
    global NUM_FLOORS

    if not isinstance(num_elevators, int) or not isinstance(num_floors, int):
        return False

    if num_elevators < MIN_ELEVATORS or num_elevators > MAX_ELEVATORS:
        return False

    if num_floors < MIN_FLOORS or num_floors > MAX_FLOORS:
        return False

    NUM_ELEVATORS = num_elevators
    NUM_FLOORS = num_floors
    return True
