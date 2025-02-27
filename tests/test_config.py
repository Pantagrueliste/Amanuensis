"""
Tests for the Config module.
"""
import os
import pytest
import tempfile
from pathlib import Path

from modules.config import Config


class TestConfig:
    """Test suite for the Config module."""
    
    def test_init_with_default_path(self, monkeypatch):
        """Test initializing config with default path."""
        # Mock the _read_config method to avoid actual file reading
        monkeypatch.setattr(Config, "_read_config", lambda self: {
            "settings": {"logging_level": "INFO"},
            "data": {
                "machine_solution_path": "data/machine_solution.json",
                "unresolved_aw_path": "data/unresolved_aw.json"
            }
        })
        
        config = Config()
        assert config.file_path == "config.toml"
        assert config.debug_level == "INFO"
    
    def test_init_with_custom_path(self, monkeypatch):
        """Test initializing config with custom path."""
        # Mock the _read_config method to avoid actual file reading
        monkeypatch.setattr(Config, "_read_config", lambda self: {
            "settings": {"logging_level": "DEBUG"},
            "data": {
                "machine_solution_path": "data/machine_solution.json",
                "unresolved_aw_path": "data/unresolved_aw.json"
            }
        })
        
        config = Config("custom_config.toml")
        assert config.file_path == "custom_config.toml"
        assert config.debug_level == "DEBUG"
    
    def test_read_config_success(self):
        """Test reading a valid config file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".toml") as temp_file:
            temp_file.write("""
[settings]
logging_level = "INFO"

