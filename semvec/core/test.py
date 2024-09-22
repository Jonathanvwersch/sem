import sys
import os

print("Python version:", sys.version)
print("Python executable:", sys.executable)
print("Python path:")
for path in sys.path:
    print(path)

print("\nCurrent working directory:", os.getcwd())
print("\nContents of current directory:")
print(os.listdir())

print("\nTrying to import numpy...")
import numpy

print("Numpy version:", numpy.__version__)

print("\nTrying to import services modules individually...")
try:
    from services import chunk_parsed_code

    print("chunk_parsed_code imported successfully")
except Exception as e:
    print(f"Error importing chunk_parsed_code: {e}")

try:
    from services import FAISSRetrievalSystem

    print("FAISSRetrievalSystem imported successfully")
except Exception as e:
    print(f"Error importing FAISSRetrievalSystem: {e}")

try:
    from services import traverse_codebase_from_path

    print("traverse_codebase_from_path imported successfully")
except Exception as e:
    print(f"Error importing traverse_codebase_from_path: {e}")

print("\nAll imports attempted")
