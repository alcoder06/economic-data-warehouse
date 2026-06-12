import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BRONZE_PATH = os.path.join(BASE_DIR, "data", "bronze")
SILVER_PATH = os.path.join(BASE_DIR, "data", "silver")

os.makedirs(SILVER_PATH, exist_ok=True)


def find_region_column(columns):
    english_candidates = [
        col for col in columns
        if col.lower().endswith("_en") or "english" in col.lower() or "klassifikator_en" in col.lower()
    ]

    if english_candidates:
        return english_candidates[0]

    non_code_cols = [col for col in columns if col != "Code" and not str(col).strip().isdigit()]
    return non_code_cols[0] if non_code_cols else columns[1]


def process_file(file_name):
    print(f"Processing {file_name}...")

    input_path = os.path.join(BRONZE_PATH, file_name)

    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        print(f"Error reading {file_name}: {e}")
        return

    if "Code" not in df.columns:
        print(f"Skipping {file_name} (No 'Code' column)")
        return

    df["Code"] = df["Code"].astype(str)
    df = df[df["Code"].str.len() == 4].copy()

    english_column = find_region_column(df.columns)
    year_columns = [col for col in df.columns if str(col).strip().isdigit()]

    if not year_columns:
        print(f"Skipping {file_name} (No year columns found)")
        return

    df_silver = df[["Code", english_column] + year_columns].copy()
    df_silver = df_silver.rename(columns={
        "Code": "region_code",
        english_column: "region_name"
    })

    output_path = os.path.join(SILVER_PATH, file_name)
    df_silver.to_csv(output_path, index=False)

    print(f"{file_name} → Silver completed.")


def main():
    for file in os.listdir(BRONZE_PATH):
        if file.endswith(".csv"):
            process_file(file)


if __name__ == "__main__":
    main()
