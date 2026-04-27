from ste.eval.replay_io import (
    CLI_REPLAY_IO_EXIT,
    PARQUET_REPLAY_READ_ERRORS,
    parquet_invalid_message,
    parquet_not_found_message,
)


def test_parquet_not_found_message_uses_fallback() -> None:
    e = FileNotFoundError(2, "msg", "from_exc")
    assert "from_exc" in parquet_not_found_message(e, "fallback")
    e2 = FileNotFoundError("bare")
    assert "fallback" in parquet_not_found_message(e2, "fallback")


def test_parquet_invalid_message_includes_exc() -> None:
    assert "x" in parquet_invalid_message(ValueError("x"))


def test_cli_exit_constant_is_two() -> None:
    assert CLI_REPLAY_IO_EXIT == 2


def test_tuple_contains_expected_types() -> None:
    assert ValueError in PARQUET_REPLAY_READ_ERRORS
    assert KeyError in PARQUET_REPLAY_READ_ERRORS
