from ste.diagnostics.check import CHECK_ALL_PROFILE, CHECK_PROFILES, merge_required_from_profile


def test_check_profiles_keys() -> None:
    assert set(CHECK_PROFILES) == {"api", "fetch", "dev"}
    assert CHECK_ALL_PROFILE == "all"


def test_merge_api_dedupes_and_order() -> None:
    assert merge_required_from_profile("api", ["httpx", "fastapi", "pandas"]) == [
        "fastapi",
        "uvicorn",
        "httpx",
        "pandas",
    ]


def test_merge_extra_only_without_profile() -> None:
    assert merge_required_from_profile(None, ["x", "y", "x"]) == ["x", "y"]


def test_run_checks_json_contains_effective_required() -> None:
    from ste.diagnostics.check import run_checks

    r = run_checks(required_modules=["pandas"], profile="api")
    j = r.to_jsonable()
    assert j["effective_required"] == ["fastapi", "uvicorn", "httpx", "pandas"]


def test_merge_all_profile_collects_all_modules_in_order() -> None:
    assert merge_required_from_profile("all", ["fastapi", "x"]) == [
        "fastapi",
        "uvicorn",
        "httpx",
        "pytest",
        "ruff",
        "yfinance",
        "x",
    ]
