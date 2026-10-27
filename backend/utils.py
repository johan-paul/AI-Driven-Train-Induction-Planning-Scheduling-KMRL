# backend/utils.py
from datetime import datetime
import pandas as pd
import io

def csv_to_rows(file_bytes):
    s = io.BytesIO(file_bytes)
    df = pd.read_csv(s)
    rows = df.to_dict(orient='records')
    return rows
