"""Add Strict and FreeText prompt modes to the existing expanded dataset.

Reads the expanded dataset, duplicates all Naive-mode rows with Strict and
FreeText prompt modes, and saves to a new file.
"""

import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_XLSX = PROJECT_ROOT / "rachel_data" / "benchassist_audit_dataset_expanded.xlsx"
OUTPUT_XLSX = PROJECT_ROOT / "rachel_data" / "benchassist_audit_dataset_4modes.xlsx"


def main():
    print(f"Reading {INPUT_XLSX}...")
    df = pd.read_excel(INPUT_XLSX, sheet_name="Audit Dataset", header=2)
    print(f"  {len(df)} rows, modes: {sorted(df['Prompt_Mode'].unique())}")

    # Get all Naive rows
    naive_rows = df[df["Prompt_Mode"] == "Naive"].copy()
    print(f"  {len(naive_rows)} Naive rows to duplicate")

    new_rows = []
    record_counter = len(df) + 1000  # offset to avoid ID collisions

    for mode in ["Strict", "FreeText"]:
        for _, row in naive_rows.iterrows():
            record_counter += 1
            new_row = row.to_dict()
            new_row["Record_ID"] = f"REC-{mode[0]}-{record_counter:04d}"
            new_row["Prompt_Mode"] = mode
            new_rows.append(new_row)
        print(f"  Added {len(naive_rows)} {mode} rows")

    # Combine
    new_df = pd.DataFrame(new_rows)
    expanded = pd.concat([df, new_df], ignore_index=True)
    print(f"\nTotal: {len(expanded)} rows")
    print(f"Modes: {sorted(expanded['Prompt_Mode'].unique())}")
    print(f"Base cases: {expanded['Base_Case_ID'].nunique()}")
    print(f"Profiles: {sorted(expanded['Counterfactual_Condition'].unique())}")

    # Write
    with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as writer:
        expanded.to_excel(writer, index=False, sheet_name="Audit Dataset", startrow=2)
        ws = writer.sheets["Audit Dataset"]
        ws.cell(row=1, column=1, value="BenchAssist IL Audit — 4-Mode Dataset")
        ws.cell(row=2, column=1, value="Naive + Masked + Strict + FreeText prompt modes")

    print(f"\nSaved to: {OUTPUT_XLSX}")


if __name__ == "__main__":
    main()
