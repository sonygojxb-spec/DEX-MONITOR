# Requirements Document

## Introduction

A desktop GUI application built with CustomTkinter that provides a modern dark-mode interface for the existing DEX Trading Agent. The GUI enables users to monitor token watchlists, view alerts, manage agent lifecycle, and configure thresholds without using the CLI. The application integrates with the existing agent architecture by running the agent loop in a background thread and exposing a new `GUIChannel` notification channel for displaying alerts in-app.

## Glossary

- **GUI_App**: The CustomTkinter-based desktop application window that hosts all visual panels and controls.
- **Agent_Thread**: A Python background thread that runs the asyncio event loop executing the DEX Trading Agent without blocking the GUI main thread.
- **Status_Bar**: A horizontal panel displaying real-time operational metrics (active pairs count, uptime, last tick time, alerts sent count).
- **Watchlist_Table**: A tabular display showing all monitored tokens with their name, severity rating, bot percentage, liquidity, and latest signal.
- **Token_Input**: A text input field paired with Add/Remove buttons for managing the watchlist by mint address.
- **Alerts_Log**: A scrollable text area displaying timestamped alert and event messages from the notification system.
- **Settings_Dialog**: A modal dialog window for configuring agent thresholds (refresh interval, bot threshold, rugpull threshold, and other numeric parameters).
- **GUIChannel**: A concrete implementation of the NotificationChannel interface that routes alerts to the Alerts_Log widget.
- **Tick_Cycle**: One complete execution of the orchestrator's per-pair monitoring loop across all active pairs (default 30 seconds).
- **Entry_Point**: The `python -m dex_agent.gui` module-level invocation that launches the desktop application.

## Requirements

### Requirement 1: Application Entry Point

**User Story:** As a developer, I want to launch the GUI with `python -m dex_agent.gui`, so that I have a dedicated desktop entry point separate from the CLI agent.

#### Acceptance Criteria

1. WHEN a user executes `python -m dex_agent.gui`, THE Entry_Point SHALL display the GUI_App window on screen within 5 seconds of invocation.
2. THE Entry_Point SHALL call `load_dotenv()` from python-dotenv to read secrets from the `.env` file before constructing the agent.
3. IF a required environment variable (MORALIS_API_KEY, SOLANA_RPC_URL, TELEGRAM_BOT_TOKEN, or TELEGRAM_CHAT_ID) is missing or empty after loading the `.env` file, THEN THE Entry_Point SHALL display an error message indicating which variable is missing and SHALL NOT attempt to construct the agent.
4. THE Entry_Point SHALL construct the agent using `build_production_agent()` with `HttpxClient`, `SolanaRpcClient`, and `NoOpSigner` matching the parameter signatures used in the existing `dex_agent/__main__.py` implementation.
5. IF `build_production_agent()` raises an exception during agent construction, THEN THE Entry_Point SHALL display an error message indicating the failure reason within the GUI_App window rather than crashing silently.
6. THE Entry_Point SHALL leave the existing `python -m dex_agent` CLI entry point unchanged such that the CLI module continues to execute its `main()` function and produce console output as before.
7. THE Entry_Point SHALL create the module files `dex_agent/gui/__init__.py` and `dex_agent/gui/app.py`.

### Requirement 2: CustomTkinter Dark-Mode Window

**User Story:** As a user, I want a modern dark-mode desktop interface, so that I can comfortably monitor the agent for extended periods.

#### Acceptance Criteria

1. THE GUI_App SHALL use the CustomTkinter library (`customtkinter`) for all widgets.
2. THE GUI_App SHALL display in dark mode by default using `customtkinter.set_appearance_mode("dark")`.
3. THE GUI_App SHALL set a minimum window size of 1100×700 pixels, sufficient to display the Status_Bar, Watchlist_Table, Token_Input, Alerts_Log, and control buttons without horizontal scrolling at the default system font size.
4. WHILE the Agent_Thread is running, THE GUI_App SHALL process user interactions (button clicks, text input, window controls) within 500 milliseconds of the user action, without freezing the main Tkinter event loop.
5. THE GUI_App SHALL display a window title containing the application name "DEX Monitor".

### Requirement 3: Status Bar Display

**User Story:** As a user, I want to see operational metrics at a glance, so that I can assess the agent's health without reading logs.

#### Acceptance Criteria

