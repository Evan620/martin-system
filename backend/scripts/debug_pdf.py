
import sys
import os
from pathlib import Path
try:
    import PyPDF2
    print(f"PyPDF2 Version: {PyPDF2.__version__}")
except ImportError:
    print("PyPDF2 not installed")

file_path = "backend/uploads/20251227234529_262_2025_wmsc_26.02.2025_ok.pdf"

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    sys.exit(1)

print(f"Testing file: {file_path}")
print(f"File size: {os.path.getsize(file_path)} bytes")

try:
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        print(f"Number of pages: {len(reader.pages)}")
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            print(f"Page {i+1} extraction success. Length: {len(text) if text else 0}")
    print("SUCCESS: PDF seems valid.")
except Exception as e:
    print(f"FAILURE: {e}")
