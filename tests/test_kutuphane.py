import json
import os

from kutuphane import ders_oku, dersleri_listele, tum_derslerde_ara


def transkript_yaz(dizin, anahtar, metin, ses="yuklenenler/ders.mp3"):
    veri = {"ses_dosyasi": ses, "ses_suresi_sn": 20.0, "parcalar": [{"baslangic": 3.0, "bitis": 5.0, "metin": metin}]}
    yol = dizin / f"{anahtar}_transkript.json"
    yol.write_text(json.dumps(veri), encoding="utf-8")
    return yol


def test_ozetli_ve_ozetsiz_adlar_cozulur(tmp_path):
    transkript_yaz(tmp_path, "Ders 1 - Tarih_e22f4dba_medium", "a")
    transkript_yaz(tmp_path, "Eski_kayit_large-v3", "b")
    (tmp_path / "ilgisiz_transkript.json").write_text("{}", encoding="utf-8")

    dersler = {d["ad"]: d["model"] for d in dersleri_listele(tmp_path)}
    assert dersler == {"Ders 1 - Tarih": "medium", "Eski_kayit": "large-v3"}


def test_en_son_islenen_basta(tmp_path):
    os.utime(transkript_yaz(tmp_path, "eski_small", "a"), (1000, 1000))
    transkript_yaz(tmp_path, "yeni_small", "b")
    assert dersleri_listele(tmp_path)[0]["ad"] == "yeni"


def test_bolumsuz_ders_acilir(tmp_path):
    transkript_yaz(tmp_path, "ders_small", "a")
    _, bolumler, olcumler = ders_oku(tmp_path, "ders_small")
    assert bolumler == [] and olcumler is None


def test_kayitli_bolum_sinirlari_duzeltilir(tmp_path):
    transkript_yaz(tmp_path, "ders_small", "a")
    kayit = {"bolumler": [{"baslik": "b", "baslangic_sn": 5, "bitis_sn": 15}], "olcumler": {"model": "m"}}
    (tmp_path / "ders_small_bolumler.json").write_text(json.dumps(kayit), encoding="utf-8")
    _, bolumler, _ = ders_oku(tmp_path, "ders_small")
    assert (bolumler[0]["baslangic_sn"], bolumler[0]["bitis_sn"]) == (0, 20.0)


def test_tum_derslerde_arama_turkce_harf_gozetmez(tmp_path):
    transkript_yaz(tmp_path, "birinci_small", "Tımar sistemi")
    transkript_yaz(tmp_path, "ikinci_small", "TIMAR beyleri")
    transkript_yaz(tmp_path, "ucuncu_small", "alakasız")
    sonuc = tum_derslerde_ara(tmp_path, "timar")
    assert sorted(s["ad"] for s in sonuc) == ["birinci", "ikinci"]
    assert sonuc[0]["baslangic"] == 3.0
