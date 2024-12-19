from ebus.custom_settings.algorithm_settings import PRINTING_SETTINGS


def time_to_seconds(time_str: str) -> int:
    """Maps time from HH:MM:SS format to total no. of seconds"""
    hms = [int(i) for i in time_str.split(':')]
    return hms[0] * 3600 + hms[1] * 60 + hms[2]


def seconds_to_time(time_seconds) -> str:
    """Maps time from total no. of seconds to HH:MM:SS format"""
    time_seconds = int(time_seconds)
    hours = time_seconds // 3600
    time_seconds %= 3600
    minutes = time_seconds // 60
    time_seconds %= 60
    return f"{hours:02}:{minutes:02}:{time_seconds:02}"


def custom_print(message, level='DEFAULT'):
    if PRINTING_SETTINGS[level]:
        print(f"[{level}] {message}")


def plans_to_string(found_plans, data):
    result = ""
    for i, plan in enumerate(found_plans):
        result += '\t-----------------\n'
        result += f'\tPlan {i}\n'
        result += "\t" + plan.format(data).replace("\n", "\n\t") + "\n"
    return result
