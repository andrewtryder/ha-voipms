"""Tests verifying strict socket isolation."""

import socket

import pytest
import pytest_socket
from pytest_homeassistant_custom_component.plugins import HASocketBlockedError

import custom_components.voipms  # noqa: F401


def test_socket_creation_blocked_by_default() -> None:
    """Verify that creating internet sockets without a scoped loopback fixture is blocked."""
    with pytest.raises(pytest_socket.SocketBlockedError) as exc_info:
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Narrowly remove only this test's deliberate exception instance so verify_cleanup
    # does not fail teardown, while preserving any unexpected socket attempt diagnostics.
    if (
        isinstance(exc_info.value, HASocketBlockedError)
        and exc_info.value in HASocketBlockedError.instances
    ):
        HASocketBlockedError.instances.remove(exc_info.value)


def test_dns_resolution_blocked_by_default() -> None:
    """Verify that external DNS resolution is blocked in standard tests."""
    with pytest.raises(
        (pytest_socket.SocketBlockedError, RuntimeError),
        match=r"^(DNS resolution disabled in tests|A test tried to use socket\.getaddrinfo\.)$",
    ) as exc_info:
        socket.getaddrinfo("example.com", 80)

    # Narrowly remove only this test's deliberate exception instance so verify_cleanup
    # does not fail teardown, while preserving any unexpected socket attempt diagnostics.
    if (
        isinstance(exc_info.value, HASocketBlockedError)
        and exc_info.value in HASocketBlockedError.instances
    ):
        HASocketBlockedError.instances.remove(exc_info.value)
