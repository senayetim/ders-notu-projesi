import json
import re
from pathlib import Path

from bolumle import sinirlari_duzelt
from yardimci import iceriyor

DOSYA_KALIBI = re.compile(r"^(?P<ad>.+?)(?:_[0-9a-f]{8})?_(?P<model>small|medium|large-v3)_transkript\.json$")


def dersleri_listele(dizin):
    """Kayıtlı dersleri en son işlenen başta olacak şekilde döner."""
    dersler = []
    yollar = sorted(dizin.glob("*_transkript.json"), key=lambda y: y.stat().st_mtime, reverse=True)
    for yol in yollar:
        eslesme = DOSYA_KALIBI.match(yol.name)
        if eslesme:
            dersler.append({
                "anahtar": yol.name.removesuffix("_transkript.json"),
                "ad": eslesme["ad"],
                "model": eslesme["model"],
            })
    return dersler


def ders_oku(dizin, anahtar):
    """Kayıtlı dersi (transkript, bölümler, ölçümler) olarak okur."""
    transkript = json.loads((dizin / f"{anahtar}_transkript.json").read_text(encoding="utf-8"))
    b_yol = dizin / f"{anahtar}_bolumler.json"
    if not b_yol.exists():
        return transkript, [], None
    kayit = json.loads(b_yol.read_text(encoding="utf-8"))
    return transkript, sinirlari_duzelt(kayit["bolumler"], transkript["ses_suresi_sn"]), kayit["olcumler"]


def ders_ozeti(dizin, ders):
    """Ana sayfadaki ders kartı için gerekli bilgileri toplar."""
    transkript, bolumler, _ = ders_oku(dizin, ders["anahtar"])
    sure = transkript["ses_suresi_sn"]
    return {
        **ders,
        "sure_sn": sure,
        "bolum_sayisi": len(bolumler),
        "oranlar": [(b["bitis_sn"] - b["baslangic_sn"]) / sure for b in bolumler],
        "ses_var": Path(transkript["ses_dosyasi"]).exists(),
        "calisma_var": (dizin / f"{ders['anahtar']}_calisma.json").exists(),
        "gomme_var": (dizin / f"{ders['anahtar']}_gomme.npz").exists(),
    }


def tum_derslerde_ara(dizin, sorgu):
    """Sorgunun geçtiği parçaları ders bilgisiyle birlikte döner."""
    sonuclar = []
    for ders in dersleri_listele(dizin):
        transkript, _, _ = ders_oku(dizin, ders["anahtar"])
        for p in transkript["parcalar"]:
            if iceriyor(p["metin"], sorgu):
                sonuclar.append({**ders, "baslangic": p["baslangic"], "metin": p["metin"]})
    return sonuclar
