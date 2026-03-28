import pandas as pd
import os

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data'))

# --- Borough Normalization ---
# The Violations & Registrations CSVs use abbreviated borough codes (e.g., 'MN', 'BK').
# The Bedbug & Complaints CSVs use full names (e.g., 'MANHATTAN', 'BROOKLYN').
# We normalize the user input to both forms for matching.
BOROUGH_ABBR_MAP = {
    "MANHATTAN": "MN",
    "BROOKLYN":  "BK",
    "QUEENS":    "QN",
    "BRONX":     "BX",
    "STATEN ISLAND": "SI",
}

print("Loading datasets into memory for fast lookup...")
try:
    violations_df  = pd.read_csv(os.path.join(DATA_DIR, 'violations.csv'),  dtype=str, low_memory=False)
    bedbug_df      = pd.read_csv(os.path.join(DATA_DIR, 'bedbug.csv'),      dtype=str, low_memory=False)
    complaints_df  = pd.read_csv(os.path.join(DATA_DIR, 'complaints.csv'),  dtype=str, low_memory=False)
    print(f"  [OK] violations:  {len(violations_df):,} rows")
    print(f"  [OK] bedbugs:     {len(bedbug_df):,} rows")
    print(f"  [OK] complaints:  {len(complaints_df):,} rows")
except Exception as e:
    print(f"Warning: Data files not accessible — {e}")
    violations_df  = pd.DataFrame()
    bedbug_df      = pd.DataFrame()
    complaints_df  = pd.DataFrame()


def lookup_address(housenumber: str, streetname: str, borough: str) -> dict:
    """
    Looks up building data for a normalized address across all datasets.
    Returns violations, bedbug reports, and complaint counts.
    """
    hn   = str(housenumber).upper().strip()
    sn   = str(streetname).upper().strip()
    boro_full  = str(borough).upper().strip()                          # e.g. "BROOKLYN"
    boro_abbr  = BOROUGH_ABBR_MAP.get(boro_full, boro_full[:2])       # e.g. "BK"

    v_list  = []
    b_list  = []
    c_list  = []

    # --- Violations (uses: housenumber, streetname, boro) ---
    if not violations_df.empty:
        v_matches = violations_df[
            (violations_df['housenumber'].astype(str).str.upper() == hn) &
            (violations_df['streetname'].astype(str).str.upper().str.contains(sn, na=False)) &
            (violations_df['boro'].astype(str).str.upper() == boro_full)
        ]
        if not v_matches.empty:
            cols = [c for c in ['class', 'novdescription', 'inspectiondate', 'currentstatus'] if c in v_matches.columns]
            v_list = v_matches[cols].dropna(subset=['class']).to_dict('records')

    # --- Bedbugs (uses: house_number, street_name, borough — full name) ---
    if not bedbug_df.empty:
        b_matches = bedbug_df[
            (bedbug_df['house_number'].astype(str).str.upper() == hn) &
            (bedbug_df['street_name'].astype(str).str.upper().str.contains(sn, na=False)) &
            (bedbug_df['borough'].astype(str).str.upper() == boro_full)
        ]
        if not b_matches.empty:
            cols = [c for c in ['filing_date', 'infested_dwelling_unit_count', 'of_dwelling_units'] if c in b_matches.columns]
            b_list = b_matches[cols].dropna(subset=['filing_date']).to_dict('records')

    # --- Complaints (uses: house_number, street_name, borough — full name) ---
    if not complaints_df.empty:
        c_matches = complaints_df[
            (complaints_df['house_number'].astype(str).str.upper() == hn) &
            (complaints_df['street_name'].astype(str).str.upper().str.contains(sn, na=False)) &
            (complaints_df['borough'].astype(str).str.upper() == boro_full)
        ]
        if not c_matches.empty:
            cols = [c for c in ['major_category', 'minor_category', 'complaint_status', 'received_date'] if c in c_matches.columns]
            c_list = c_matches[cols].dropna(subset=['major_category']).to_dict('records')

    return {
        "violations":     v_list,
        "bedbug_reports": b_list,
        "complaints":     c_list,
    }
