"""Search for Kortix/Suna components in the component index.

This script uses the build_component_index function to scan all components
dynamically and search for 'kortix' or 'suna' references.
"""

import sys
from pathlib import Path

# Add scripts directory to path so we can import build_component_index
scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from build_component_index import build_component_index


def find_key(obj, key, path=""):
    """Recursively search for keys/values containing the search term."""
    results = []
    
    if isinstance(obj, dict):
        for k, v in obj.items():
            if key in k.lower():
                results.append(f"Found key '{k}' at {path}")
            if isinstance(v, (dict, list)):
                results.extend(find_key(v, key, f"{path}.{k}"))
            elif isinstance(v, str) and key in v.lower():
                results.append(f"Found value '{v}' at {path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, (dict, list)):
                results.extend(find_key(v, key, f"{path}[{i}]"))
            elif isinstance(v, str) and key in v.lower():
                results.append(f"Found value '{v}' at {path}[{i}]")
    
    return results


def main():
    """Build component index and search for kortix/suna references."""
    print("Building component index dynamically...")
    
    try:
        index = build_component_index()
        
        if not index:
            print("Failed to build component index", file=sys.stderr)
            sys.exit(1)
        
        print(f"\nIndex built successfully:")
        print(f"  Version: {index.get('version', 'unknown')}")
        print(f"  Components: {index.get('metadata', {}).get('num_components', 0)}")
        print(f"  Modules: {index.get('metadata', {}).get('num_modules', 0)}")
        
        print("\n" + "=" * 60)
        print("Searching for 'kortix'...")
        print("=" * 60)
        kortix_results = find_key(index, 'kortix')
        if kortix_results:
            for result in kortix_results:
                print(f"  {result}")
        else:
            print("  No 'kortix' references found.")
        
        print("\n" + "=" * 60)
        print("Searching for 'suna'...")
        print("=" * 60)
        suna_results = find_key(index, 'suna')
        if suna_results:
            for result in suna_results:
                print(f"  {result}")
        else:
            print("  No 'suna' references found.")
        
        print("\n" + "=" * 60)
        print(f"Summary: {len(kortix_results)} kortix + {len(suna_results)} suna references")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
