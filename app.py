
import io
import re

import fitz
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="EPF–ESIC ECR Highlighter",
    page_icon="🟨",
    layout="wide",
)

st.title("🟨 EPF–ESIC ECR Highlighter")
st.caption(
    "Upload ECR PDF and employee Excel/CSV to highlight matching employees."
)


def norm(value):
    if value is None:
        return ""
    s = str(value).strip().lower()
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return re.sub(r"[^a-z0-9]", "", s)


def read_list(uploaded):
    uploaded.seek(0)
    if uploaded.name.lower().endswith(".csv"):
        return pd.read_csv(
            uploaded, dtype=str, keep_default_na=False
        ).fillna("")
    return pd.read_excel(
        uploaded, dtype=str, keep_default_na=False
    ).fillna("")


def line_groups(page):
    words = page.get_text("words", sort=True)
    grouped = {}

    for w in words:
        key = (w[5], w[6])
        grouped.setdefault(key, []).append(w)

    for group in grouped.values():
        group.sort(key=lambda x: x[7])
        text = " ".join(w[4] for w in group)
        rect = fitz.Rect(
            min(w[0] for w in group),
            min(w[1] for w in group),
            max(w[2] for w in group),
            max(w[3] for w in group),
        )
        yield text, rect


def find_column(columns, hints):
    for hint in hints:
        for col in columns:
            if hint in str(col).strip().lower():
                return col
    return None


def get_keys(df, selected_col, search_type, name_col):
    columns = list(df.columns)

    if search_type == "Same identifier as selected Excel column":
        source_col = selected_col

    elif search_type == "Employee name":
        source_col = name_col or find_column(
            columns,
            ["employee name", "emp name", "member name", "full name"],
        )
        source_col = source_col or selected_col

    elif search_type == "UAN / Member ID":
        source_col = find_column(
            columns, ["uan", "member id", "memberid"]
        )
        source_col = source_col or selected_col

    elif search_type == "ESIC IP Number":
        source_col = find_column(
            columns,
            ["ip number", "ip no", "ipno", "insurance number"],
        )
        source_col = source_col or selected_col

    else:
        source_col = find_column(
            columns,
            ["employee code", "emp code", "employeeid", "empid"],
        )
        source_col = source_col or selected_col

    keys = set()

    for value in df[source_col].tolist():
        key = norm(value)
        if key and len(key) >= 3:
            keys.add(key)

    return keys, source_col


def numeric_identifier(key):
    return key.isdigit()


def find_matches(line, keys, search_type):
    normalized_line = norm(line)
    matches = set()

    for key in keys:
        if numeric_identifier(key) and search_type in (
            "UAN / Member ID",
            "ESIC IP Number",
        ):
            # Match a complete number, allowing spaces or separators
            # between digits in the PDF.
            pattern = r"(?<!\d)" + r"[\s./-]*".join(
                re.escape(ch) for ch in key
            ) + r"(?!\d)"

            if re.search(pattern, line):
                matches.add(key)

        elif key in normalized_line:
            matches.add(key)

    return matches


with st.sidebar:
    st.header("Settings")
    category = st.radio("ECR type", ["EPF", "ESIC"])
    st.info(
        "EPF: use UAN / Member ID. ESIC: use IP Number "
        "wherever available."
    )

pdf_file = st.file_uploader("1. Upload ECR PDF", type=["pdf"])
excel_file = st.file_uploader(
    "2. Upload employee list", type=["xlsx", "xls", "csv"]
)

