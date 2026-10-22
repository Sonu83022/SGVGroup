import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import re
import io
from collections import Counter

st.set_page_config(page_title="EPF–ESIC ECR Highlighter", page_icon="🟨", layout="wide")

st.title("🟨 EPF–ESIC ECR Highlighter")
st.caption("Upload an ECR PDF and an Excel employee list. Matching employee rows are highlighted and exported as a new PDF.")

with st.expander("How to use", expanded=True):
    st.markdown("""
1. Select **EPF** or **ESIC**.
2. Upload the ECR PDF.
3. Upload the Excel/CSV list containing employees to highlight.
4. Select the matching column in Excel (prefer UAN for EPF and IP Number for ESIC, if present).
5. Select the corresponding identifier found in the PDF, then click **Create highlighted PDF**.

**Privacy:** Files are processed by this app session. Do not upload files you are not authorized to process. If deployed on a public host, use only an approved/private deployment for employee data.
""")

def norm(value):
    if value is None:
        return ""
    s = str(value).strip().lower()
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return re.sub(r"[^a-z0-9]", "", s)

def read_list(uploaded):
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded, dtype=str).fillna("")
    return pd.read_excel(uploaded, dtype=str).fillna("")

def line_groups(page):
    words = page.get_text("words")
    grouped = {}
    for w in words:
        # x0, y0, x1, y1, word, block_no, line_no, word_no
        key = (w[5], w[6])
        grouped.setdefault(key, []).append(w)
    for group in grouped.values():
        group.sort(key=lambda x: x[7])
        text = " ".join(w[4] for w in group)
        rect = fitz.Rect(
            min(w[0] for w in group), min(w[1] for w in group),
            max(w[2] for w in group), max(w[3] for w in group)
        )
        yield text, rect

with st.sidebar:
    st.header("Settings")
    category = st.radio("ECR type", ["EPF", "ESIC"], horizontal=True)
    st.info("EPF: UAN is usually the safest matching key. ESIC: IP Number is usually the safest matching key.")

pdf_file = st.file_uploader("1. Upload ECR PDF", type=["pdf"])
excel_file = st.file_uploader("2. Upload employee list", type=["xlsx", "xls", "csv"])

if excel_file is not None:
    try:
        df = read_list(excel_file)
        if df.empty or len(df.columns) == 0:
            st.error("The employee list appears to be empty.")
            st.stop()
        st.success(f"Employee list loaded: {len(df)} rows, {len(df.columns)} columns.")
        st.dataframe(df.head(8), use_container_width=True)
        cols = list(df.columns)
        default_index = 0
        hints = ["uan", "ip", "insurance", "employee id", "emp code", "member id", "name"]
        for hint in hints:
            found = next((i for i, c in enumerate(cols) if hint in str(c).lower()), None)
            if found is not None:
                default_index = found
                break
        match_col = st.selectbox("3. Which Excel column identifies employees to highlight?", cols, index=default_index)
        pdf_key_type = st.selectbox(
            "4. What should the app search for in the PDF?",
            ["Same identifier as selected Excel column", "Employee name", "UAN / Member ID", "ESIC IP Number", "Employee Code"]
        )
        values = [norm(x) for x in df[match_col].tolist()]
        keys = set(x for x in values if x)
        st.caption(f"Unique non-blank match values: {len(keys)}")
    except Exception as e:
        st.error(f"Could not read the employee list: {e}")
        st.stop()

    if pdf_file is not None:
        if st.button("Create highlighted PDF", type="primary", use_container_width=True):
            try:
                pdf_bytes = pdf_file.getvalue()
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                if not keys:
                    st.error("No usable values found in the selected Excel column.")
                    st.stop()
                highlighted_lines = 0
                matched_values = set()
                pages_with_text = 0
                for page in doc:
                    page_lines = list(line_groups(page))
                    if page_lines:
                        pages_with_text += 1
                    for line_text, rect in page_lines:
                        normalized_line = norm(line_text)
                        found_keys = [k for k in keys if len(k) >= 3 and k in normalized_line]
                        if found_keys:
                            annot = page.add_highlight_annot(rect)
                            annot.set_colors(stroke=(1, 0.85, 0.1))
                            annot.update()
                            highlighted_lines += 1
                            matched_values.update(found_keys)
                if pages_with_text == 0:
                    st.warning("No selectable text was found in this PDF. It may be scanned/image-only; OCR is needed before highlighting.")
                out = io.BytesIO()
                doc.save(out, garbage=4, deflate=True)
                doc.close()
                st.success(f"Finished. Highlighted {highlighted_lines} line(s); matched {len(matched_values)} unique identifier(s).")
                st.download_button(
                    "⬇️ Download highlighted PDF",
                    data=out.getvalue(),
                    file_name=f"{category.lower()}_ecr_highlighted.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
                unmatched = sorted(keys - matched_values)
                with st.expander(f"Unmatched Excel values ({len(unmatched)})"):
                    st.write("These values were not found in selectable PDF text. Check identifier type, spelling, or whether the PDF is scanned.")
                    st.dataframe(pd.DataFrame({"Unmatched values": unmatched}), use_container_width=True)
            except Exception as e:
                st.error(f"Could not process the PDF: {e}")
else:
    st.info("Upload an employee Excel/CSV list to configure matching options.")

st.divider()
st.caption("Important: This tool highlights matching text lines; it does not validate EPF/ESIC calculations or file correctness. Always review the generated PDF before sharing.")
