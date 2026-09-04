import json

import pytest

from agentdeck import (
    FilesystemProviderCallJournal,
    MemoryProviderCallJournal,
    ProviderCallCustodyError,
    inspect_provider_call_custody,
)


def _intent(player="Claude"):
    return {
        "player": player,
        "provider": "anthropic",
        "model": "claude-test",
        "phase": "turn",
        "match_id": "match-1",
        "turn_number": 1,
        "composed_input_sha256": "a" * 64,
    }


def _request():
    return {
        "sdk": "anthropic",
        "method": "messages.create",
        "arguments": {"model": "claude-test"},
        "arguments_sha256": "b" * 64,
        "assurance": "sent_to_official_sdk",
    }


def _provider_call(call_id="call-1"):
    return {
        "schema_version": "0.1",
        "call_id": call_id,
        "player": "Claude",
        "sdk_request": _request(),
        "sdk_response": {
            "response_text": '{"action":"WAIT"}',
            "assurance": "returned_by_official_sdk",
        },
    }


def _usage():
    return {
        "tokens": 12,
        "prompt_tokens": 10,
        "completion_tokens": 2,
        "cost": 0.001,
        "provider": "anthropic",
        "call_id": "call-1",
    }


def test_memory_journal_preserves_attempt_lifecycle():
    journal = MemoryProviderCallJournal()

    journal.begin_attempt(call_id="call-1", attempt_index=1, intent=_intent())
    journal.mark_dispatch_started(call_id="call-1", attempt_index=1, sdk_request=_request())
    journal.commit_response(
        call_id="call-1",
        attempt_index=1,
        provider_call=_provider_call(),
        usage_info=_usage(),
    )

    assert journal.entries() == (
        {
            "schema_version": "0.1",
            "call_id": "call-1",
            "attempt_index": 1,
            "state": "response_committed",
            "intent": _intent(),
            "dispatch": {"sdk_request": _request()},
            "result": {
                "provider_call": _provider_call(),
                "usage_info": _usage(),
            },
        },
    )


def test_filesystem_journal_survives_new_process_view(tmp_path):
    directory = tmp_path / "provider_calls"
    writer = FilesystemProviderCallJournal(directory)
    writer.begin_attempt(call_id="call-1", attempt_index=1, intent=_intent())
    writer.mark_dispatch_started(call_id="call-1", attempt_index=1, sdk_request=_request())
    writer.commit_response(
        call_id="call-1",
        attempt_index=1,
        provider_call=_provider_call(),
        usage_info=_usage(),
    )

    reader = FilesystemProviderCallJournal(directory)

    assert reader.entries() == writer.entries()
    assert len(list(directory.glob("attempt_*.json"))) == 1


def test_dispatch_failure_is_preserved_as_unknown_provider_outcome():
    journal = MemoryProviderCallJournal()
    journal.begin_attempt(call_id="call-1", attempt_index=1, intent=_intent())
    journal.mark_dispatch_started(call_id="call-1", attempt_index=1, sdk_request=_request())
    journal.commit_error(
        call_id="call-1",
        attempt_index=1,
        error={"type": "ConnectionError", "message": "connection closed"},
    )

    entry = journal.entries()[0]
    assert entry["state"] == "attempt_failed"
    assert entry["provider_outcome"] == "unknown"


def test_invalid_transition_fails_closed():
    journal = MemoryProviderCallJournal()
    journal.begin_attempt(call_id="call-1", attempt_index=1, intent=_intent())

    with pytest.raises(ProviderCallCustodyError, match="expected custody state"):
        journal.commit_response(
            call_id="call-1",
            attempt_index=1,
            provider_call=_provider_call(),
            usage_info=_usage(),
        )


def test_interrupted_execution_inspection_recovers_known_usage(tmp_path):
    directory = tmp_path / "01_run" / "session" / "provider_calls"
    journal = FilesystemProviderCallJournal(directory)
    journal.begin_attempt(call_id="call-1", attempt_index=1, intent=_intent())
    journal.mark_dispatch_started(call_id="call-1", attempt_index=1, sdk_request=_request())
    journal.commit_response(
        call_id="call-1",
        attempt_index=1,
        provider_call=_provider_call(),
        usage_info=_usage(),
    )

    custody = inspect_provider_call_custody(tmp_path)

    assert custody["response_committed"] == 1
    assert custody["outcome_unknown"] == 0
    assert custody["usage"] == {
        "cost_usd": 0.001,
        "calls": 1,
        "tokens": 12,
        "by_player": {"Claude": 0.001},
    }


def test_interrupted_execution_deduplicates_usage_already_in_record(tmp_path):
    directory = tmp_path / "01_run" / "session" / "provider_calls"
    journal = FilesystemProviderCallJournal(directory)
    journal.begin_attempt(call_id="call-1", attempt_index=1, intent=_intent())
    journal.mark_dispatch_started(call_id="call-1", attempt_index=1, sdk_request=_request())
    journal.commit_response(
        call_id="call-1",
        attempt_index=1,
        provider_call=_provider_call(),
        usage_info=_usage(),
    )
    records = tmp_path / "01_run" / "session" / "records"
    records.mkdir(parents=True)
    (records / "match_1.json").write_text(
        json.dumps(
            {
                "events": [{"data": {"provider_call": _provider_call()}}],
                "metadata": {
                    "match": {
                        "cost": 0.001,
                        "player_costs": {"Claude": 0.001},
                    }
                },
                "api_usage_summary": {"total_calls": 1, "total_tokens": 12},
            }
        ),
        encoding="utf-8",
    )

    custody = inspect_provider_call_custody(tmp_path)

    assert custody["known_unincorporated_usage"]["calls"] == 0
    assert custody["usage"]["calls"] == 1
    assert custody["usage"]["cost_usd"] == 0.001