if excel_file is not None:
    try:
        df = read_list(excel_file)

        if df.empty or len(df.columns) == 0:
            st.error("The employee list is empty.")
            st.stop()

        st.success(
            f"Excel loaded: {len(df)} rows, {len(df.columns)} columns."
        )
        st.dataframe(df.head(8), use_container_width=True)

        columns = list(df.columns)

        default_col = find_column(
            columns,
            ["uan", "ip number", "insurance number", "member id",
             "employee code", "emp code", "employee name", "name"],
        )

        if default_col is None:
            default_col = columns[0]

        selected_col = st.selectbox(
            "3. Select employee identifier column",
            columns,
            index=columns.index(default_col),
        )

        name_col = find_column(
            columns,
            ["employee name", "emp name", "member name", "full name"],
        )

        search_type = st.selectbox(
            "4. Identifier to search in PDF",
            [
                "Same identifier as selected Excel column",
                "UAN / Member ID",
                "ESIC IP Number",
                "Employee Code",
                "Employee name",
            ],
            index=(
                1 if category == "EPF" else 2
            ),
        )

        keys, actual_col = get_keys(
            df, selected_col, search_type, name_col
        )

        st.caption(f"Excel column used: {actual_col}")
        st.caption(f"Unique identifiers to search: {len(keys)}")

        if not keys:
            st.warning("No usable identifiers found in this column.")

        if pdf_file is not None:
            if st.button(
                "Create highlighted PDF",
                type="primary",
                use_container_width=True,
            ):
                if not keys:
                    st.error("Please select a column containing identifiers.")
                    st.stop()

                try:
                    doc = fitz.open(
                        stream=pdf_file.getvalue(),
                        filetype="pdf",
                    )

                    total_lines = 0
                    highlighted_lines = 0
                    pages_with_text = 0
                    matched_values = set()
                    pages_highlighted = set()

                    progress = st.progress(0)

                    for page_number, page in enumerate(doc):
                        page_lines = list(line_groups(page))

                        if page_lines:
                            pages_with_text += 1

                        for line_text, rect in page_lines:
                            total_lines += 1

                            found = find_matches(
                                line_text, keys, search_type
                            )

                            if found:
                                annot = page.add_highlight_annot(rect)
                                annot.set_colors(
                                    stroke=(1, 0.85, 0.1)
                                )
                                annot.update()

                                highlighted_lines += 1
                                matched_values.update(found)
                                pages_highlighted.add(page_number + 1)

                        progress.progress(
                            (page_number + 1) / max(len(doc), 1)
                        )

                    if pages_with_text == 0:
                        doc.close()
                        st.error(
                            "No selectable PDF text found. "
                            "This may be a scanned PDF; OCR is required."
                        )
                        st.stop()

                    output = io.BytesIO()
                    doc.save(output, garbage=4, deflate=True)
                    doc.close()

                    unmatched = sorted(keys - matched_values)

                    st.success(
                        f"Completed: {highlighted_lines} lines "
                        f"highlighted across {len(pages_highlighted)} pages."
                    )

                    st.metric("Excel identifiers", len(keys))
                    st.metric("Identifiers matched", len(matched_values))
                    st.metric("Identifiers not found", len(unmatched))

                    st.download_button(
                        "⬇️ Download highlighted PDF",
                        data=output.getvalue(),
                        file_name=f"{category.lower()}_ecr_highlighted.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True,
                    )

                    if highlighted_lines == 0:
                        st.warning(
                            "No matches found. Check the selected "
                            "Excel column and PDF identifier type."
                        )

                    with st.expander(
                        f"Unmatched Excel identifiers ({len(unmatched)})"
                    ):
                        st.dataframe(
                            pd.DataFrame({"Unmatched identifiers": unmatched}),
                            use_container_width=True,
                        )

                    with st.expander("Matching summary"):
                        st.write(
                            f"PDF pages containing selectable text: "
                            f"{pages_with_text}"
                        )
                        st.write(f"PDF lines checked: {total_lines}")
                        st.write(
                            "Pages highlighted: "
                            + (
                                ", ".join(map(str, sorted(pages_highlighted)))
                                if pages_highlighted else "None"
                            )
                        )

                except Exception as e:
                    st.error(f"Could not process PDF: {e}")

    except Exception as e:
        st.error(f"Could not read employee list: {e}")

else:
    st.info("Upload an employee Excel/CSV list to start.")

st.divider()
st.caption(
    "This tool matches identifiers in selectable PDF text. "
    "Scanned PDFs may require OCR. Review the output before use."
)
