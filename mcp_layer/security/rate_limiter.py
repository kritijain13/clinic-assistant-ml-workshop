import time


MAX_REQUESTS_PER_MINUTE = 10

user_requests = {}


def check_rate_limit(user_id: int):

    current_time = time.time()

    if user_id not in user_requests:
        user_requests[user_id] = []

    # Sirf last 60 seconds ke requests rakho
    user_requests[user_id] = [
        request_time
        for request_time in user_requests[user_id]
        if current_time - request_time < 60
    ]

    if len(user_requests[user_id]) >= MAX_REQUESTS_PER_MINUTE:
        return False

    user_requests[user_id].append(current_time)

    return True