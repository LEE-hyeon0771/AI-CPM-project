"""
Tests for prompt loader functionality.
"""
import pytest
import tempfile
import os
from pathlib import Path
from backend.utils.prompt_loader import PromptLoader, get_prompt, get_system_prompt, get_query_prompt


class TestPromptLoader:
    """Test cases for PromptLoader class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.prompt_loader = PromptLoader(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_prompt_success(self):
        """Test successful prompt loading."""
        # Create a test prompt file
        prompt_content = "This is a test prompt with {variable}."
        prompt_file = Path(self.temp_dir) / "test_prompt.txt"
        
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt_content)
        
        result = self.prompt_loader.load_prompt("test_prompt")
        assert result == prompt_content
    
    def test_load_prompt_with_extension(self):
        """Test loading prompt with .txt extension."""
        prompt_content = "Test prompt content"
        prompt_file = Path(self.temp_dir) / "test_prompt.txt"
        
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt_content)
        
        result = self.prompt_loader.load_prompt("test_prompt.txt")
        assert result == prompt_content
    
    def test_load_prompt_not_found(self):
        """Test loading non-existent prompt."""
        with pytest.raises(FileNotFoundError):
            self.prompt_loader.load_prompt("nonexistent_prompt")
    
    def test_format_prompt(self):
        """Test prompt formatting with variables."""
        prompt_content = "Hello {name}, you have {count} messages."
        prompt_file = Path(self.temp_dir) / "format_test.txt"
        
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt_content)
        
        result = self.prompt_loader.format_prompt("format_test", name="Alice", count=5)
        assert result == "Hello Alice, you have 5 messages."
    
    def test_format_prompt_missing_variable(self):
        """Test prompt formatting with missing variable."""
        prompt_content = "Hello {name}, you have {count} messages."
        prompt_file = Path(self.temp_dir) / "format_test.txt"
        
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt_content)
        
        with pytest.raises(ValueError, match="Missing variable"):
            self.prompt_loader.format_prompt("format_test", name="Alice")
    
    def test_prompt_caching(self):
        """Test prompt caching functionality."""
        prompt_content = "Cached prompt content"
        prompt_file = Path(self.temp_dir) / "cache_test.txt"
        
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt_content)
        
        # Load prompt first time
        result1 = self.prompt_loader.load_prompt("cache_test")
        assert result1 == prompt_content
        
        # Modify file content
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write("Modified content")
        
        # Load again - should return cached content
        result2 = self.prompt_loader.load_prompt("cache_test")
        assert result2 == prompt_content  # Should be cached
        
        # Force reload
        result3 = self.prompt_loader.reload_prompt("cache_test")
        assert result3 == "Modified content"
    
    def test_clear_cache(self):
        """Test cache clearing."""
        prompt_content = "Cache test content"
        prompt_file = Path(self.temp_dir) / "cache_test.txt"
        
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt_content)
        
        # Load and cache
        self.prompt_loader.load_prompt("cache_test")
        assert "cache_test.txt" in self.prompt_loader._prompt_cache
        
        # Clear cache
        self.prompt_loader.clear_cache()
        assert len(self.prompt_loader._prompt_cache) == 0
    
    def test_get_available_prompts(self):
        """Test getting available prompts."""
        # Create multiple prompt files
        prompts = ["prompt1.txt", "prompt2.txt", "prompt3.txt"]
        for prompt in prompts:
            prompt_file = Path(self.temp_dir) / prompt
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(f"Content for {prompt}")
        
        available = self.prompt_loader.get_available_prompts()
        assert len(available) == 3
        assert "prompt1" in available
        assert "prompt2" in available
        assert "prompt3" in available
    
    def test_get_available_prompts_empty_dir(self):
        """Test getting available prompts from empty directory."""
        available = self.prompt_loader.get_available_prompts()
        assert available == []
    
    def test_get_available_prompts_nonexistent_dir(self):
        """Test getting available prompts from nonexistent directory."""
        nonexistent_loader = PromptLoader("nonexistent_directory")
        available = nonexistent_loader.get_available_prompts()
        assert available == []


class TestPromptConvenienceFunctions:
    """Test cases for convenience functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test prompts
        prompts_dir = Path(self.temp_dir)
        prompts_dir.mkdir(exist_ok=True)
        
        # System prompt
        system_prompt = "You are a helpful assistant."
        with open(prompts_dir / "test_agent_system.txt", 'w', encoding='utf-8') as f:
            f.write(system_prompt)
        
        # Query prompt
        query_prompt = "Please analyze: {query}"
        with open(prompts_dir / "test_agent_query.txt", 'w', encoding='utf-8') as f:
            f.write(query_prompt)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_prompt_without_variables(self):
        """Test get_prompt without variables."""
        # Temporarily modify the global prompt loader
        from backend.utils import prompt_loader
        original_dir = prompt_loader.prompts_dir
        prompt_loader.prompts_dir = Path(self.temp_dir)
        
        try:
            result = get_prompt("test_agent_system")
            assert result == "You are a helpful assistant."
        finally:
            prompt_loader.prompts_dir = original_dir
    
    def test_get_prompt_with_variables(self):
        """Test get_prompt with variables."""
        from backend.utils import prompt_loader
        original_dir = prompt_loader.prompts_dir
        prompt_loader.prompts_dir = Path(self.temp_dir)
        
        try:
            result = get_prompt("test_agent_query", query="test analysis")
            assert result == "Please analyze: test analysis"
        finally:
            prompt_loader.prompts_dir = original_dir
    
    def test_get_system_prompt(self):
        """Test get_system_prompt function."""
        from backend.utils import prompt_loader
        original_dir = prompt_loader.prompts_dir
        prompt_loader.prompts_dir = Path(self.temp_dir)
        
        try:
            result = get_system_prompt("test_agent")
            assert result == "You are a helpful assistant."
        finally:
            prompt_loader.prompts_dir = original_dir
    
    def test_get_query_prompt(self):
        """Test get_query_prompt function."""
        from backend.utils import prompt_loader
        original_dir = prompt_loader.prompts_dir
        prompt_loader.prompts_dir = Path(self.temp_dir)
        
        try:
            result = get_query_prompt("test_agent", query="test query")
            assert result == "Please analyze: test query"
        finally:
            prompt_loader.prompts_dir = original_dir
