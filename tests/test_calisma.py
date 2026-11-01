import calisma
from bolumle import sn_to_dk
from calisma import calisma_setini_temizle, cevabi_temizle
from transkript import terimleri_birlestir
from yardimci import parcaya_oturt

PARCALAR = [{"baslangic": 0.0}, {"baslangic": 10.5}, {"baslangic": 20.0}]


def soru(dogru, secenekler=("a", "b", "c", "d"), kaynak=11):
    return {"soru": "s", "secenekler": list(secenekler), "dogru_indeks": dogru, "aciklama": "", "kaynak_sn": kaynak}


def test_parcaya_oturt():
    assert parcaya_oturt(PARCALAR, 11) == 10.5
    assert parcaya_oturt(PARCALAR, 999) == 20.0
    assert parcaya_oturt(PARCALAR, -5) == 0.0


def test_gecersiz_sorular_atilir_kaynaklar_oturur():
    veri = {"sorular": [soru(1), soru(4), soru(0, secenekler=("tek",))], "kartlar": [{"on": "o", "arka": "a", "kaynak_sn": 21}]}
    sonuc = calisma_setini_temizle(veri, PARCALAR)
    assert len(sonuc["sorular"]) == 1
    assert sonuc["sorular"][0]["kaynak_sn"] == 10.5
    assert sonuc["kartlar"][0]["kaynak_sn"] == 20.0


def test_cevap_kaynaklari_tekillesir_ve_sinirlanir():
    sonuc = cevabi_temizle({"bulundu": True, "cevap": "c", "kaynak_sn": [11, 12, 0, 20, 21]}, PARCALAR)
    assert sonuc["kaynak_sn"] == [10.5, 0.0, 20.0]


def test_bulunamayan_cevapta_kaynak_gosterilmez():
    assert cevabi_temizle({"bulundu": False, "cevap": "yok", "kaynak_sn": [11]}, PARCALAR)["kaynak_sn"] == []


def test_soru_transkript_ile_birlikte_gonderilir(monkeypatch):
    gorulen = {}

    def sahte(icerik, talimat, sema, sicaklik=0.2):
        gorulen["icerik"] = icerik
        return {"bulundu": True, "cevap": "c", "kaynak_sn": [0]}, {}

    monkeypatch.setattr(calisma, "llm_json", sahte)
    calisma.soru_cevapla({"parcalar": [{"baslangic": 0.0, "metin": "tımar"}]}, "nedir?")
    assert "[0] tımar" in gorulen["icerik"] and "SORU: nedir?" in gorulen["icerik"]


def test_saatli_sure():
    assert sn_to_dk(75) == "01:15"
    assert sn_to_dk(4170.4) == "1:09:30"


def test_terimler_birlesir():
    assert terimleri_birlestir(" tımar, ikta\n\nhassa ordusu ,") == "tımar, ikta, hassa ordusu"
    assert terimleri_birlestir("  ") == ""
