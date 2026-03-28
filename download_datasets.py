import urllib.request
import os

os.makedirs('data', exist_ok=True)

print("Downloading datasets (capped at 50,000 rows each to keep it fast)...")

# We use the SODA API .csv endpoint combined with $limit to pull a quick slice without timing out.
datasets = {
    'data/violations.csv': 'https://data.cityofnewyork.us/resource/wvxf-dwi5.csv?$limit=50000',
    'data/complaints.csv': 'https://data.cityofnewyork.us/resource/ygpa-z7cr.csv?$limit=50000',
    'data/bedbug.csv': 'https://data.cityofnewyork.us/resource/wz6d-d3jb.csv?$limit=50000',
    'data/registrations.csv': 'https://data.cityofnewyork.us/resource/tesw-yqqr.csv?$limit=50000'
}

for file_path, url in datasets.items():
    print(f"Fetching {file_path}...")
    try:
        urllib.request.urlretrieve(url, file_path)
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        print(f"✓ Downloaded {file_path} ({size_mb:.2f} MB)")
    except Exception as e:
        print(f"✗ Error downloading {file_path}: {e}")

print("\nAll requested datasets for the MVP are ready in the 'data' folder.")
