import re
from bisect import bisect_right
from html import escape


def sadelestir(metin):
    """Küçük harfe çevirir ve Türkçe karakterleri sadeleştirir (arama için)."""
    metin = metin.replace("İ", "i").replace("I", "ı").lower()
    return metin.translate(str.maketrans("çğıöşü", "cgiosu"))


def _eslesmeler(metin, sorgu):
    """Sorgunun kelime başında geçtiği yerleri bulur; "ikta" "Anladıktan"ın ortasını yakalamaz."""
    return re.finditer(rf"(?<!\w){re.escape(sadelestir(sorgu))}", sadelestir(metin))


def iceriyor(metin, sorgu):
    return next(_eslesmeler(metin, sorgu), None) is not None


def vurgula(metin, sorgu):
    """Sorgunun geçtiği yerleri <mark> ile sarar; dönen metin HTML olarak güvenlidir."""
    if not sadelestir(sorgu):
        return escape(metin)
    sonuc, i = "", 0
    for e in _eslesmeler(metin, sorgu):
        sonuc += escape(metin[i:e.start()]) + "<mark>" + escape(metin[e.start():e.end()]) + "</mark>"
        i = e.end()
    return sonuc + escape(metin[i:])


def bolum_bul(bolumler, sn):
    """Verilen saniyenin hangi bölümde olduğunu (sıra, bölüm) olarak döner."""
    for i, b in enumerate(bolumler):
        if b["baslangic_sn"] <= sn < b["bitis_sn"]:
            return i, b
    return None


def parcaya_oturt(parcalar, sn):
    """LLM'in verdiği saniyeyi, o anda konuşulan gerçek parçanın başlangıcına çeker."""
    baslangiclar = [p["baslangic"] for p in parcalar]
    return baslangiclar[max(bisect_right(baslangiclar, sn) - 1, 0)]
