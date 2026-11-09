MAX_RECENT_MESSAGES = 6


def get_recent_messages(messages):
    """
    Keep only the most recent messages.
    """

    if len(messages) <= MAX_RECENT_MESSAGES:
        return messages

    return messages[-MAX_RECENT_MESSAGES:]


def prepare_context(messages, summary=None):

    recent_messages = get_recent_messages(messages)

    context = []

    if summary:
        context.append({
            "role": "system",
            "content": f"Previous conversation summary: {summary}"
        })

    context.extend(recent_messages)

    return context