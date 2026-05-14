# FinTech Report Generation Guide

This guide explains how to generate the sample dataset, clean it, and produce the fraud detection report in this workspace.

## Files involved

- `fintech_data_generator.py`
  - Generates 10,000 simulated FinTech records.
  - Output: `fintech_sample_data.csv`

- `fintech_data_cleaner.py`
  - Cleans the generated dataset.
  - Validates and corrects email, CPF, account numbers, timestamps, and more.
  - Output: `fintech_data_cleaned.csv`, `cleaning_logs.json`, `cleaning_report.txt`

- `fraud_detection_analyzer.py`
  - Analyzes the cleaned dataset for fraud and risk patterns.
  - Produces alerts and customer risk scores.
  - Output: `fraud_detection_report.txt`, `fraud_alerts.json`, `customer_risk_scores.csv`

## Prerequisites

- Python environment configured in `c:\Users\wtfce\Documents\Python`.
- `faker` installed in the environment.
- `pandas` installed in the environment.

If needed, install packages with:

```powershell
cd c:\Users\wtfce\Documents\Python
.\.venv\Scripts\python.exe -m pip install faker pandas
```

## Step-by-step process

### 1. Generate sample data

Run the generator script to create the raw dataset:

```powershell
cd c:\Users\wtfce\Documents\Python
.\.venv\Scripts\python.exe fintech_data_generator.py
```

Expected output files:

- `fintech_sample_data.csv`

### 2. Clean the dataset

Run the cleaner script to validate and fix data quality issues:

```powershell
cd c:\Users\wtfce\Documents\Python
.\.venv\Scripts\python.exe fintech_data_cleaner.py
```

Expected output files:

- `fintech_data_cleaned.csv`
- `cleaning_logs.json`
- `cleaning_report.txt`

### 3. Analyze for fraud and risk

Run the fraud detection analyzer script:

```powershell
cd c:\Users\wtfce\Documents\Python
.\.venv\Scripts\python.exe fraud_detection_analyzer.py
```

Expected output files:

- `fraud_detection_report.txt`
- `fraud_alerts.json`
- `customer_risk_scores.csv`

## Notes

- The cleaning script uses `cleaning_logs.json` to record all detected data issues.
- The fraud analysis script uses the cleaned dataset only (`fintech_data_cleaned.csv`).
- If you want to rerun from scratch, delete or overwrite the existing CSV outputs and rerun the scripts in order.

## Troubleshooting

- If the report shows an unexpectedly high mean for `amount`, that indicates outliers are still present in the dataset.
- Use the cleaned output file `fintech_data_cleaned.csv` as the input for fraud analysis.
- If any script fails with encoding errors, make sure the script files are saved with UTF-8 and the command uses `encoding='utf-8'` where files are written.

## Recommended order

1. `fintech_data_generator.py`
2. `fintech_data_cleaner.py`
3. `fraud_detection_analyzer.py`

That is the complete workflow for generating the report files in this project.
