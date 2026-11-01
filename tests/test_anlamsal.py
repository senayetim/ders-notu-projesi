import io
from types import SimpleNamespace

import numpy as np
import pytest
from docx import Document
from google.genai import types

import anlamsal
from disari_aktar import notlari_docx, notlari_pdf

BOLUMLER = [{
    "baslik": "Tımar sistemi", "baslangic_sn": 0, "bitis_sn": 4000,
    "ozet": "Şükrü'nün özeti: İĞNE, ığdır, çöğür.", "anahtar_kelimeler": ["tımar", "ikta"],
}]


def test_parcalar_hedef_sureye_gore_birlesir():
    parcalar = [
        {"baslangic": 0.0, "bitis": 20.0, "metin": "a"},
        {"baslangic": 20.0, "bitis": 44.0, "metin": "b"},
        {"baslangic": 44.0, "bitis": 60.0, "metin": "c"},
    ]
    assert anlamsal.parcalari_birlestir(parcalar) == [
        {"baslangic": 0.0, "metin": "a b"},
        {"baslangic": 44.0, "metin": "c"},
    ]


class SahteIstemci:
    """Gerçek API gibi davranır: düz metin listesini tek vektörde birleştirir."""

    def __init__(self, sabit_adet=None):
        self.models = self
        self.sabit_adet = sabit_adet

    def embed_content(self, model, contents, config):
        adet = self.sabit_adet or (len(contents) if isinstance(contents[0], types.Content) else 1)
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[1.0, 0.0]) for _ in range(adet)])


def test_her_metin_ayri_vektor_alir():
    assert anlamsal._gom(SahteIstemci(), "m", ["a", "b", "c"], "RETRIEVAL_DOCUMENT").shape == (3, 2)


def test_eksik_vektor_sessizce_gecilmez():
    with pytest.raises(RuntimeError):
        anlamsal._gom(SahteIstemci(sabit_adet=1), "m", ["a", "b"], "RETRIEVAL_DOCUMENT")


def dizin_ornegi():
    return {
        "model": "m",
        "baslangic": np.array([0.0, 50.0, 100.0]),
        "metin": np.array(["bir", "iki", "üç"]),
        "vektor": np.array([[1.0, 0.0], [0.0, 1.0], [0.6, 0.8]], dtype=np.float32),
    }


def test_en_benzerler_siralar_ve_sinirlar():
    sonuc = anlamsal.en_benzerler(dizin_ornegi(), np.array([0.0, 1.0], dtype=np.float32), adet=2)
    assert [s["metin"] for s in sonuc] == ["iki", "üç"]


def test_dizin_kaydedilip_okunur(tmp_path):
    yol = tmp_path / "d_gomme.npz"
    anlamsal.dizin_kaydet(yol, dizin_ornegi())
    okunan = anlamsal.dizin_oku(yol)
    assert okunan["model"] == "m"
    assert okunan["metin"].tolist() == ["bir", "iki", "üç"]


def test_word_turkce_icerigi_tasir():
    belge = Document(io.BytesIO(notlari_docx("Ders", BOLUMLER)))
    metin = "\n".join(p.text for p in belge.paragraphs)
    assert "[00:00 - 1:06:40] Tımar sistemi" in metin
    assert "İĞNE, ığdır" in metin


def test_pdf_uretilir():
    pdf = notlari_pdf("Ders ğüşıöç", BOLUMLER)
    assert pdf.startswith(b"%PDF")
