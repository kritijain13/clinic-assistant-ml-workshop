import secrets

from clinic_assistant.auth.security import hash_password, verify_password


def test_password_hashing_and_verification():
    password = secrets.token_urlsafe(24)
    wrong_password = secrets.token_urlsafe(24)
    hashed_password = hash_password(password)

    assert hashed_password != password
    assert verify_password(password, hashed_password)
    assert not verify_password(wrong_password, hashed_password)
