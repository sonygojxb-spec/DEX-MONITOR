"""Entry point for the DEX Monitor GUI.

Run with:  python -m dex_agent.gui

Launches the CustomTkinter desktop application. Validates required environment
variables, constructs the agent via build_production_agent(), and starts the
DEXMonitorApp window.
"""

import os

from dotenv import load_dotenv

# Load secrets from .env before anything else
load_dotenv()

import customtkinter

from dex_agent.agent import AgentSecrets, build_production_agent
from dex_agent.__main__ import HttpxClient, SolanaRpcClient, NoOpSigner

# Required environment variables for agent operation
REQUIRED_ENV_VARS = [
    "MORALIS_API_KEY",
    "SOLANA_RPC_URL",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
]


def _check_env_vars() -> list[str]:
    """Return list of required env vars that are missing or empty."""
    missing = []
    for var in REQUIRED_ENV_VARS:
        value = os.environ.get(var, "").strip()
        if not value:
            missing.append(var)
    return missing


def _show_error_window(message: str) -> None:
    """Display a minimal error window with the given message and exit on close."""
    customtkinter.set_appearance_mode("dark")
    root = customtkinter.CTk()
    root.title("DEX Monitor - Error")
    root.geometry("600x200")
    root.minsize(600, 200)

    error_label = customtkinter.CTkLabel(
        root,
        text=message,
        text_color="red",
        wraplength=550,
        justify="left",
        font=customtkinter.CTkFont(size=14),
    )
    error_label.pack(padx=20, pady=40, fill="both", expand=True)

    root.mainloop()


def main() -> None:
    """Main entry point for the GUI application."""

    # 1. Validate required environment variables
    missing = _check_env_vars()
    if missing:
        missing_str = ", ".join(missing)
        _show_error_window(
            f"Missing required environment variables: {missing_str}\n\n"
            f"Please set them in your .env file before launching the GUI."
        )
        return

    # 2. Construct the agent via build_production_agent()
    try:
        secrets = AgentSecrets(
            moralis_api_key=os.environ["MORALIS_API_KEY"].strip(),
            solana_rpc_url=os.environ["SOLANA_RPC_URL"].strip(),
            telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"].strip(),
            telegram_chat_id=os.environ["TELEGRAM_CHAT_ID"].strip(),
            goplus_api_key=os.environ.get("GOPLUS_API_KEY", "").strip() or None,
        )

        http_client = HttpxClient(timeout=30.0)
        rpc_client = SolanaRpcClient(secrets.solana_rpc_url, timeout=30.0)

        agent = build_production_agent(
            secrets=secrets,
            http_client=http_client,
            rpc_client=rpc_client,
            signer=NoOpSigner(),
            webhook_url=os.environ.get("WEBHOOK_URL", "http://localhost:8080/webhook"),
            enable_dexscreener_fallback=True,
        )
    except Exception as exc:
        # Display build error in a GUI window with the error in an alerts-log style
        _show_error_window(
            f"Failed to construct agent:\n\n{exc}"
        )
        return

    # 3. Seed the watchlist from SEED_TOKENS env var (same as CLI entry point)
    seed = os.environ.get("SEED_TOKENS", "").strip()
    if seed:
        from dex_agent.models import Network
        for mint in [m.strip() for m in seed.split(",") if m.strip()]:
            try:
                agent.add_token(mint, Network.SOLANA)
            except Exception:
                pass  # Non-fatal: log in alerts once GUI is up

    # 4. Launch the DEXMonitorApp
    # DEXMonitorApp will be implemented in task 11.1; import conditionally
    try:
        from dex_agent.gui.app import DEXMonitorApp
    except ImportError:
        # Fallback: show a placeholder window until app.py is created (task 11.1)
        customtkinter.set_appearance_mode("dark")
        root = customtkinter.CTk()
        root.title("DEX Monitor")
        root.geometry("1100x700")
        root.minsize(1100, 700)

        label = customtkinter.CTkLabel(
            root,
            text="DEX Monitor - Agent constructed successfully.\n"
                 "Full UI will be available after app.py is implemented.",
            font=customtkinter.CTkFont(size=16),
        )
        label.pack(padx=20, pady=40, fill="both", expand=True)

        root.mainloop()
        return

    app = DEXMonitorApp(agent)
    app.mainloop()


if __name__ == "__main__":
    main()
