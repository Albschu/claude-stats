from pathlib import Path


def extract_project_name(dir_name: str, home: Path) -> tuple[str, str]:
    """Convert '-home-albert-GitHub-noxtcore' -> ('GitHub/noxtcore', 'noxtcore')."""
    # Build the home prefix as it appears in the dir name: /home/albert -> -home-albert
    home_prefix = str(home).replace("/", "-")
    name = dir_name.lstrip("-")
    home_key = home_prefix.lstrip("-")
    if name.startswith(home_key):
        name = name[len(home_key):].lstrip("-")
    if not name:
        return "", ""
    full_path = name.replace("-", "/")
    short_name = name.split("-")[-1]
    return full_path, short_name