1. THE Status_Bar SHALL display the count of currently active monitored pairs retrieved from `MonitoringOrchestrator.active_count()`.
2. THE Status_Bar SHALL display the uptime duration since the Agent_Thread was started, formatted as `HH:MM:SS`.
3. THE Status_Bar SHALL display the timestamp of the last completed Tick_Cycle, formatted as `HH:MM:SS`.
4. THE Status_Bar SHALL display the total count of alerts delivered through the GUIChannel since the Agent_Thread was started.
5. WHILE the Agent_Thread is running, THE Status_Bar SHALL refresh the uptime display every 1 second and refresh the active pairs count, last tick time, and alert count every Tick_Cycle.
6. WHILE the Agent_Thread is stopped, THE Status_Bar SHALL display zero for active pairs, the last recorded tick time frozen at its final value, the uptime frozen at its final value, and the alert count retained at its accumulated total.
7. IF the Agent_Thread has not yet been started, THEN THE Status_Bar SHALL display zero for active pairs, `00:00:00` for uptime, no value for last tick time, and zero for alerts delivered.

### Requirement 4: Watchlist Table

**User Story:** As a user, I want to see the current state of all monitored tokens in a table, so that I can quickly identify tokens requiring attention.

#### Acceptance Criteria

1. THE Watchlist_Table SHALL display columns for: token name, severity rating (one of NONE, LOW, MEDIUM, HIGH, CRITICAL), bot transaction percentage (0–100), liquidity (decimal currency value), and latest signal type (ENTRY or EXIT) with its score.
2. WHEN a Tick_Cycle completes, THE Watchlist_Table SHALL update all rows with the latest data retrieved from the WatchlistRepository, SecurityEvalRepository, WalletAnalysisRepository, and SignalRepository.
3. THE Watchlist_Table SHALL support single-row selection for use with the Remove button.
4. WHEN a new token is added to the watchlist, THE Watchlist_Table SHALL display the new entry after the next Tick_Cycle refresh.
5. WHEN a token is removed from the watchlist, THE Watchlist_Table SHALL remove the corresponding row after the next Tick_Cycle refresh.
6. IF no SecurityEvaluation, WalletAnalysis, or Signal exists yet for a watchlist entry, THEN THE Watchlist_Table SHALL display a dash character ("-") in each column where data is unavailable.
7. THE Watchlist_Table SHALL display rows in the order they were added to the watchlist (insertion order from WatchlistRepository.list_active()).

### Requirement 5: Add and Remove Token Controls

**User Story:** As a user, I want to add tokens by mint address and remove selected tokens, so that I can manage the watchlist through the GUI.

#### Acceptance Criteria

1. THE Token_Input SHALL provide a single-line text entry field that accepts between 1 and 44 characters for entering a Solana mint address.
2. WHEN the user clicks the Add button with a non-empty mint address in the Token_Input, THE GUI_App SHALL call `agent.add_token(mint_address, Network.SOLANA)` on the Agent_Thread within 1 second of the click event.
3. IF the `add_token` call returns an error, THEN THE GUI_App SHALL append the error's message property to the Alerts_Log and retain the current text in the Token_Input.
4. WHEN the user clicks the Remove button with a row selected in the Watchlist_Table, THE GUI_App SHALL call `agent.remove_pair(pair_id)` for the selected row's pair identifier.
5. WHEN the `add_token` call returns a successful result, THE Token_Input SHALL clear its text content to an empty string.
6. WHILE the Agent_Thread is stopped, THE GUI_App SHALL disable the Add and Remove buttons so that click events on them produce no effect.
7. IF the user clicks the Add button with an empty or whitespace-only string in the Token_Input, THEN THE GUI_App SHALL not invoke `add_token` and SHALL leave the Token_Input unchanged.
8. IF the user clicks the Remove button with no row selected in the Watchlist_Table, THEN THE GUI_App SHALL not invoke `remove_pair` and SHALL leave the Watchlist_Table unchanged.

### Requirement 6: Alerts Log

**User Story:** As a user, I want to see timestamped alerts in the GUI, so that I can track events without switching to a terminal.

#### Acceptance Criteria

1. THE Alerts_Log SHALL display each alert entry on a new line with the format `YYYY-MM-DD HH:MM:SS [title] body`, where `title` is the Alert's title field enclosed in square brackets and `body` is the Alert's body field.
2. THE Alerts_Log SHALL be a scrollable text area that automatically scrolls to the bottom when a new entry is appended, provided the user has not manually scrolled upward; IF the user has scrolled upward from the bottom, THEN THE Alerts_Log SHALL not auto-scroll until the user scrolls back to the bottom.
3. WHEN the GUIChannel receives an alert from the Notifier, THE Alerts_Log SHALL append the alert as a new timestamped entry within the same Tick_Cycle using thread-safe GUI scheduling.
4. THE Alerts_Log SHALL retain all messages from the current session without truncation, up to a maximum of 10,000 entries, until the application is closed.
5. THE Alerts_Log SHALL be read-only so users cannot edit, delete, or insert alert text.
6. IF the Alerts_Log contains 10,000 entries and a new alert arrives, THEN THE Alerts_Log SHALL remove the oldest entry before appending the new entry.

