def sadelestir(metin):
    """Küçük harfe çevirir ve Türkçe karakterleri sadeleştirir (arama için)."""
    metin = metin.replace("İ", "i").replace("I", "ı").lower()
    return metin.translate(str.maketrans("çğıöşü", "cgiosu"))


def vurgula(metin, sorgu):
    m, s = sadelestir(metin), sadelestir(sorgu)
    if not s:
        return metin
    sonuc, i = "", 0
    while True:
        j = m.find(s, i)
        if j == -1:
            return sonuc + metin[i:]
        sonuc += metin[i:j] + "**" + metin[j:j + len(s)] + "**"
        i = j + len(s)


def bolum_bul(bolumler, sn):
    """Verilen saniyenin hangi bölümde olduğunu (sıra, bölüm) olarak döner."""
    for i, b in enumerate(bolumler):
        if b["baslangic_sn"] <= sn < b["bitis_sn"]:
            return i, b
    return None
