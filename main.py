"""
Main entry point for the Teaching Assistant Grader application
"""
import sys
from src.ui import create_ui

if __name__ == "__main__":
    demo = create_ui()
    demo.launch(
        share=True,
        server_name="127.0.0.1"
    )
