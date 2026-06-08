"""End-to-end integration tests for the wired Agent assembly (Task 19.2-19.7).

These tests drive the fully composed :class:`dex_agent.agent.Agent` through
realistic scenarios using only in-memory provider fakes and a controllable
clock - no real network, chain, signing, or secret access occurs.
"""
