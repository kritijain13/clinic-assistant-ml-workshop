import time


DUPLICATE_WINDOW = 10  # seconds

recent_requests = {}


def is_duplicate_request(user_id: int, query: str):

    current_time = time.time()

    query = query.lower().strip()

    key = (user_id, query)

    if key in recent_requests:

        previous_time = recent_requests[key]

        if current_time - previous_time < DUPLICATE_WINDOW:
            return True

    recent_requests[key] = current_time

    return False