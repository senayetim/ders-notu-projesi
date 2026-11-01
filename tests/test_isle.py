import importlib
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    modul = importlib.import_module("app")
    modul.YUKLEME_DIZINI.mkdir(exist_ok=True)
    modul.CIKTI_DIZINI.mkdir(exist_ok=True)
    monkeypatch.setattr(modul, "st", MagicMock(session_state=SimpleNamespace()))
    cagrilar = {"transkript": 0, "bolum": 0}

    def sahte_transkript(yol, model, terimler="", ilerleme=None):
        cagrilar["transkript"] += 1
        return {
            "ses_dosyasi": yol, "ses_suresi_sn": 20.0,
            "parcalar": [{"baslangic": 0.0, "bitis": 20.0, "metin": "x"}],
        }

    def sahte_bolumle(transkript):
        cagrilar["bolum"] += 1
        return (
            [{"baslik": "b", "baslangic_sn": 0, "bitis_sn": 20.0, "ozet": "", "anahtar_kelimeler": []}],
            {"model": "m"},
        )

    monkeypatch.setattr(modul, "transkript_et", sahte_transkript)
    monkeypatch.setattr(modul, "bolumle", sahte_bolumle)
    modul.cagrilar = cagrilar
    return modul


def test_ayni_dosya_kayittan_gelir(app):
    app.isle(b"ses", "ders.mp3", "medium", False, False)
    app.isle(b"ses", "ders.mp3", "medium", False, False)
    assert app.cagrilar == {"transkript": 1, "bolum": 1}


def test_ayni_adli_farkli_dosya_yeniden_islenir(app):
    app.isle(b"birinci", "ders.mp3", "medium", False, False)
    app.isle(b"ikinci", "ders.mp3", "medium", False, False)
    assert app.cagrilar == {"transkript": 2, "bolum": 2}


def test_yeni_transkript_bolumleri_de_yeniler(app):
    app.isle(b"ses", "ders.mp3", "medium", False, False)
    app.isle(b"ses", "ders.mp3", "medium", True, False)
    assert app.cagrilar == {"transkript": 2, "bolum": 2}


def test_bolumleme_basarisizsa_eski_bolum_geri_gelmez(app, monkeypatch):
    app.isle(b"ses", "ders.mp3", "medium", False, False)

    def bozuk(transkript):
        raise RuntimeError("yok")

    monkeypatch.setattr(app, "bolumle", bozuk)
    app.isle(b"ses", "ders.mp3", "medium", True, False)
    app.isle(b"ses", "ders.mp3", "medium", False, False)
    assert not list(app.CIKTI_DIZINI.glob("*_bolumler.json"))


def test_transkript_hatasi_uygulamayi_dusurmez(app, monkeypatch):
    def bozuk(yol, model, terimler="", ilerleme=None):
        raise RuntimeError("bozuk dosya")

    monkeypatch.setattr(app, "transkript_et", bozuk)
    app.isle(b"ses", "ders.mp3", "medium", False, False)
    assert not list(app.CIKTI_DIZINI.glob("*.json"))


def test_kayitli_bolumlerin_sinirlari_duzeltilir(app):
    app.isle(b"ses", "ders.mp3", "medium", False, False)
    b_yol = next(app.CIKTI_DIZINI.glob("*_bolumler.json"))
    kayit = json.loads(b_yol.read_text(encoding="utf-8"))
    kayit["bolumler"][0].update(baslangic_sn=5, bitis_sn=15)
    b_yol.write_text(json.dumps(kayit), encoding="utf-8")

    app.isle(b"ses", "ders.mp3", "medium", False, False)
    assert app.st.session_state.bolumler[0]["baslangic_sn"] == 0
    assert app.st.session_state.bolumler[0]["bitis_sn"] == 20.0
