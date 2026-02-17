import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BRONZE_PATH = os.path.join(BASE_DIR, "data", "bronze")
SILVER_PATH = os.path.join(BASE_DIR, "data", "silver")

os.makedirs(SILVER_PATH, exist_ok=True)


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

    # Ensure Code is string
    df["Code"] = df["Code"].astype(str)

    # Keep only 4-digit codes (regions + national level)
    df = df[df["Code"].str.len() == 4].copy()

    # English classification column (D column)
    english_column = df.columns[3]  # adjust if structure differs

    # Detect year columns
    year_columns = [col for col in df.columns if col.isdigit()]

    # Keep only English column + year columns
    df_silver = df[[english_column] + year_columns].copy()

    # Rename English column to standardized name
    df_silver = df_silver.rename(columns={english_column: "Classification"})

    # Save to Silver layer
    output_path = os.path.join(SILVER_PATH, file_name)
    df_silver.to_csv(output_path, index=False)

    print(f"{file_name} → Silver completed.")


def main():
    for file in os.listdir(BRONZE_PATH):
        if file.endswith(".csv"):
            process_file(file)


if __name__ == "__main__":
    main()
