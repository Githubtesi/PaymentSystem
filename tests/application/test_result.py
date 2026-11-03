from seedwork.application.result import Result


def test_ok_result():
    result = Result.ok({"id": "1"})

    assert result.is_success
    assert result.value == {"id": "1"}
    assert result.error is None


def test_failed_result():
    result = Result.fail("validation failed", code="VALIDATION")

    assert not result.is_success
    assert result.error == "validation failed"
    assert result.code == "VALIDATION"


def test_result_is_immutable():
    result = Result.ok("value")

    try:
        result.value = "changed"
    except AttributeError:
        pass
    else:
        raise AssertionError("Result should be immutable")
