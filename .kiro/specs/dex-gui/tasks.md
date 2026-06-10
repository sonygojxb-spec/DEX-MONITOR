# Implementation Plan: DEX GUI

## Overview

Build a desktop GUI application using CustomTkinter that wraps the existing DEX Trading Agent. All new code lives in `dex_agent/gui/` with zero modifications to existing files. The GUI runs the agent in a background daemon thread, communicates state via a thread-safe queue, and routes alerts through a new `GUIChannel` implementation of `NotificationChannel`.

## Tasks

- [x] 1. Set up GUI package structure and entry point
  - [x] 1.1 Create the `dex_agent/gui/` package with `__init__.py`, `__main__.py`, and directory scaffolding
    - Create `dex_agent/gui/__init__.py` (package marker)
    - Create `dex_agent/gui/__main__.py` with env var validation, `load_dotenv()`, agent construction via `build_production_agent()`, and `DEXMonitorApp` launch
    - Create `dex_agent/gui/frames/__init__.py` and `dex_agent/gui/dialogs/__init__.py`
    - Import `HttpxClient`, `SolanaRpcClient`, `NoOpSigner` from `dex_agent/__main__`
    - Display error label in GUI if required env vars are missing (MORALIS_API_KEY, SOLANA_RPC_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    - Display error in Alerts_Log if `build_production_agent()` raises an exception
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 12.1, 12.2_

  - [x] 1.2 Write property tests for entry point env var validation
    - **Property 1: Missing environment variable detection**
    - **Validates: Requirements 1.3**
    - Use `st.sets(st.sampled_from(REQUIRED_VARS))` to generate subsets of missing vars
    - Assert error message names the specific missing variable and agent is not constructed

  - [x] 1.3 Write property test for agent construction exception display
    - **Property 2: Agent construction/boot exception display**
    - **Validates: Requirements 1.5, 9.6**
    - Use `st.from_type(Exception)` to generate arbitrary exceptions
    - Assert exception message appears in Alerts_Log and state remains stopped

- [x] 2. Implement data models and AgentThread
  - [x] 2.1 Create data models (`AgentState`, `WatchlistRow`) in `dex_agent/gui/thread.py`
    - Define `AgentState` frozen dataclass with fields: active_pairs, uptime_seconds, last_tick_time, alerts_count, watchlist_rows, is_running, error
    - Define `WatchlistRow` frozen dataclass with fields: pair_id, token_name, severity, bot_pct, liquidity, signal_type, signal_score
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1_

  - [x] 2.2 Implement `AgentThread` class in `dex_agent/gui/thread.py`
    - Create daemon thread running `asyncio.run()` with the agent tick loop
    - Implement `start()`, `request_stop()`, `is_running()`, `is_transitioning()`, `submit()` methods
    - Use `threading.Event` for stop signaling
    - Push `AgentState` snapshots to `queue.Queue` after each tick
    - Collect state from repositories (WatchlistRepository, SecurityEvalRepository, WalletAnalysisRepository, SignalRepository)
    - Handle unhandled exceptions: set error in AgentState, transition to stopped
    - Implement 60-second timeout on stop with force-termination fallback
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 8.2, 8.5, 8.8_

- [x] 3. Implement GUIChannel notification integration
  - [x] 3.1 Create `GUIChannel` class in `dex_agent/gui/channel.py`
    - Implement `NotificationChannel` abstract interface (`deliver(alert) -> Result[DeliveryResult]`)
    - Use `widget.after()` for thread-safe scheduling to Alerts_Log
    - Return `Ok(DeliveryResult(channel=name, delivered=True, detail=""))` when widget available
    - Return `Ok(DeliveryResult(channel=name, delivered=False, detail="widget unavailable"))` when widget destroyed
    - Catch `TclError` gracefully without raising
    - Implement `set_widget(widget)` for deferred widget binding
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 12.4_

  - [x] 3.2 Write property test for GUIChannel deliver contract
    - **Property 11: GUIChannel deliver contract**
    - **Validates: Requirements 7.4, 7.6**
    - Use `st.builds(Alert)` + `st.booleans()` for widget availability
    - Assert correct DeliveryResult based on widget state

- [x] 4. Checkpoint - Ensure core infrastructure tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Status Bar frame
  - [x] 5.1 Create `StatusBarFrame` in `dex_agent/gui/frames/status_bar.py`
    - Display labels for: active pairs count, uptime (HH:MM:SS), last tick time (HH:MM:SS), alerts count
    - Implement `update_state(state: AgentState)` method to refresh all labels
    - Implement `_tick_uptime()` with 1-second `after()` scheduling for live uptime counter
    - Show zeros/empty on initial state before agent starts
    - Freeze uptime and last tick when agent stops; retain alert count
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [x] 5.2 Write property tests for Status Bar
    - **Property 3: Status bar numeric accuracy**
    - **Validates: Requirements 3.1, 3.4**
    - Use `st.integers(min_value=0)` to generate active_pairs and alerts_count
    - Assert displayed values match input integers exactly

  - [x] 5.3 Write property test for time duration formatting
    - **Property 4: Time duration formatting**
    - **Validates: Requirements 3.2, 3.3**
    - Use `st.integers(min_value=0, max_value=360000)` for duration seconds
    - Assert output matches `HH:MM:SS` pattern with correct arithmetic

- [x] 6. Implement Watchlist Table frame
  - [x] 6.1 Create `WatchlistTableFrame` in `dex_agent/gui/frames/watchlist.py`
    - Display columns: token name, severity, bot %, liquidity, signal type, signal score
    - Implement `update_rows(rows: list[WatchlistRow])` to refresh table contents
    - Implement `get_selected_pair_id() -> str | None` for single-row selection
    - Display `"-"` for any field that is None or unavailable
    - Preserve insertion order from input list
    - Retain previously displayed data on repository failure (staleness)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 11.1, 11.2, 11.4, 11.5, 11.6_

  - [x] 6.2 Write property test for watchlist row rendering with missing data
    - **Property 5: Watchlist row rendering with missing data**
    - **Validates: Requirements 4.1, 4.6**
    - Use custom `st.builds(WatchlistRow)` with optional None fields
    - Assert all None fields render as `"-"`

  - [x] 6.3 Write property test for watchlist row ordering preservation
    - **Property 6: Watchlist row ordering preservation**
    - **Validates: Requirements 4.7**
    - Use `st.lists(st.builds(WatchlistRow))` to generate row sequences
    - Assert displayed order matches input list order

  - [x] 6.4 Write property test for repository failure data retention
    - **Property 16: Repository failure data retention**
    - **Validates: Requirements 11.5**
    - Use `st.lists(st.booleans(), min_size=4, max_size=4)` for failure combinations
    - Assert previously displayed data retained for affected columns

- [x] 7. Implement Token Input frame
  - [x] 7.1 Create `TokenInputFrame` in `dex_agent/gui/frames/token_input.py`
    - Provide single-line text entry (1–44 characters for Solana mint address)
    - Implement Add button: call `on_add(mint_address)` callback with entry text
    - Implement Remove button: call `on_remove()` callback
    - Implement `set_enabled(enabled: bool)` to disable buttons when agent stopped
    - Implement `clear_input()` to reset entry field
    - Reject empty/whitespace-only input on Add (no-op)
    - _Requirements: 5.1, 5.2, 5.6, 5.7, 5.8_

  - [x] 7.2 Write property test for add token workflow correctness
    - **Property 7: Add token workflow correctness**
    - **Validates: Requirements 5.2, 5.3, 5.5**
    - Use `st.text(min_size=1, max_size=44)` for valid mint addresses
    - Assert `add_token` called with exact string; input cleared on Ok, preserved on Err

  - [x] 7.3 Write property test for whitespace input rejection
    - **Property 8: Whitespace input rejection**
    - **Validates: Requirements 5.7**
    - Use `st.from_regex(r'^\s*$')` for whitespace-only strings
    - Assert `add_token` is never invoked and input text unchanged

- [x] 8. Implement Alerts Log frame
  - [x] 8.1 Create `AlertsLogFrame` in `dex_agent/gui/frames/alerts_log.py`
    - Scrollable read-only CTkTextbox for timestamped messages
    - Implement `append_alert(title: str, body: str)` with format `YYYY-MM-DD HH:MM:SS [title] body`
    - Implement `append_message(message: str)` for general messages
    - Auto-scroll to bottom unless user has scrolled up
    - Enforce MAX_ENTRIES = 10,000 (remove oldest when exceeded)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 8.2 Write property test for alert log entry formatting
    - **Property 9: Alert log entry formatting**
    - **Validates: Requirements 6.1**
    - Use `st.text()` pairs for title and body
    - Assert output matches `YYYY-MM-DD HH:MM:SS [title] body` pattern

  - [x] 8.3 Write property test for alerts log capacity management
    - **Property 10: Alerts log capacity management**
    - **Validates: Requirements 6.4, 6.6**
    - Use `st.integers(min_value=9990, max_value=10100)` for entry count sequences
    - Assert log never exceeds 10,000 entries; oldest removed first

- [x] 9. Checkpoint - Ensure all frame tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement Controls frame and Settings Dialog
  - [x] 10.1 Create `ControlsFrame` in `dex_agent/gui/frames/controls.py`
    - Start button: calls `app.start_agent()`; disabled while running or transitioning
    - Stop button: calls `app.stop_agent()`; disabled while stopped or transitioning
    - Settings button: opens `SettingsDialog`
    - Update button states based on agent running/stopped/transitioning
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.6, 8.7_

  - [x] 10.2 Create `SettingsDialog` in `dex_agent/gui/dialogs/settings.py`
    - Modal CTkToplevel that blocks main window interaction
    - Generate labeled input fields for each key in `ConfigManager.PARAM_RANGES`
    - Pre-populate fields from `config_manager.active` or `DEFAULTS`
    - Save button: coerce values to int/Decimal per `ParamRange.integer`, call `config_manager.save(inputs)`
    - Display `ConfigValidationError` or `ConfigPersistenceError` messages; retain dialog open with values preserved
    - Cancel button: close without saving
    - On success: close dialog; new config applied on next tick cycle
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8_

  - [x] 10.3 Write property test for settings dialog fields match PARAM_RANGES
    - **Property 12: Settings dialog fields match PARAM_RANGES**
    - **Validates: Requirements 10.2**
    - Exhaustive check that every key in `PARAM_RANGES` has a corresponding labeled field

  - [x] 10.4 Write property test for settings dialog pre-population
    - **Property 13: Settings dialog pre-population**
    - **Validates: Requirements 10.3**
    - Use `st.builds(Configuration)` to generate config values
    - Assert each field pre-populated with corresponding config value

  - [x] 10.5 Write property test for settings type coercion on save
    - **Property 14: Settings type coercion on save**
    - **Validates: Requirements 10.4**
    - Use `st.decimals()` / `st.integers()` for numeric inputs
    - Assert `save()` receives int for integer-typed params, Decimal for decimal-typed

  - [x] 10.6 Write property test for settings save error retention
    - **Property 15: Settings save error retention**
    - **Validates: Requirements 10.5, 10.6**
    - Use `st.builds(ConfigValidationError)` for error generation
    - Assert error displayed, dialog remains open, all field values preserved

- [x] 11. Implement main application window and wiring
  - [x] 11.1 Create `DEXMonitorApp` class in `dex_agent/gui/app.py`
    - Set `customtkinter.set_appearance_mode("dark")` and window title "DEX Monitor"
    - Set minimum window size 1100×700 pixels
    - Instantiate and layout all frames: StatusBarFrame, WatchlistTableFrame, TokenInputFrame, AlertsLogFrame, ControlsFrame
    - Instantiate `GUIChannel` and bind to AlertsLogFrame
    - Implement `start_agent()`: create AgentThread, start it, update button states
    - Implement `stop_agent()`: signal stop, wait for completion, update button states
    - Implement `on_closing()`: stop agent if running, destroy window
    - Implement `_poll_state_queue()`: poll queue every 200ms via `after()`, update UI
    - Implement `_update_ui_state(state)`: route state to StatusBar, WatchlistTable
    - Wire TokenInput callbacks: `on_add` → `agent.add_token()`, `on_remove` → `agent.remove_pair()`
    - Handle add_token Ok → clear input; Err → append error to Alerts_Log
    - Disable Token_Input buttons when agent stopped; enable when running
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 5.2, 5.3, 5.4, 5.5, 5.6, 8.1, 8.3, 8.4, 8.6, 11.3_

  - [x] 11.2 Write unit tests for application wiring and button state transitions
    - Test Start/Stop button enable/disable logic
    - Test `on_closing` triggers agent stop
    - Test initial state (zeros, empty table)
    - Test add_token error routing to Alerts_Log
    - _Requirements: 8.3, 8.4, 8.7, 5.3_

- [x] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Integration testing and CLI preservation verification
  - [x] 13.1 Write integration tests for agent thread lifecycle
    - Test full start → tick → state pushed to queue → stop lifecycle
    - Test GUIChannel delivery from background thread via `widget.after()`
    - Test settings save → config applied to next tick cycle
    - _Requirements: 9.1, 9.2, 9.4, 7.3, 10.7, 11.3_

  - [x] 13.2 Verify CLI entry point preservation
    - Run `python -m dex_agent` smoke test to confirm existing CLI still works
    - Run `pytest` to confirm zero new test failures and zero modified test files
    - Confirm no files outside `dex_agent/gui/` have been modified
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [x] 14. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (16 total)
- Unit tests validate specific examples and edge cases
- All GUI tests use mocked widgets (no display server required) for CI compatibility
- Hypothesis library (already present in project) used for property-based testing with `@settings(max_examples=100)`
- Test files live in `tests/gui/` directory

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "2.1"] },
    { "id": 2, "tasks": ["2.2", "3.1"] },
    { "id": 3, "tasks": ["3.2", "5.1", "6.1", "7.1", "8.1"] },
    { "id": 4, "tasks": ["5.2", "5.3", "6.2", "6.3", "6.4", "7.2", "7.3", "8.2", "8.3"] },
    { "id": 5, "tasks": ["10.1", "10.2"] },
    { "id": 6, "tasks": ["10.3", "10.4", "10.5", "10.6", "11.1"] },
    { "id": 7, "tasks": ["11.2", "13.1"] },
    { "id": 8, "tasks": ["13.2"] }
  ]
}
```
