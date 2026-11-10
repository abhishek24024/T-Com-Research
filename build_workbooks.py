#!/usr/bin/env python3
"""build_workbooks.py - Generate polished Excel workbooks with data validation for human coders.

Creates:
  - coder_A.xlsx, coder_B.xlsx (all 97 records from coding_sheet.csv)
  - pilot_A.xlsx, pilot_B.xlsx (16 pilot records from pilot_sample.csv)

Features:
  - Frozen header row
  - Text wrapping on all text cells
  - Clickable hyperlinks for review_url
  - Dropdown data validation for:
      relevance, narrative, content_form, direction, origin
  - All coder label cells left strictly blank.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

from config import (
    CONTENT_FORMS,
    DIRECTIONS,
    NARRATIVES,
    ORIGINS,
    RELEVANCES,
    get_processed_data_dir,
    get_raw_data_dir,
)


def create_workbook_for_df(df: pd.DataFrame, title: str) -> openpyxl.Workbook:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title

    # Setup header columns
    headers = [
        ("Record ID", "record_id", 14),
        ("Claim Text", "claim_text", 45),
        ("Publisher", "publisher_name", 20),
        ("Fact-Check URL", "review_url", 38),
        ("Relevance", "relevance", 16),
        ("Primary Narrative", "narrative", 26),
        ("Content Form", "content_form", 26),
        ("Direction", "direction", 26),
        ("Origin", "origin", 22),
        ("Coder Notes", "coder_notes", 32),
    ]

    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    for col_idx, (hdr_text, _, width) in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=hdr_text)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
        col_letter = openpyxl.utils.get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = width

    ws.row_dimensions[1].height = 28
    ws.freeze_panes = "A2"

    # Fill rows
    regular_font = Font(name="Calibri", size=10)
    link_font = Font(name="Calibri", size=10, color="0563C1", underline="single")
    left_wrap = Alignment(horizontal="left", vertical="top", wrap_text=True)
    center_align = Alignment(horizontal="center", vertical="top")

    num_rows = len(df)
    for row_idx, (_, row_data) in enumerate(df.iterrows(), start=2):
        ws.row_dimensions[row_idx].height = 42

        # Record ID
        c1 = ws.cell(row=row_idx, column=1, value=str(row_data["record_id"]))
        c1.font = regular_font
        c1.alignment = center_align
        c1.border = thin_border

        # Claim Text
        c2 = ws.cell(row=row_idx, column=2, value=str(row_data.get("claim_text", "")))
        c2.font = regular_font
        c2.alignment = left_wrap
        c2.border = thin_border

        # Publisher
        c3 = ws.cell(row=row_idx, column=3, value=str(row_data.get("publisher_name", "")))
        c3.font = regular_font
        c3.alignment = left_wrap
        c3.border = thin_border

        # Fact Check URL (clickable hyperlink)
        url = str(row_data.get("review_url", "")).strip()
        c4 = ws.cell(row=row_idx, column=4, value=url if url else "")
        if url.startswith("http"):
            c4.hyperlink = url
            c4.font = link_font
        else:
            c4.font = regular_font
        c4.alignment = left_wrap
        c4.border = thin_border

        # Blank coder cells (columns 5 to 10)
        for col_idx in range(5, 11):
            cell = ws.cell(row=row_idx, column=col_idx, value="")
            cell.font = regular_font
            cell.alignment = left_wrap
            cell.border = thin_border

    # Dropdown Data Validations
    max_row = num_rows + 1

    # 1. Relevance (Col E / 5)
    dv_rel = DataValidation(type="list", formula1=f'"{",".join(RELEVANCES)}"', allow_blank=True)
    dv_rel.error = "Invalid relevance. Choose from the dropdown list."
    dv_rel.errorTitle = "Invalid Relevance"
    ws.add_data_validation(dv_rel)
    dv_rel.add(f"E2:E{max_row}")

    # 2. Narrative (Col F / 6)
    dv_narr = DataValidation(type="list", formula1=f'"{",".join(NARRATIVES)}"', allow_blank=True)
    dv_narr.error = "Invalid narrative code. Choose from the dropdown list."
    dv_narr.errorTitle = "Invalid Narrative"
    ws.add_data_validation(dv_narr)
    dv_narr.add(f"F2:F{max_row}")

    # 3. Content Form (Col G / 7)
    dv_form = DataValidation(type="list", formula1=f'"{",".join(CONTENT_FORMS)}"', allow_blank=True)
    dv_form.error = "Invalid content form. Choose from the dropdown list."
    dv_form.errorTitle = "Invalid Content Form"
    ws.add_data_validation(dv_form)
    dv_form.add(f"G2:G{max_row}")

    # 4. Direction (Col H / 8)
    dv_dir = DataValidation(type="list", formula1=f'"{",".join(DIRECTIONS)}"', allow_blank=True)
    dv_dir.error = "Invalid direction. Choose from the dropdown list."
    dv_dir.errorTitle = "Invalid Direction"
    ws.add_data_validation(dv_dir)
    dv_dir.add(f"H2:H{max_row}")

    # 5. Origin (Col I / 9)
    dv_orig = DataValidation(type="list", formula1=f'"{",".join(ORIGINS)}"', allow_blank=True)
    dv_orig.error = "Invalid origin code. Choose from the dropdown list."
    dv_orig.errorTitle = "Invalid Origin"
    ws.add_data_validation(dv_orig)
    dv_orig.add(f"I2:I{max_row}")

    return wb


def main() -> None:
    proc_dir = get_processed_data_dir()
    raw_dir = get_raw_data_dir()
    raw_dir.mkdir(parents=True, exist_ok=True)

    sheet_path = proc_dir / "coding_sheet.csv"
    if not sheet_path.exists():
        raise FileNotFoundError(f"Missing {sheet_path}")
    full_df = pd.read_csv(sheet_path)

    pilot_path = proc_dir / "pilot_sample.csv"
    if not pilot_path.exists():
        raise FileNotFoundError(f"Missing {pilot_path}")
    pilot_df = pd.read_csv(pilot_path)

    targets = [
        ("coder_A.xlsx", full_df, "Coding Sheet - Coder A"),
        ("coder_B.xlsx", full_df, "Coding Sheet - Coder B"),
        ("pilot_A.xlsx", pilot_df, "Pilot Sample - Coder A"),
        ("pilot_B.xlsx", pilot_df, "Pilot Sample - Coder B"),
    ]

    for fname, df_data, title in targets:
        wb = create_workbook_for_df(df_data, title)
        # Save in both data/processed and data/raw for convenience
        p_path = proc_dir / fname
        r_path = raw_dir / fname
        wb.save(p_path)
        wb.save(r_path)
        print(f"Generated workbook: {r_path} ({len(df_data)} records, all label cells blank)")


if __name__ == "__main__":
    main()
