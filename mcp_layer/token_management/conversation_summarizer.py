SUMMARY_THRESHOLD = 10


def should_summarize(messages):
    return len(messages) > SUMMARY_THRESHOLD


def get_messages_for_summary(messages):
    if not should_summarize(messages):
        return []

    return messages[:-6]


def create_summary_prompt(messages):
    if not messages:
        return None

    conversation_text = ""

    for message in messages:
        role = message.get("role", "unknown")
        content = message.get("content", "")

        conversation_text += f"{role}: {content}\n"

    prompt = f"""
Summarize the important information from this conversation.
Keep only information that may be useful for future questions.

Conversation:
{conversation_text}
"""

    return prompt