### Requirement 7: GUIChannel Notification Integration

**User Story:** As a user, I want the GUI to receive alerts from the agent's notification system, so that I see the same alerts that would go to Telegram.

#### Acceptance Criteria

1. THE GUIChannel SHALL implement the `NotificationChannel` abstract interface (`deliver(alert) -> Result[DeliveryResult]`), accepting an `Alert` instance and returning a `Result[DeliveryResult]`.
2. THE GUIChannel SHALL be registered in the agent's notification channels list so that the Notifier dispatches every alert to the GUIChannel in addition to the existing TelegramChannel.
3. WHEN the Notifier dispatches an alert, THE GUIChannel SHALL schedule an update on the GUI main thread that appends the alert's `title` and `body` fields to the Alerts_Log widget within 500 milliseconds of receiving the `deliver` call.
4. THE GUIChannel SHALL return `Ok(DeliveryResult)` with `channel` set to its name identifier, `delivered=True`, and an empty `detail` string for every delivery attempt while the Alerts_Log widget is available.
5. THE GUIChannel SHALL use `widget.after()` or equivalent thread-safe scheduling to update the Alerts_Log from the Agent_Thread, ensuring no direct widget mutation occurs on a non-main thread.
6. IF the Alerts_Log widget has been destroyed when `deliver` is called, THEN THE GUIChannel SHALL return `Ok(DeliveryResult)` with `delivered=False` and a `detail` string indicating the widget is unavailable, without raising an exception.

### Requirement 8: Start and Stop Agent Controls

**User Story:** As a user, I want Start/Stop buttons to control the agent loop, so that I can start monitoring and cleanly shut it down.

#### Acceptance Criteria

1. WHEN the user clicks the Start button, THE GUI_App SHALL start the Agent_Thread running the agent's boot sequence and monitoring loop.
2. WHEN the user clicks the Stop button, THE GUI_App SHALL signal the Agent_Thread to stop cleanly and wait for the current Tick_Cycle to complete within 60 seconds.
3. WHILE the Agent_Thread is running, THE GUI_App SHALL disable the Start button and enable the Stop button.
4. WHILE the Agent_Thread is stopped, THE GUI_App SHALL enable the Start button and disable the Stop button.
5. IF the Agent_Thread raises an unhandled exception, THEN THE GUI_App SHALL display the error in the Alerts_Log and transition to the stopped state.
6. WHEN the user closes the GUI_App window while the Agent_Thread is running, THE GUI_App SHALL signal the Agent_Thread to stop cleanly before exiting.
7. WHILE the Agent_Thread is in a transitional state (booting or stopping), THE GUI_App SHALL disable both the Start and Stop buttons until the transition completes.
8. IF the Agent_Thread does not terminate within 60 seconds after the stop signal, THEN THE GUI_App SHALL force-terminate the thread and transition to the stopped state.

### Requirement 9: Background Thread Architecture

**User Story:** As a developer, I want the agent to run in a background thread, so that the GUI remains responsive during monitoring operations.

#### Acceptance Criteria

1. THE Agent_Thread SHALL run the asyncio event loop in a dedicated daemon thread separate from the Tkinter main thread.
2. THE Agent_Thread SHALL execute `agent.boot()` followed by the per-pair tick loop (discovery scan + orchestrator ticks) replicating the behavior from `__main__.py`.
3. THE GUI_App SHALL communicate with the Agent_Thread using thread-safe mechanisms (queue, `threading.Event`, or `widget.after()` callbacks).
4. WHEN the stop signal is set, THE Agent_Thread SHALL complete the current Tick_Cycle and then terminate within 60 seconds without interrupting in-progress provider calls; IF the Agent_Thread does not terminate within 60 seconds, THEN THE GUI_App SHALL force-terminate the thread and transition to the stopped state.
5. THE Agent_Thread SHALL not modify Tkinter widgets directly; all GUI updates SHALL be scheduled on the main thread via `widget.after()`.
6. IF `agent.boot()` raises an exception during Agent_Thread startup, THEN THE Agent_Thread SHALL propagate the error to the GUI_App via the thread-safe communication mechanism and terminate, and THE GUI_App SHALL display the error in the Alerts_Log and remain in the stopped state.

### Requirement 10: Settings Dialog

