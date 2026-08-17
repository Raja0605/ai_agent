"""
Model-response parsing.

Both bugs here were found against the live Gemini API, not in a test:

1. `gemini-3.1-pro-preview` is a thinking model. It returns its reasoning as
   extra `parts` flagged `thought`, and concatenating every part glued that
   commentary onto the JSON answer.
2. The old extractor matched greedily from the first `{` to the last `}`, so
   any trailing content produced "Extra data" and the whole evaluation fell
   back to the keyword scorer while a valid API key was configured.
"""

import pytest

from app.services.ai.base import _extract_json


def test_plain_json_object():
    assert _extract_json('{"score": 80}', "test") == {"score": 80}


def test_json_wrapped_in_a_code_fence():
    raw = 'Here is the result:\n```json\n{"score": 70}\n```'
    assert _extract_json(raw, "test") == {"score": 70}


def test_json_preceded_by_reasoning_prose():
    raw = 'Let me consider the candidate carefully.\n\n{"score": 65, "confidence": "high"}'
    assert _extract_json(raw, "test") == {"score": 65, "confidence": "high"}


def test_trailing_content_after_the_object_is_ignored():
    """The exact failure: greedy matching raised 'Extra data' here."""
    raw = '{"score": 55}\n\nHope that helps!'
    assert _extract_json(raw, "test") == {"score": 55}


def test_multiple_objects_takes_the_first_complete_one():
    raw = 'thinking: {"draft": true}\nfinal: {"score": 90}'
    assert _extract_json(raw, "test") == {"draft": True}


def test_nested_objects_are_preserved():
    raw = 'x {"score": 80, "detail": {"a": [1, 2]}} y'
    assert _extract_json(raw, "test") == {"score": 80, "detail": {"a": [1, 2]}}


def test_unparsable_response_returns_none():
    assert _extract_json("no json here at all", "test") is None
    assert _extract_json("{broken", "test") is None


@pytest.mark.parametrize("raw", ["", "   ", "[1,2,3]"])
def test_non_object_responses_return_none(raw):
    """A bare array is valid JSON but not the object shape callers expect."""
    assert _extract_json(raw, "test") is None
