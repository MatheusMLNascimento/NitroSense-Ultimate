import time

import pytest

from nitrosense.core.error_codes import (
    ErrorCode,
    CircuitBreaker,
    CircuitBreakerOpenException,
    get_error_description,
    is_critical,
    is_recoverable,
)


def test_error_description_and_critical_flags():
    assert "Operation successful" in get_error_description(ErrorCode.SUCCESS)
    assert is_critical(ErrorCode.CRITICAL_TEMP_95C)
    assert not is_recoverable(ErrorCode.CRITICAL_SYSTEM_FAILURE)
    assert is_recoverable(ErrorCode.NBFC_TIMEOUT)


def test_circuit_breaker_opens_after_threshold(monkeypatch):
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=60)

    def failing_call():
        raise RuntimeError("failure")

    with pytest.raises(RuntimeError):
        breaker.call(failing_call)

    with pytest.raises(RuntimeError):
        breaker.call(failing_call)

    with pytest.raises(CircuitBreakerOpenException):
        breaker.call(lambda: None)


def test_circuit_breaker_recovery():
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    call_count = 0

    def failing_call():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("failure")
        return "success"

    with pytest.raises(RuntimeError):
        breaker.call(failing_call)

    with pytest.raises(RuntimeError):
        breaker.call(failing_call)

    with pytest.raises(CircuitBreakerOpenException):
        breaker.call(failing_call)

    time.sleep(0.2)  # Wait for recovery

    result = breaker.call(failing_call)
    assert result == "success"


def test_circuit_breaker_success_resets():
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=60)

    def sometimes_failing():
        return "success"

    breaker.call(sometimes_failing)
    breaker.call(sometimes_failing)
    # Should not be open
    result = breaker.call(sometimes_failing)
    assert result == "success"


def test_error_code_enum_values():
    assert ErrorCode.SUCCESS.value == 0
    assert ErrorCode.CRITICAL_SYSTEM_FAILURE.value == 1000


def test_get_error_description_unknown():
    desc = get_error_description(9999)
    assert "Unknown error" in desc


def test_is_critical_various_codes():
    assert is_critical(ErrorCode.CRITICAL_TEMP_95C)
    assert is_critical(ErrorCode.CRITICAL_SYSTEM_FAILURE)
    assert not is_critical(ErrorCode.SUCCESS)
    assert not is_critical(ErrorCode.NBFC_TIMEOUT)


def test_is_recoverable_various_codes():
    assert is_recoverable(ErrorCode.NBFC_TIMEOUT)
    assert is_recoverable(ErrorCode.SENSOR_READ_ERROR)
    assert not is_recoverable(ErrorCode.CRITICAL_SYSTEM_FAILURE)


def test_circuit_breaker_state():
    breaker = CircuitBreaker()
    assert breaker.state == "closed"
    # After failures, it would be "open", but testing state directly
    breaker._failure_count = 3
    breaker._state = "open"
    assert breaker.state == "open"


def test_circuit_breaker_call_success():
    breaker = CircuitBreaker()
    result = breaker.call(lambda: "ok")
    assert result == "ok"
    assert breaker._failure_count == 0


def test_circuit_breaker_call_failure():
    breaker = CircuitBreaker()
    with pytest.raises(RuntimeError):
        breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("test")))
    assert breaker._failure_count == 1
