def count_tokens(text: str):
    """
    Approximate token count.
    1 token ≈ 4 characters for English text.
    """

    if not text:
        return 0

    return max(1, len(text) // 4)


def calculate_total_tokens(input_text: str, output_text: str):

    input_tokens = count_tokens(input_text)
    output_tokens = count_tokens(output_text)

    total_tokens = input_tokens + output_tokens

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens
    }