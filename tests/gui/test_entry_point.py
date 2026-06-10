"""Property-based tests for the GUI entry point (dex_agent.gui.__main__).

Tests validate that the entry point correctly handles environment variable
validation and agent construction failures as specified in the design document.
"""

from __future__ import annotations

from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from dex_agent.gui.__main__ import _check_env_vars, REQUIRED_ENV_VARS

# Alias for strategy use
REQUIRED_VARS = REQUIRED_ENV_VARS


# ---------------------------------------------------------------------------
# Feature: dex-gui, Property 1: Missing environment variable detection
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    missing_vars=st.sets(st.sampled_from(REQUIRED_VARS), min_size=1),
)
def test_property_1_missing_env_var_detection(missing_vars: set[str]) -> None:
    """Validates: Requirements 1.3

    For any subset of the required environment variables where at least one
    variable is missing or empty, _check_env_vars() SHALL return those exact
    variables.
    """
    # Build an environment where the missing vars are absent and the rest are set
    present_vars = set(REQUIRED_VARS) - missing_vars
    mock_env = {var: "valid_value" for var in present_vars}

    with patch.dict("os.environ", mock_env, clear=True):
        result = _check_env_vars()

    # Assert all missing vars are detected
    assert set(result) == missing_vars, (
        f"Expected missing vars {missing_vars}, got {set(result)}"
    )

    # Assert each specific missing variable is named in the result
    for var in missing_vars:
        assert var in result, f"Missing var '{var}' not reported by _check_env_vars()"


@settings(max_examples=100)
@given(
    missing_vars=st.sets(st.sampled_from(REQUIRED_VARS), min_size=1),
)
def test_property_1_main_does_not_construct_agent_when_vars_missing(
    missing_vars: set[str],
) -> None:
    """Validates: Requirements 1.3

    When required environment variables are missing, main() SHALL NOT call
    build_production_agent() and SHALL display an error naming the missing vars.
    """
    # Build an environment where the missing vars are absent and the rest are set
    present_vars = set(REQUIRED_VARS) - missing_vars
    mock_env = {var: "valid_value" for var in present_vars}

    with (
        patch.dict("os.environ", mock_env, clear=True),
        patch(
            "dex_agent.gui.__main__.build_production_agent"
        ) as mock_build,
        patch("dex_agent.gui.__main__._show_error_window") as mock_show_error,
    ):
        from dex_agent.gui.__main__ import main

        main()

    # Agent construction must NOT be attempted
    mock_build.assert_not_called()

    # Error window must be shown with a message naming each missing var
    mock_show_error.assert_called_once()
    error_message = mock_show_error.call_args[0][0]
    for var in missing_vars:
        assert var in error_message, (
            f"Error message does not mention missing var '{var}': {error_message}"
        )


# ---------------------------------------------------------------------------
# Feature: dex-gui, Property 2: Agent construction/boot exception display
# ---------------------------------------------------------------------------

# Mock customtkinter at module level so patching the GUI module works in CI
# where customtkinter may not be installed. The module was already imported
# above (for Property 1) so we just need to ensure the patches work.

import sys
from unittest.mock import MagicMock

# Ensure customtkinter mock is available if not installed
if "customtkinter" not in sys.modules:
    _mock_ctk = MagicMock()
    sys.modules["customtkinter"] = _mock_ctk

import dex_agent.gui.__main__ as _gui_main_module


@settings(max_examples=100, deadline=None)
@given(exc_message=st.text(min_size=1, max_size=200))
def test_property_2_agent_construction_exception_displayed(exc_message: str) -> None:
    """**Validates: Requirements 1.5, 9.6**

    For any exception raised during build_production_agent(), the GUI SHALL
    display the exception's message in an error window and SHALL NOT proceed
    to launch DEXMonitorApp (remains in stopped state / returns early).
    """
    # Build an exception with the generated message
    exc = Exception(exc_message)

    # Patch all env vars as present so we get past the env var check
    fake_env = {
        "MORALIS_API_KEY": "test_key_123",
        "SOLANA_RPC_URL": "https://api.mainnet-beta.solana.com",
        "TELEGRAM_BOT_TOKEN": "bot_token_abc",
        "TELEGRAM_CHAT_ID": "chat_id_xyz",
    }

    captured_messages: list[str] = []

    def mock_show_error_window(message: str) -> None:
        captured_messages.append(message)

    with (
        patch.dict("os.environ", fake_env, clear=False),
        patch(
            "dex_agent.gui.__main__.build_production_agent", side_effect=exc
        ),
        patch(
            "dex_agent.gui.__main__._show_error_window",
            side_effect=mock_show_error_window,
        ),
        patch("dex_agent.gui.__main__.load_dotenv"),
    ):
        _gui_main_module.main()

    # The exception message must appear in the error display
    assert len(captured_messages) == 1, (
        f"Expected exactly 1 error message, got {len(captured_messages)}"
    )
    displayed_msg = captured_messages[0]
    assert str(exc) in displayed_msg, (
        f"Exception message '{exc_message}' not found in displayed error: "
        f"'{displayed_msg}'"
    )


@settings(max_examples=100, deadline=None)
@given(exc_message=st.text(min_size=1, max_size=200))
def test_property_2_agent_construction_exception_does_not_launch_app(
    exc_message: str,
) -> None:
    """**Validates: Requirements 1.5, 9.6**

    For any exception raised during build_production_agent(), the application
    SHALL NOT proceed to launch DEXMonitorApp (remains in stopped state).
    The app must return early without creating a CTk window for the main app.
    """
    exc = RuntimeError(exc_message)

    fake_env = {
        "MORALIS_API_KEY": "test_key_123",
        "SOLANA_RPC_URL": "https://api.mainnet-beta.solana.com",
        "TELEGRAM_BOT_TOKEN": "bot_token_abc",
        "TELEGRAM_CHAT_ID": "chat_id_xyz",
    }

    def mock_show_error_window(message: str) -> None:
        pass  # Swallow the error display; we're testing the app doesn't launch

    mock_ctk_class = MagicMock()

    with (
        patch.dict("os.environ", fake_env, clear=False),
        patch(
            "dex_agent.gui.__main__.build_production_agent", side_effect=exc
        ),
        patch(
            "dex_agent.gui.__main__._show_error_window",
            side_effect=mock_show_error_window,
        ),
        patch("dex_agent.gui.__main__.load_dotenv"),
        patch("dex_agent.gui.__main__.customtkinter.CTk", mock_ctk_class),
    ):
        _gui_main_module.main()

    # DEXMonitorApp / fallback CTk window should NOT have been created
    # (the function should have returned early after showing the error)
    mock_ctk_class.assert_not_called()
