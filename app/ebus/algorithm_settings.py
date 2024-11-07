WALKING_SETTINGS = {
    'PACE': 1.4,  # (m/s)
    'ALWAYS_WALKING_TIME_CONSTANT': 180,   #time_to_seconds('00:03:00')
    'TIME_WITHIN_WALKING': 600, #time_to_seconds('00:10:00')
}

HEURISTIC_SETTINGS = {
    'MAX_SPEED': 5.56, # (m/s)
    # TODO:
    # Thats actually an average tram speed in Poznań, way too slow for admissable heuristic
    # I just left it like that, because I made some improvements,
    # and I didn't want to make algorithm to work slower after all
    # BTW, even though it is not admissable heurisitc,
    # in most cases results are otimal compared to jakdojade and google
    'ALWAYS_WALKING_TIME_CONSTANT': 180 # seconds
}

PRINTING_SETTINGS = {
    'DEFAULT': True,
    'SETUP_TIMES' : True,
    'DATASTRUCTURES_INIT_TIMES' : True,
    'ALGORITHM_PREPROCESSING_TIMES' : True,
    'DEBUG' : True,
    'BENCHMARK' : True,
    'PRINT_PLAN' : True,
    'ALGORITHM_ITERATIONS' : True,
    }