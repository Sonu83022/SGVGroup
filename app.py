if found:
    for key in found:
        search_pattern = (
            r"(?<!\d)" +
            r"[\s./-]*".join(re.escape(ch) for ch in key) +
            r"(?!\d)"
        )

        for match in re.finditer(search_pattern, line_text):
            matched_text = match.group(0).strip()

            if not matched_text:
                continue

            # Find the exact identifier in the PDF line
            rects = page.search_for(matched_text)

            for identifier_rect in rects:
                annot = page.add_highlight_annot(identifier_rect)
                annot.set_colors(stroke=(1, 0.85, 0.1))
                annot.update()

    highlighted_lines += 1
    matched_values.update(found)
