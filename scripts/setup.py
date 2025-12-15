"""
Setup script for project environment
"""
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a shell command"""
    print(f"\n{'='*60}")
    print(f"📦 {description}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ {description} - Success")
        if result.stdout:
            print(result.stdout)
    else:
        print(f"❌ {description} - Failed")
        if result.stderr:
            print(result.stderr)
    
    return result.returncode == 0


def main():
    """Setup the project"""
    print("🚀 Setting up Teaching Assistant Grader")
    
    project_root = Path(__file__).parent.parent
    
    # Check Python version
    print(f"\n✅ Python version: {sys.version}")
    
    # Install requirements
    requirements_file = project_root / "requirements.txt"
    if requirements_file.exists():
        run_command(
            f"pip install -r {requirements_file}",
            "Installing Python dependencies"
        )
    
    # Check Ollama
    run_command(
        "ollama --version",
        "Checking Ollama installation"
    )
    
    # Pull default model
    run_command(
        "ollama pull llama3.1:latest",
        "Pulling default Ollama model"
    )
    
    # Create necessary directories
    for dir_name in ["data", "logs", "models"]:
        dir_path = project_root / dir_name
        dir_path.mkdir(exist_ok=True)
        print(f"✅ Created directory: {dir_name}/")
    
    print("\n" + "="*60)
    print("🎉 Setup completed!")
    print("="*60)
    print("\nNext steps:")
    print("1. Place kaggle.json in config/ (if using Kaggle tool)")
    print("2. Run: python main.py")
    print("3. Open: http://127.0.0.1:7860")


if __name__ == "__main__":
    main()
