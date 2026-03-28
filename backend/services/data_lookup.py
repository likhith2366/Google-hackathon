import pandas as pd
import os

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data'))

print("Loading datasets into memory for fast lookup...")
try:
    violations_df = pd.read_csv(os.path.join(DATA_DIR, 'violations.csv'), dtype=str)
    bedbug_df = pd.read_csv(os.path.join(DATA_DIR, 'bedbug.csv'), dtype=str)
except Exception as e:
    print(f"Warning: Data files not accessible. {e}")
    violations_df = pd.DataFrame()
    bedbug_df = pd.DataFrame()

def lookup_address(housenumber: str, streetname: str, borough: str):
    """
    Looks up building data for a normalized address.
    """
    hn = str(housenumber).upper().strip()
    sn = str(streetname).upper().strip()
    boro = str(borough).upper().strip()
    
    v_list = []
    b_list = []

    if not violations_df.empty:
        # Match using string containment for street name to handle slight variations
        v_matches = violations_df[
            (violations_df['housenumber'].astype(str).str.upper() == hn) & 
            (violations_df['streetname'].astype(str).str.upper().str.contains(sn, na=False)) &
            (violations_df['borough'].astype(str).str.upper() == boro)
        ]
        if not v_matches.empty and 'class' in v_matches.columns:
            v_records = v_matches[['class', 'novdescription', 'inspectiondate']].dropna()
            v_list = v_records.to_dict('records')
            
    if not bedbug_df.empty:
        b_matches = bedbug_df[
            (bedbug_df['house_number'].astype(str).str.upper() == hn) & 
            (bedbug_df['street_name'].astype(str).str.upper().str.contains(sn, na=False)) &
            (bedbug_df['borough'].astype(str).str.upper() == boro)
        ]
        if not b_matches.empty and 'filing_date' in b_matches.columns:
            b_records = b_matches[['filing_date', 'infested_dwelling_unit_count']].dropna()
            b_list = b_records.to_dict('records')

    return {
        "violations": v_list,
        "bedbug_reports": b_list
    }
