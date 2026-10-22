if found:
    line_highlighted = False

    # PDF line ke words aur unki positions nikalein
    words = page.get_text("words")

    line_words = [
        w for w in words
        if w[5] == block_no and w[6] == line_no
    ]

    for key in found:
        key_norm = norm(key)

        if not key_norm:
            continue

        # Pehle individual words mein exact number dhoondhein
        for word in line_words:
            word_text = word[4]
            word_norm = norm(word_text)

            if word_norm == key_norm:
                rect = fitz.Rect(word[0], word[1], word[2], word[3])
                annot = page.add_highlight_annot(rect)
                annot.set_colors(stroke=(1, 0.85, 0.1))
                annot.update()
                line_highlighted = True

    if line_highlighted:
        highlighted_lines += 1
        matched_values.update(found)
