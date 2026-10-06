"""
Environment check script.

Yeh script confirm karta hai ke:
1. Python ka version theek hai (3.10+).
2. Hum venv ke andar hain.
3. Saari zaroori libraries import ho rahi hain.
4. settings object sahi load ho raha hai.
5. data folders ban chuke hain.

Ise chalane ka tareeqa:
    python tests\\test_environment.py
"""

import sys
import platform
from pathlib import Path


def print_header(title: str) -> None:
    """Ek saaf heading print karta hai."""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_python_version() -> bool:
    """Python 3.10+ hona chahiye."""
    print_header("1. Python version check")
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    print(f"   Python: {version_str}")
    print(f"   Platform: {platform.system()} {platform.release()}")

    if version.major == 3 and version.minor >= 10:
        print("   Status: OK (3.10+)")
        return True
    print("   Status: FAIL (need Python 3.10 or higher)")
    return False


def check_venv() -> bool:
    """Venv active hai ya nahi."""
    print_header("2. Virtual environment check")
    # venv ke andar sys.prefix venv folder ko point karta hai;
    # venv ke bahar sys.prefix system Python ko point karta hai.
    is_venv = sys.prefix != sys.base_prefix
    print(f"   sys.prefix:      {sys.prefix}")
    print(f"   sys.base_prefix: {sys.base_prefix}")

    if is_venv:
        print("   Status: OK (venv active)")
        return True
    print("   Status: FAIL (venv active nahi hai)")
    print("   Fix: venv\\Scripts\\activate chalao")
    return False


def check_imports() -> bool:
    """Zaroori libraries import karne ki koshish karo."""
    print_header("3. Library imports check")

    # (import_name, friendly_name)
    libraries = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("pymupdf", "PyMuPDF (PDF extract)"),
        ("langchain", "LangChain"),
        ("langchain_community", "LangChain Community"),
        ("langchain_text_splitters", "LangChain Text Splitters"),
        ("langchain_openai", "LangChain OpenAI"),
        ("sentence_transformers", "Sentence Transformers"),
        ("faiss", "FAISS"),
        ("openai", "OpenAI SDK"),
        ("sqlalchemy", "SQLAlchemy"),
        ("dotenv", "python-dotenv"),
        ("numpy", "NumPy"),
    ]

    all_ok = True
    for import_name, friendly in libraries:
        try:
            __import__(import_name)
            print(f"   OK    {friendly}")
        except ImportError as e:
            print(f"   FAIL  {friendly}  ({e})")
            all_ok = False

    if all_ok:
        print("   Status: OK (saari libraries import ho gayin)")
    else:
        print("   Status: FAIL (kuch libraries missing hain)")
        print("   Fix: pip install -r requirements.txt")
    return all_ok


def check_settings() -> bool:
    """settings object load ho raha hai aur paths sahi hain."""
    print_header("4. Settings check")

    try:
        # Project root ko sys.path me daalo taake 'app' package mile
        project_root = Path(__file__).resolve().parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from app.core.config import settings

        print(f"   APP_NAME:        {settings.APP_NAME}")
        print(f"   APP_ENV:         {settings.APP_ENV}")
        print(f"   LOG_LEVEL:       {settings.LOG_LEVEL}")
        print(f"   UPLOAD_DIR:      {settings.UPLOAD_DIR}")
        print(f"   VECTORSTORE_DIR: {settings.VECTORSTORE_DIR}")
        print(f"   DATABASE_URL:    {settings.DATABASE_URL}")
        print(f"   CHUNK_SIZE:      {settings.CHUNK_SIZE}")
        print(f"   CHUNK_OVERLAP:   {settings.CHUNK_OVERLAP}")
        print(f"   TOP_K:           {settings.TOP_K}")
        print("   Status: OK (settings load ho gayin)")
        return True
    except Exception as e:
        print(f"   Status: FAIL ({type(e).__name__}: {e})")
        return False


def check_folders() -> bool:
    """Zaroori data folders mojood hain."""
    print_header("5. Data folders check")

    project_root = Path(__file__).resolve().parent.parent
    required = [
        project_root / "data",
        project_root / "data" / "uploads",
        project_root / "data" / "vectorstore",
    ]

    all_ok = True
    for folder in required:
        if folder.exists() and folder.is_dir():
            print(f"   OK    {folder}")
        else:
            print(f"   FAIL  {folder} (missing)")
            all_ok = False

    if all_ok:
        print("   Status: OK (saare folders mojood)")
    else:
        print("   Status: FAIL (kuch folders missing hain)")
    return all_ok


def main() -> int:
    print()
    print("############################################################")
    print("#   RAG Document QA — Environment Check                    #")
    print("############################################################")

    results = {
        "python_version": check_python_version(),
        "venv": check_venv(),
        "imports": check_imports(),
        "settings": check_settings(),
        "folders": check_folders(),
    }

    print_header("Summary")
    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"   {status:4s}  {name}")

    all_ok = all(results.values())
    print()
    if all_ok:
        print("   >>> SAB KUCH THEEK HAI. Aage barh sakte hain.")
        return 0
    print("   >>> KUCH CHECKS FAIL HUE. Upar wale FAIL messages dekho.")
    return 1


if __name__ == "__main__":
    sys.exit(main())