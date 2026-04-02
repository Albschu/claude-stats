import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from claude_stats import extract_project_name

HOME = Path("/home/albert")

def test_github_project():
    full, short = extract_project_name("-home-albert-GitHub-noxtcore", HOME)
    assert short == "noxtcore"
    assert full == "GitHub/noxtcore"

def test_nested_project():
    full, short = extract_project_name("-home-albert-GitHub-bauteilversagen", HOME)
    assert short == "bauteilversagen"
    assert full == "GitHub/bauteilversagen"

def test_home_dir_only():
    full, short = extract_project_name("-home-albert", HOME)
    assert short == ""
    assert full == ""

def test_deeply_nested():
    full, short = extract_project_name("-home-albert-GitHub-bauteilversagen-sub", HOME)
    assert short == "sub"
    assert full == "GitHub/bauteilversagen/sub"
