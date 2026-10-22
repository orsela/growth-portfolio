import pytest
from cloud_agents import safe_gemini_parse

def test_safe_gemini_parse_valid_json():
    text = '{"key": "value"}'
    assert safe_gemini_parse(text) == {"key": "value"}

def test_safe_gemini_parse_markdown_json():
    text = '```json\n{"key": "value"}\n```'
    assert safe_gemini_parse(text) == {"key": "value"}

def test_safe_gemini_parse_markdown_generic():
    text = '```\n{"key": "value"}\n```'
    assert safe_gemini_parse(text) == {"key": "value"}

def test_safe_gemini_parse_with_surrounding_text():
    text = 'Here is the JSON:\n```json\n{"key": "value"}\n```\nEnjoy!'
    assert safe_gemini_parse(text) == {"key": "value"}

def test_safe_gemini_parse_invalid_json():
    text = '{"key": "value"'
    assert safe_gemini_parse(text) is None

def test_safe_gemini_parse_empty_string():
    assert safe_gemini_parse('') is None

def test_safe_gemini_parse_no_braces():
    assert safe_gemini_parse('just some text') is None
