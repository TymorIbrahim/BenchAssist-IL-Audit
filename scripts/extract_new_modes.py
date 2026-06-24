"""Extract only Strict + FreeText rows from the 4-mode dataset."""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
inp = ROOT / "rachel_data" / "benchassist_audit_dataset_4modes.xlsx"
out = ROOT / "rachel_data" / "benchassist_audit_dataset_newmodes.xlsx"

df = pd.read_excel(inp, sheet_name="Audit Dataset", header=2)
new = df[df["Prompt_Mode"].isin(["Strict", "FreeText"])].copy()
print(f"Filtered: {len(new)} rows ({sorted(new['Prompt_Mode'].unique())})")

with pd.ExcelWriter(out, engine="openpyxl") as w:
    new.to_excel(w, index=False, sheet_name="Audit Dataset", startrow=2)
    ws = w.sheets["Audit Dataset"]
    ws.cell(row=1, column=1, value="BenchAssist IL Audit — New Modes Only")
    ws.cell(row=2, column=1, value="Strict + FreeText prompt modes")

print(f"Saved {out}")
