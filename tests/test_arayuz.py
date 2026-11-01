import arayuz

KOTU = '<img src=x onerror="alert(1)">'


def bolum(baslangic, bitis, baslik="b"):
    return {"baslik": baslik, "baslangic_sn": baslangic, "bitis_sn": bitis, "ozet": "", "anahtar_kelimeler": []}


def test_uzun_sure():
    assert arayuz.uzun_sure(4170) == "1 sa 10 dk"
    assert arayuz.uzun_sure(1200) == "20 dk"
    assert arayuz.uzun_sure(10) == "1 dk"


def test_dis_metinler_kacislanir():
    ozet = {
        "ad": KOTU, "sure_sn": 60, "bolum_sayisi": 1, "model": "medium", "oranlar": [1.0],
        "ses_var": True, "calisma_var": False, "gomme_var": False,
    }
    b = {**bolum(0, 10, KOTU), "ozet": KOTU, "anahtar_kelimeler": [KOTU]}
    parcalar = [
        arayuz.ders_karti(ozet),
        arayuz.bolum_karti(0, b, False),
        arayuz.zaman_seridi([b], 10),
        arayuz.bilgi_karti(KOTU, 1, 1, False),
        arayuz.baloncuk(KOTU, "soru"),
        arayuz.quiz_sonucu(1, True, KOTU, KOTU),
        arayuz.bulunan("x", kaynak=KOTU, rozet=(KOTU, "#000")),
        arayuz.transkript_okuma([{"baslangic": 0, "metin": KOTU}], [b]),
        arayuz.istatistikler([(KOTU, KOTU)]),
    ]
    assert not any("<img" in p for p in parcalar)


def test_transkript_bolum_basliklari_yerine_oturur():
    parcalar = [{"baslangic": 0, "metin": "a"}, {"baslangic": 12, "metin": "b"}]
    metin = arayuz.transkript_okuma(parcalar, [bolum(0, 10, "Giriş"), bolum(10, 20, "Gelişme")])
    assert metin.index("Giriş") < metin.index(">a<") < metin.index("Gelişme") < metin.index(">b<")


def test_skor_bos_cevabi_bildirir():
    assert "2 soru boş kaldı" in arayuz.skor(5, 10, 8)
    assert "boş kaldı" not in arayuz.skor(10, 10, 10)
