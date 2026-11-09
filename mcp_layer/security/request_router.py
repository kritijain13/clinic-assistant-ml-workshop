import re


def is_other_patient_data_request(query: str, authenticated_patient_id: int | None = None) -> bool:
    """Reject attempts to look up a patient's private data outside the session owner."""
    text = query.casefold()
    data_request = re.search(
        r"\b(details?|information|info|data|records?|profile|address|phone|contact|age|dob|medical|clinical|diagnosis|history|name|email|gender|sex|birth|identifier|who)\b",
        text
    )
    if not data_request or not re.search(r"\bpatients?\b", text):
        return False

    id_match = re.search(r"\bpatient\s*(?:id|number|no\.?)\s*[:#-]?\s*(\d+)\b", text)
    if id_match:
        return authenticated_patient_id is None or int(id_match.group(1)) != authenticated_patient_id

    own_record_request = re.search(
        r"\b(?:my|own|mera|meri|mere)\b.{0,30}\b(?:patient|details?|information|info|data|records?|profile|medical|clinical|diagnosis|history|name|email|gender|sex|birth)\b"
        r"|\b(?:patient|details?|information|info|data|records?|profile|medical|clinical|diagnosis|history|name|email|gender|sex|birth)\b.{0,30}\b(?:my|own|mera|meri|mere)\b",
        text
    )
    return own_record_request is None


def get_query_intent(query: str) -> str:
    query = query.lower().strip()

    # Requests to find/list/recommend a doctor must be answered from the
    # doctor database, even when phrased as a recommendation question.
    if "doctor" in query and any(term in query for term in (
        "find", "show", "available", "recommend", "list", "search", "book", "who is"
    )):
        return "doctor"

    # Complex queries → LLM
    complex_words = [
        "summarize",
        "summary",
        "explain",
        "analyze",
        "analyse",
        "why",
        "how",
        "recommend",
        "advice",
        "should i",
        "what should",
        "can you explain"
    ]

    for word in complex_words:
        if re.search(r"\b" + re.escape(word) + r"\b", query):
            return "llm"

    # Appointment related
    if "appointment" in query:
        return "appointment"

    # Doctor related
    if "doctor" in query or "doctors" in query:
        return "doctor"

    # Prescription related
    if "prescription" in query:
        return "prescription"

    # History related
    if "history" in query:
        return "history"

    # Unknown → LLM
    return "llm"


def should_use_llm(query: str) -> bool:
    return get_query_intent(query) == "llm"
