ALTERNATIVE_PLAN_SETTINGS = {
    'ALLOWED_RELATIVE_DIFFERENCE': 1/4,
    'ALLOWED_ABSOLUTE_DIFFERENCE': 5 * 60,
}

WALKING_SETTINGS = {
    'PACE': 1.4,  # (m/s)
    'DISTANCE_MULTIPLIER': 1.1, # Used when exact distance is unknown
}

PROSPECTING_SETTINGS = {
    'START_RADIUS': 1000,
    'START_MIN_COUNT': 10,
    'DESTINATION_RADIUS': 1000,
    'DESTINATION_MIN_COUNT': 10,
}

HEURISTIC_SETTINGS = {
    'MAX_SPEED': 20, # (m/s)
    # TODO:
    # Thats actually an average tram speed in Poznań, way too slow for admissable heuristic
    # I just left it like that, because I made some improvements,
    # and I didn't want to make algorithm to work slower after all
    # BTW, even though it is not admissable heurisitc,
    # in most cases results are otimal compared to jakdojade and google
    'TRANSFER_TIME': 180,
}

INCONVENIENCE_SETTINGS = {
    'WALK_TIME_PENALTY': 2, # Per second
    'WAIT_TIME_PENALTY': 1, # Per second
    'TRANSFER_PENALTY': 200,
}

METRICS_SETTINGS = {
    'TIME': True,
    'EXPANSIONS' : True,
}

PRINTING_SETTINGS = {
    'DEFAULT': True,
    'SETUP_TIMES' : True,
    'DATASTRUCTURES_INIT_TIMES' : True,
    'ALGORITHM_PREPROCESSING_TIMES' : True,
    'DEBUG' : False,
    'BENCHMARK' : True,
    'PRINT_PLAN' : True,
    'ALGORITHM_ITERATIONS' : True,
    }
