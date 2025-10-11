"""
Prompt loader utility for loading and formatting prompts from files.
"""
import os
from typing import Dict, Any, Optional
from pathlib import Path


class PromptLoader:
    """Utility class for loading and formatting prompts from text files."""
    
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
        self._prompt_cache: Dict[str, str] = {}
    
    def load_prompt(self, filename: str) -> str:
        """
        Load a prompt from a text file.
        
        Args:
            filename: Name of the prompt file (with or without .txt extension)
            
        Returns:
            Prompt content as string
            
        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        # Add .txt extension if not present
        if not filename.endswith('.txt'):
            filename += '.txt'
        
        # Check cache first
        if filename in self._prompt_cache:
            return self._prompt_cache[filename]
        
        # Load from file
        prompt_path = self.prompts_dir / filename
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Cache the content
            self._prompt_cache[filename] = content
            return content
            
        except Exception as e:
            raise IOError(f"Error loading prompt file {prompt_path}: {e}")
    
    def format_prompt(self, filename: str, **kwargs) -> str:
        """
        Load and format a prompt with variables.
        
        Args:
            filename: Name of the prompt file
            **kwargs: Variables to substitute in the prompt
            
        Returns:
            Formatted prompt string
        """
        prompt = self.load_prompt(filename)
        
        try:
            return prompt.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing variable in prompt {filename}: {e}")
        except Exception as e:
            raise ValueError(f"Error formatting prompt {filename}: {e}")
    
    def get_available_prompts(self) -> list:
        """Get list of available prompt files."""
        if not self.prompts_dir.exists():
            return []
        
        return [f.stem for f in self.prompts_dir.glob("*.txt")]
    
    def clear_cache(self):
        """Clear the prompt cache."""
        self._prompt_cache.clear()
    
    def reload_prompt(self, filename: str) -> str:
        """
        Force reload a prompt from file (bypass cache).
        
        Args:
            filename: Name of the prompt file
            
        Returns:
            Prompt content as string
        """
        # Remove from cache if exists
        if not filename.endswith('.txt'):
            filename += '.txt'
        
        if filename in self._prompt_cache:
            del self._prompt_cache[filename]
        
        return self.load_prompt(filename)


# Global prompt loader instance
prompt_loader = PromptLoader()


def get_prompt(filename: str, **kwargs) -> str:
    """
    Convenience function to get a formatted prompt.
    
    Args:
        filename: Name of the prompt file
        **kwargs: Variables to substitute in the prompt
        
    Returns:
        Formatted prompt string
    """
    if kwargs:
        return prompt_loader.format_prompt(filename, **kwargs)
    else:
        return prompt_loader.load_prompt(filename)


def get_system_prompt(agent_name: str) -> str:
    """
    Get system prompt for a specific agent.
    
    Args:
        agent_name: Name of the agent (law_rag, threshold_builder, etc.)
        
    Returns:
        System prompt string
    """
    return get_prompt(f"{agent_name}_system")


def get_query_prompt(agent_name: str, **kwargs) -> str:
    """
    Get query prompt for a specific agent.
    
    Args:
        agent_name: Name of the agent
        **kwargs: Variables to substitute in the prompt
        
    Returns:
        Formatted query prompt string
    """
    return get_prompt(f"{agent_name}_query", **kwargs)