[data]
machine_solution_path = "data/machine_solution.json"
unresolved_aw_path = "data/unresolved_aw.json"
            """)
        
        try:
            config = Config(temp_file.name)
            assert config.settings["settings"]["logging_level"] == "INFO"
            assert config.settings["data"]["machine_solution_path"] == "data/machine_solution.json"
        finally:
            os.unlink(temp_file.name)
    
    def test_read_config_file_not_found(self):
        """Test handling of non-existent config file."""
        with pytest.raises(FileNotFoundError):
            Config("nonexistent_config.toml")
    
    def test_read_config_invalid_format(self):
        """Test handling of invalid TOML format."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".toml") as temp_file:
            temp_file.write("""
[settings
logging_level = "INFO"  # Missing closing bracket
            """)
        
        try:
            with pytest.raises(Exception):
                Config(temp_file.name)
        finally:
            os.unlink(temp_file.name)
    
    def test_get_existing_key(self, monkeypatch):
        """Test getting existing configuration keys."""
        # Mock the _read_config method
        monkeypatch.setattr(Config, "_read_config", lambda self: {
            "settings": {"logging_level": "INFO", "context_size": 20},
            "data": {"machine_solution_path": "data/machine_solution.json"},
            "paths": {"input_path": "/input", "output_path": "/output"}
        })
        
        config = Config()
        
        # Test getting a key
        assert config.get("settings", "logging_level") == "INFO"
        assert config.get("data", "machine_solution_path") == "data/machine_solution.json"
        
        # Test getting a section
        settings = config.get("settings")
        assert settings["logging_level"] == "INFO"
        assert settings["context_size"] == 20
    
    def test_get_with_default(self, monkeypatch):
        """Test getting keys with default values."""
        # Mock the _read_config method
        monkeypatch.setattr(Config, "_read_config", lambda self: {
            "settings": {"logging_level": "INFO"},
        })
        
        config = Config()
        
        # Test getting non-existent key with default
        assert config.get("settings", "nonexistent", "default_value") == "default_value"
        assert config.get("nonexistent_section", "nonexistent", "default_value") == "default_value"
    
    def test_get_missing_key(self, monkeypatch):
        """Test handling of missing keys."""
        # Mock the _read_config method
        monkeypatch.setattr(Config, "_read_config", lambda self: {
            "settings": {"logging_level": "INFO"},
        })
        
        config = Config()
        
        # Test missing key without default
        with pytest.raises(KeyError):
            config.get("settings", "nonexistent")
        
        # Test missing section without default
        with pytest.raises(KeyError):
            config.get("nonexistent_section")
    
    def test_print_config_recap(self, monkeypatch, capsys):
        """Test the configuration recap printing."""
        # Mock the _read_config method
        monkeypatch.setattr(Config, "_read_config", lambda self: {
            "settings": {"logging_level": "INFO", "context_size": 20},
            "unicode_replacements": {
                "replacements_on": True,
                "characters_to_delete": ["a", "b", "c"],
                "characters_to_replace": {"x": "y", "z": "w"}
            },
            "OpenAI_integration": {"gpt_suggestions": True}
        })
        
        config = Config()
        config.print_config_recap()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "Current Settings:" in output
        assert "Unicode Replacement: Enabled" in output
        assert "Characters Defined for Deletion: 3" in output
        assert "Characters Defined for Replacement: 2" in output
        assert "GPT Suggestions: Activated" in output
        assert "Context Size: 20" in output
    
    def test_validate_paths_success(self, monkeypatch, tmp_path):
        """Test successful path validation."""
        # Create test directories
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        # Create test files
        machine_solution_path = data_dir / "machine_solution.json"
        machine_solution_path.write_text("{}")
        user_solution_path = data_dir / "user_solution.json"
        user_solution_path.write_text("{}")
        
        # Mock the _read_config method
        monkeypatch.setattr(Config, "_read_config", lambda self: {
            "paths": {
                "input_path": str(input_dir),
                "output_path": str(tmp_path / "output")
            },
            "data": {
                "machine_solution_path": str(machine_solution_path),
                "user_solution_path": str(user_solution_path)
            }
        })
        
        config = Config()
        
        # Should not raise any exceptions
        config.validate_paths()
        
        # Check if output directory was created
        assert os.path.exists(tmp_path / "output")
    
    def test_validate_paths_failure(self, monkeypatch, tmp_path):
        """Test path validation with missing paths."""
        # Mock the _read_config method
        monkeypatch.setattr(Config, "_read_config", lambda self: {
            "paths": {
                "input_path": str(tmp_path / "nonexistent_input"),
                "output_path": str(tmp_path / "output")
            },
            "data": {
                "machine_solution_path": str(tmp_path / "nonexistent_machine_solution.json"),
                "user_solution_path": str(tmp_path / "nonexistent_user_solution.json")
            }
        })
        
        config = Config()
        
        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            config.validate_paths()
    
    def test_get_ambiguous_aws(self, monkeypatch):
        """Test getting ambiguous abbreviations."""
        # Test with ambiguous_aws defined
        monkeypatch.setattr(Config, "_read_config", lambda self: {
            "settings": {"logging_level": "INFO"},
            "ambiguity": {"ambiguous_aws": ["yt", "ye", "wt"]}
        })
        
        config = Config()
        assert config.get_ambiguous_aws() == ["yt", "ye", "wt"]
        
        # Test with ambiguous_aws not defined
        monkeypatch.setattr(Config, "_read_config", lambda self: {
            "settings": {"logging_level": "INFO"}
        })
        
        config = Config()
        assert config.get_ambiguous_aws() == []
    
    def test_get_openai_integration(self, monkeypatch):
        """Test getting OpenAI integration settings."""
        # Test with OpenAI integration defined
        monkeypatch.setattr(Config, "_read_config", lambda self: {
            "settings": {"logging_level": "INFO"},
            "OpenAI_integration": {
                "api_key": "test_key",
                "model": "gpt-4",
                "temperature": 0.7
            }
        })
        
        config = Config()
        assert config.get_openai_integration("api_key") == "test_key"
        assert config.get_openai_integration("model") == "gpt-4"
        assert config.get_openai_integration("temperature") == 0.7
        assert config.get_openai_integration("nonexistent") is None
        
        # Test with OpenAI integration not defined
        monkeypatch.setattr(Config, "_read_config", lambda self: {
            "settings": {"logging_level": "INFO"}
        })
        
        config = Config()
        assert config.get_openai_integration("api_key") is None