**User Story:** As a user, I want to configure agent thresholds through a dialog, so that I can tune parameters without editing files.

#### Acceptance Criteria

1. WHEN the user clicks the Settings button, THE GUI_App SHALL open the Settings_Dialog as a modal window that blocks interaction with the main window until dismissed.
2. THE Settings_Dialog SHALL display labeled input fields for each numeric parameter defined in `Config_Manager.PARAM_RANGES`: refresh_interval_s, signal_interval_s, discovery_scan_interval_s, measurement_period_s, bot_pct_threshold, holder_conc_threshold, rugpull_threshold, dump_threshold, entry_threshold, slippage_tolerance, confirmation_timeout_s, exit_alert_retries, and retention_days.
3. THE Settings_Dialog SHALL pre-populate each field with the current active configuration value from `agent.config_manager.active`, or with the documented `DEFAULTS` values if `agent.config_manager.active` is None.
4. WHEN the user clicks Save in the Settings_Dialog, THE GUI_App SHALL call `agent.config_manager.save(inputs)` with the entered values, where each value is passed as the numeric type expected by the parameter (integer for integer-typed parameters, Decimal for decimal-typed parameters).
5. IF `config_manager.save()` returns an Err containing a ConfigValidationError, THEN THE Settings_Dialog SHALL display the error message identifying the offending parameter and its allowed range, and SHALL retain the dialog open with the user's entered values preserved in all fields.
6. IF `config_manager.save()` returns an Err containing a ConfigPersistenceError, THEN THE Settings_Dialog SHALL display an error message indicating the persistence failure and SHALL retain the dialog open with the user's entered values preserved.
7. WHEN `config_manager.save()` returns Ok, THE Settings_Dialog SHALL close and THE GUI_App SHALL use the updated configuration for subsequent Tick_Cycles without requiring an Agent_Thread restart.
8. THE Settings_Dialog SHALL provide a Cancel button that closes the dialog without calling save and without modifying the active configuration.

### Requirement 11: Watchlist Data Refresh

**User Story:** As a user, I want the watchlist table to update every tick cycle, so that I always see current data.

#### Acceptance Criteria

1. WHILE the Agent_Thread is running, THE Watchlist_Table SHALL refresh its data every Tick_Cycle as defined by `Configuration.refresh_interval_s` (valid range 5–300 seconds, default 30 seconds).
2. THE Watchlist_Table SHALL retrieve token data from the `WatchlistRepository`, `SecurityEvalRepository`, `WalletAnalysisRepository`, and `SignalRepository` to populate the columns defined in Requirement 4 (token name, severity rating, bot percentage, liquidity, latest signal).
3. WHEN the refresh interval is changed via the Settings_Dialog, THE Watchlist_Table SHALL apply the new interval starting from the next scheduled refresh, without restarting or interrupting a refresh that is already in progress.
4. THE Watchlist_Table refresh SHALL execute on the Agent_Thread and push results to the main thread for rendering via `widget.after()` scheduling.
5. IF one or more repository calls fail during a refresh cycle, THEN THE Watchlist_Table SHALL retain the previously displayed data for the affected columns and display a visual staleness indicator on the affected rows until the next successful refresh.
6. WHILE the Agent_Thread is stopped, THE Watchlist_Table SHALL retain the last successfully retrieved data without further refresh attempts.

### Requirement 12: Existing CLI Preservation

**User Story:** As a developer, I want the GUI addition to not modify existing core components, so that the CLI entry point and all existing tests remain functional.

#### Acceptance Criteria

1. THE GUI_App SHALL not modify any file in the existing `dex_agent/` package outside of the new `dex_agent/gui/` directory, including no changes to `dex_agent/__init__.py` or any other existing module's source code.
2. THE Entry_Point SHALL import and instantiate `HttpxClient`, `SolanaRpcClient`, and `NoOpSigner` from `dex_agent/__main__.py` without re-declaring those classes in `dex_agent/gui/` or any other new module.
3. WHEN the `python -m dex_agent` command is executed after the GUI feature is added, THE CLI_Entry_Point SHALL start the monitoring loop, produce console output, and exit with the same exit codes (0 on Ctrl+C, non-zero on missing environment variables) as the version prior to the GUI addition.
4. THE GUIChannel SHALL implement the `NotificationChannel` abstract interface defined in `dex_agent/providers/interfaces.py` and SHALL be injected into the Notifier via its existing `channels` constructor parameter without modifying the `Notifier` class source code.
5. WHEN the existing test suite is executed via `pytest` after the GUI feature is added, THE test suite SHALL pass with zero new failures and zero modified test files.
