"""Build a tiny valid PDF without extra libraries (for tests and the demo sample)."""


def build_simple_pdf(text: str) -> bytes:
    """Return a one-page PDF whose visible string is `text`."""
    escaped = (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", " ")
        .replace("\n", " ")
    )
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET\n".encode("latin-1", errors="replace")

    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Count 1 /Kids [3 0 R] >>\nendobj\n",
        (
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        ),
        b"4 0 obj\n<< /Length %d >>\nstream\n" % len(stream) + stream + b"endstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]

    header = b"%PDF-1.4\n"
    body = b""
    offsets = [0]
    cursor = len(header)
    for obj in objects:
        offsets.append(cursor)
        body += obj
        cursor += len(obj)

    xref_start = cursor
    xref = [b"xref\n0 6\n0000000000 65535 f \n"]
    for off in offsets[1:]:
        xref.append(f"{off:010d} 00000 n \n".encode("ascii"))

    trailer = (
        b"trailer\n<< /Size 6 /Root 1 0 R >>\n"
        b"startxref\n"
        + str(xref_start).encode("ascii")
        + b"\n%%EOF\n"
    )
    return header + body + b"".join(xref) + trailer
