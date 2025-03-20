import pytest
import os
from unittest.mock import patch, MagicMock
import google.generativeai as genai
from dotenv import load_dotenv
from esl_teacher_cli_v1_1_0_copy import ESLTeacherCLI  # Replace your_module


@pytest.fixture
def cli_instance(tmp_path):
    """Fixture to create an ESLTeacherCLI instance with a temporary database."""
    db_path = tmp_path / "test.db"
    return ESLTeacherCLI(str(db_path))


def test_setup_gemini_api_valid_key(cli_instance, monkeypatch, tmp_path):
    """Test setup_gemini_api with a valid API key."""
    monkeypatch.setenv("GOOGLE_API_KEY", "valid_key")
    assert cli_instance.setup_gemini_api() is True


def test_setup_gemini_api_missing_key(cli_instance, monkeypatch, capsys, tmp_path):
    """Test setup_gemini_api when the API key is missing."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert cli_instance.setup_gemini_api() is False
    captured = capsys.readouterr()
    assert "GOOGLE_API_KEY not found" in captured.err


def test_setup_gemini_api_invalid_key(cli_instance, monkeypatch, capsys, tmp_path):
    """Test setup_gemini_api with an invalid API key."""
    monkeypatch.setenv("GOOGLE_API_KEY", "invalid_key")
    with patch("google.generativeai.configure") as mock_configure:
        mock_configure.side_effect = ValueError("Invalid API key")
        assert cli_instance.setup_gemini_api() is False
        captured = capsys.readouterr()
        assert "Invalid API key" in captured.err


def test_setup_gemini_api_import_error(cli_instance, monkeypatch, capsys, tmp_path):
    """Test setup_gemini_api when google.generativeai is not installed."""
    monkeypatch.setenv("GOOGLE_API_KEY", "valid_key")
    with patch("google.generativeai.configure") as mock_configure:
        mock_configure.side_effect = ImportError(
            "No module named 'google.generativeai'"
        )
        assert cli_instance.setup_gemini_api() is False
        captured = capsys.readouterr()
        assert "Missing required module" in captured.err


def test_setup_gemini_api_general_error(cli_instance, monkeypatch, capsys, tmp_path):
    """Test setup_gemini_api with a general exception."""
    monkeypatch.setenv("GOOGLE_API_KEY", "valid_key")
    with patch("google.generativeai.configure") as mock_configure:
        mock_configure.side_effect = Exception("General error")
        assert cli_instance.setup_gemini_api() is False
        captured = capsys.readouterr()
        assert "Unexpected error setting up Gemini API" in captured.err


def test_get_current_context_no_selection(cli_instance):
    """Test get_current_context when no items are selected."""
    assert cli_instance.get_current_context() == "No context available."


def test_get_current_context_student_only(cli_instance):
    """Test get_current_context with only a student selected."""
    cli_instance.current_student = {"id": 1}
    with patch.object(cli_instance, "execute_query") as mock_query:
        mock_query.return_value = {
            "name": "Test Student",
            "email": "test@example.com",
            "enrollment_date": "2024-01-01",
        }
        context = cli_instance.get_current_context()
        assert "Student: Test Student" in context
        assert "Email: test@example.com" in context
        assert "Enrollment Date: 2024-01-01" in context


# Add more tests for course, unit, lesson and block context.


def test_use_gemini_assistant_setup_fails(cli_instance, monkeypatch, capsys):
    """Test use_gemini_assistant when setup_gemini_api fails."""
    monkeypatch.setattr(cli_instance, "setup_gemini_api", MagicMock(return_value=False))
    cli_instance.use_gemini_assistant()
    captured = capsys.readouterr()
    assert "Press Enter to return to main menu" in captured.out


def test_use_gemini_assistant_valid_interaction(cli_instance, monkeypatch, capsys):
    """Test a valid interaction with use_gemini_assistant."""
    monkeypatch.setattr(cli_instance, "setup_gemini_api", MagicMock(return_value=True))
    monkeypatch.setattr("builtins.input", lambda _: "exit")  # exit the loop.
    mock_chat = MagicMock()
    mock_chat.send_message.return_value.text = "Gemini response"
    with patch("google.generativeai.GenerativeModel") as mock_model:
        mock_model.return_value.start_chat.return_value = mock_chat
        cli_instance.use_gemini_assistant()
        captured = capsys.readouterr()
        assert "Gemini response" in captured.out


def test_use_gemini_assistant_general_exception(cli_instance, monkeypatch, capsys):
    """Test use_gemini_assistant when a general exception occurs."""
    monkeypatch.setattr(cli_instance, "setup_gemini_api", MagicMock(return_value=True))
    with patch("google.generativeai.GenerativeModel") as mock_model:
        mock_model.side_effect = Exception("General error")
        cli_instance.use_gemini_assistant()
        captured = capsys.readouterr()
        assert "Error using Gemini API: General error" in captured.err
