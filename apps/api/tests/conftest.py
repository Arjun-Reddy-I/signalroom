import sys
from pathlib import Path

# Add apps/api to Python path for pytest imports
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))
