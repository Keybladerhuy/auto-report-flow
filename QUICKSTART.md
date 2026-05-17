# Quickstart

## Prerequisites

```bash
pip install -r requirements.txt
```

Make sure `data/online_retail_II.xlsx` is present (it's committed to the repo, so a fresh clone has it).

Optionally, copy `.env.example` to `.env` and fill in credentials to enable email delivery and Google Sheets data loading.

## Run the full pipeline

```bash
# Step 1 — clean data and generate all charts (notebooks 01 → 04)
./scripts/run_pipeline.sh

# Step 2 — assemble the PDF reports (English + Japanese)
.venv/bin/python generate_report.py

# Step 3 — deliver the reports (email via SendGrid; extend for Slack, Teams, S3, etc.)
.venv/bin/python deliver_report.py
```

Two PDFs are saved to `output/`: `report_sample_en.pdf` and `report_sample_ja.pdf`.  
This full pipeline runs automatically every Monday 08:00 JST via GitHub Actions.

## Using a client's data

- **Excel:** replace `data/online_retail_II.xlsx` with the client's file (same column schema)
- **Google Sheets:** set `GOOGLE_SHEETS_KEY_PATH` and `GOOGLE_SHEETS_TEMPLATE_ID` in `.env`

Then run the three commands above.
