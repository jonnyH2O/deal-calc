"""Builds small PDF and Word files for the tests of PDF Text and the Report Reader.

PDF Text finds a PDF's objects by looking for "n 0 obj", so these PDFs need no cross-reference table.
"""

import io
import zipfile
import zlib

HELVETICA = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"  # no /Widths, so each character is 500 wide


def stream(data: bytes, info: bytes = b"", compress: bool = False, length: bytes | None = None) -> bytes:
    """A stream object. compress applies Flate; length replaces the right /Length (such as b"99" or b"6 0 R")."""
    if compress:
        data = zlib.compress(data)
        info += b" /Filter /FlateDecode"
    length = str(len(data)).encode() if length is None else length
    return b"<<" + info + b" /Length " + length + b" >>\nstream\n" + data + b"\nendstream"


def make_pdf(objects: dict[int, bytes], trailer: bytes = b"/Root 1 0 R") -> bytes:
    """A PDF file holding the objects, in the order given."""
    parts = [b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"]
    parts += [b"%d 0 obj\n%b\nendobj\n" % (num, body) for num, body in objects.items()]
    parts.append(b"trailer\n<< " + trailer + b" >>\n%%EOF\n")
    return b"".join(parts)


def page_pdf(content: bytes, extra: dict[int, bytes] | None = None, compress: bool = False,
             trailer: bytes = b"/Root 1 0 R") -> bytes:
    """A one-page PDF: catalog 1, page tree 2, page 3, Helvetica as /F1 (object 4), the content stream 5, and any
    extra objects."""
    return make_pdf({
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> "
           b"/Contents 5 0 R >>",
        4: HELVETICA,
        5: stream(content, compress=compress),
        **(extra or {}),
    }, trailer)


def text_pdf(*lines: str) -> bytes:
    """A one-page PDF with each line of text drawn on its own line, and a tab (a wide gap) wherever a line has one."""
    content = [b"BT /F1 10 Tf 14 TL 72 760 Td"]
    for line in lines:
        content.append(b"T*")
        for cell in line.split("\t"):
            content.append(b"(%b) Tj 200 0 Td" % cell.encode("cp1252").replace(b"(", b"\\(").replace(b")", b"\\)"))
        content.append(b"%d 0 Td" % (-200 * len(line.split("\t"))))
    content.append(b"ET")
    return page_pdf(b"\n".join(content))


def word_file(document_xml: str, parts: dict[str, str] | None = None) -> bytes:
    """A .docx file (a zip file) holding word/document.xml and any other parts."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", document_xml)
        for name, text in (parts or {}).items():
            archive.writestr(name, text)
    return buffer.getvalue()
