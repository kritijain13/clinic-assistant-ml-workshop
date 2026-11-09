from mcp_layer.token_management.context_manager import (
    prepare_context
)

from mcp_layer.token_management.conversation_summarizer import (
    should_summarize,
    get_messages_for_summary,
    create_summary_prompt
)


def prepare_conversation(messages, summary=None):

    # Step 1: Check whether conversation is long
    summarize_required = should_summarize(messages)

    summary_prompt = None

    # Step 2: Prepare old messages for summarization
    if summarize_required:

        old_messages = get_messages_for_summary(
            messages
        )

        summary_prompt = create_summary_prompt(
            old_messages
        )

    # Step 3: Keep only required context
    context = prepare_context(
        messages,
        summary
    )

    return {
        "context": context,
        "summarize_required": summarize_required,
        "summary_prompt": summary_prompt
    }