from app.api.deps import is_valid_csrf_pair, should_enforce_csrf


def test_should_enforce_csrf_for_unsafe_api_calls_with_session_cookie() -> None:
    assert (
        should_enforce_csrf(
            method="POST",
            path="/api/products",
            access_cookie_present=True,
            csrf_enabled=True,
        )
        is True
    )


def test_should_not_enforce_csrf_on_safe_or_non_api_calls() -> None:
    assert (
        should_enforce_csrf(
            method="GET",
            path="/api/products",
            access_cookie_present=True,
            csrf_enabled=True,
        )
        is False
    )
    assert (
        should_enforce_csrf(
            method="POST",
            path="/internal/jobs/check-prices",
            access_cookie_present=True,
            csrf_enabled=True,
        )
        is False
    )
    assert (
        should_enforce_csrf(
            method="POST",
            path="/api/products",
            access_cookie_present=False,
            csrf_enabled=True,
        )
        is False
    )


def test_is_valid_csrf_pair_requires_non_empty_equal_values() -> None:
    assert is_valid_csrf_pair("abc", "abc") is True
    assert is_valid_csrf_pair("abc", "xyz") is False
    assert is_valid_csrf_pair("", "abc") is False
    assert is_valid_csrf_pair("abc", "") is False
    assert is_valid_csrf_pair(None, "abc") is False
    assert is_valid_csrf_pair("abc", None) is False

