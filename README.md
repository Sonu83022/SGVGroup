# EPF–ESIC ECR Highlighter

A Streamlit app that accepts:
- EPF or ESIC ECR PDF
- Employee list in Excel (.xlsx/.xls) or CSV

It highlights PDF text lines containing values from the selected Excel column and exports a highlighted PDF.

## Run on your computer
1. Install Python 3.10 or newer.
2. Extract this ZIP.
3. Open Command Prompt in the extracted folder and run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app opens in your browser, usually at http://localhost:8501.

## Publish as a shareable website
1. Create a GitHub repository and upload `app.py` and `requirements.txt`.
2. Open https://share.streamlit.io/ and sign in.
3. Choose the repository, branch, and `app.py` as the main file.
4. Deploy. Streamlit will provide a shareable URL.

## Employee-data privacy
ECRs contain sensitive personal/payroll information. Keep the repository public only if it contains code alone—never upload employee files. For real employee data, use an access-controlled/private deployment and follow your organization's data-protection rules.

## Limitations
- The PDF needs selectable text. Scanned/image-only PDFs need OCR first.
- Matching is based on the selected Excel column values being present in the PDF text.
- The app highlights the text line where a match occurs; review output for table layouts and wrapped rows.
- It does not alter the ECR or check statutory calculations.
