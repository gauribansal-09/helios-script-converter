from helios_converter.exceptions import ConversionError


def _raise(exc: BaseException) -> BaseException:
    """Raise and return an exception so it has a real traceback."""
    try:
        raise exc
    except type(exc) as e:
        return e


def test_no_cause_has_no_location() -> None:
    err = ConversionError("something went wrong")
    assert str(err) == "something went wrong"


def test_cause_with_traceback_appends_location() -> None:
    cause = _raise(ValueError("bad value"))
    err = ConversionError("conversion failed", cause=cause)
    msg = str(err)
    assert msg.startswith("conversion failed (at ")
    assert "test_exceptions.py:" in msg


def test_cause_without_traceback_has_no_location() -> None:
    cause = ValueError("never raised")
    err = ConversionError("conversion failed", cause=cause)
    assert str(err) == "conversion failed"


def test_cause_is_set() -> None:
    cause = _raise(RuntimeError("original"))
    err = ConversionError("wrapped", cause=cause)
    assert err.__cause__ is cause


def test_none_cause_not_set() -> None:
    err = ConversionError("no cause")
    assert err.__cause__ is None
