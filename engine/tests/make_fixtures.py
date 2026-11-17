"""Small synthetic PDFs only. No research data is included in automated tests."""

from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def make_pdf(
    path: Path,
    title="Synthetic viral evolution",
    body="Evidence for viral evolution. DOI: 10.1234/petrus.test",
    author="Example Researcher",
):
    writer = PdfWriter()
    page = writer.add_blank_page(width=400, height=500)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    safe = body.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream.set_data(f"BT /F1 11 Tf 20 450 Td ({safe}) Tj ET".encode("latin-1"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.add_metadata({"/Title": title, "/Author": author, "/CreationDate": "D:20261015000000"})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        writer.write(handle)
    return path


if __name__ == "__main__":
    fixtures = Path(__file__).parent / "fixtures"
    make_pdf(fixtures / "evolution.pdf")
    make_pdf(
        fixtures / "surveillance.pdf",
        title="Synthetic surveillance study",
        body="Genomic surveillance and sample testing. 10.5678/test.2026",
    )
