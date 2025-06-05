import pandas as pd
import os

print("Current directory:", os.getcwd())
print("Files in directory:", os.listdir())

try:
    print("\nTrying to read Excel file...")
    df = pd.read_excel('data.xlsx')
    print("\nExcel file loaded successfully!")
    print(f"Number of rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print("\nFirst row:")
    print(df.iloc[0])
except Exception as e:
    print(f"\nError reading Excel file: {str(e)}") 