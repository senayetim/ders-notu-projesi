from bolumle import sinirlari_duzelt
from yardimci import bolum_bul, iceriyor, sadelestir, vurgula


def bolum(baslangic, bitis):
    return {"baslik": "b", "baslangic_sn": baslangic, "bitis_sn": bitis, "ozet": "", "anahtar_kelimeler": []}


def test_sadelestir_turkce_harfleri_esitler():
    assert sadelestir("IŞIK İĞNE çöpü") == "isik igne copu"


def test_vurgula_aksansiz_sorguyla_ozgun_metni_korur():
    assert vurgula("Küçük Prens geldi", "kucuk") == "<mark>Küçük</mark> Prens geldi"


def test_vurgula_tum_gecisleri_isaretler():
    assert vurgula("koyun ve Koyun", "koyun") == "<mark>koyun</mark> ve <mark>Koyun</mark>"


def test_arama_kelime_basini_yakalar_ortasini_yakalamaz():
    assert iceriyor("İktanın önemi", "ikta")
    assert iceriyor("Bu (ikta) sistemi", "ikta")
    assert not iceriyor("Anladıktan sonra", "ikta")
    assert vurgula("Anladıktan sonra ikta", "ikta") == "Anladıktan sonra <mark>ikta</mark>"


def test_vurgula_bos_sorgu():
    assert vurgula("metin", "") == "metin"


def test_vurgula_html_kacar():
    assert vurgula("<b>koyun</b>", "koyun") == "&lt;b&gt;<mark>koyun</mark>&lt;/b&gt;"
    assert vurgula("<script>", "") == "&lt;script&gt;"


def test_bolum_bul_sinirlar():
    bolumler = [bolum(0, 10), bolum(10, 20)]
    assert bolum_bul(bolumler, 10)[0] == 1
    assert bolum_bul(bolumler, 20) is None


def test_sinirlar_bosluklari_kapatir_ve_kaydin_sonuna_uzanir():
    sonuc = sinirlari_duzelt([bolum(5, 78), bolum(79, 117)], 120.8)
    assert [(b["baslangic_sn"], b["bitis_sn"]) for b in sonuc] == [(0, 79), (79, 120.8)]


def test_sinirlar_sirasiz_ve_cakisan_bolumleri_duzeltir():
    sonuc = sinirlari_duzelt([bolum(50, 100), bolum(0, 60)], 100)
    assert [(b["baslangic_sn"], b["bitis_sn"]) for b in sonuc] == [(0, 50), (50, 100)]


def test_sinirlar_sifir_uzunluklu_bolumu_atar():
    assert len(sinirlari_duzelt([bolum(0, 10), bolum(10, 10), bolum(10, 20)], 20)) == 2


def test_sinirlar_tekrar_uygulaninca_degismez():
    bir_kez = sinirlari_duzelt([bolum(5, 78), bolum(79, 117)], 120.8)
    assert sinirlari_duzelt(bir_kez, 120.8) == bir_kez


def test_son_parca_artik_bir_bolume_duser():
    sonuc = sinirlari_duzelt([bolum(0, 117)], 120.8)
    assert bolum_bul(sonuc, 117.28) is not None
