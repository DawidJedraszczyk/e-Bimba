from datetime import datetime



def convert_datetime(datetime_str):
    # Parse the input string into a datetime object
    dt = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M')

    # Extract the date and time from the datetime object
    date_obj = dt.date()
    time_obj = dt.time()

    return date_obj, time_obj


# def prepare_session_response(algorithm_results):
#     response = {}
#     for index, results in enumerate(algorithm_results):
#         response[index] = {}
#         for bus_index, buses in enumerate(results):
#             response[index][bus_index] = {}
#             for key, value in buses.items():
#                 response[index][bus_index][key] = value.id
#
#     return response