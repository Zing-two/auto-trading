def get_int_for_interval(interval: str):
    if interval == "1m":
        return 60
    elif interval == "5m":
        return 300
    elif interval == "15m":
        return 90
    elif interval == "1h":
        return 360
    return 60


def get_end_time(start_time: int, interval: str, limit: int):
    return start_time + get_int_for_interval(interval) * limit * 1000
