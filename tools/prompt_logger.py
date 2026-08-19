from typing import Optional
from tools import db_tool


def save_prompt(prompt: str) -> Optional[int]:
    
    return db_tool.log_prompt(prompt)
