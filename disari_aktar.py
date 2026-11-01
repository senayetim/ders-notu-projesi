import io
from pathlib import Path

from docx import Document
from fpdf import FPDF

from bolumle import sn_to_dk

# Türkçe harfleri içeren yazı tipleri (normal, kalın); bulunan ilk çift kullanılır
YAZI_TIPLERI = [
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
]


def _aralik(b):
    return f"{sn_to_dk(b['baslangic_sn'])} - {sn_to_dk(b['bitis_sn'])}"


def notlari_docx(dosya_adi, bolumler):
    belge = Document()
    belge.add_heading(dosya_adi, level=0)
    for b in bolumler:
        belge.add_heading(f"[{_aralik(b)}] {b['baslik']}", level=1)
        belge.add_paragraph(b["ozet"])
        paragraf = belge.add_paragraph()
        paragraf.add_run("Anahtar kelimeler: ").bold = True
        paragraf.add_run(", ".join(b["anahtar_kelimeler"]))
    cikti = io.BytesIO()
    belge.save(cikti)
    return cikti.getvalue()


def notlari_pdf(dosya_adi, bolumler):
    """Notları PDF yapar; Türkçe destekli yazı tipi bulunamazsa None döner."""
    yazi_tipi = next((y for y in YAZI_TIPLERI if Path(y[0]).exists() and Path(y[1]).exists()), None)
    if not yazi_tipi:
        return None

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font("Govde", "", yazi_tipi[0])
    pdf.add_font("Govde", "B", yazi_tipi[1])
    pdf.add_page()

    def yaz(metin, stil, boyut, bosluk):
        pdf.set_font("Govde", stil, boyut)
        pdf.multi_cell(0, boyut * 0.55, metin, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(bosluk)

    yaz(dosya_adi, "B", 16, 4)
    for b in bolumler:
        yaz(f"[{_aralik(b)}] {b['baslik']}", "B", 12, 1)
        yaz(b["ozet"], "", 11, 1)
        yaz(f"Anahtar kelimeler: {', '.join(b['anahtar_kelimeler'])}", "", 9, 4)
    return bytes(pdf.output())
