from pydantic import BaseModel

from bolumle import llm_json, transkripti_metne_cevir
from yardimci import parcaya_oturt

SECENEK_SAYISI = 4
EN_FAZLA_KAYNAK = 3


class Soru(BaseModel):
    soru: str
    secenekler: list[str]
    dogru_indeks: int
    aciklama: str
    kaynak_sn: float


class Kart(BaseModel):
    on: str
    arka: str
    kaynak_sn: float


class CalismaSeti(BaseModel):
    sorular: list[Soru]
    kartlar: list[Kart]


class Cevap(BaseModel):
    bulundu: bool
    cevap: str
    kaynak_sn: list[float]


CALISMA_TALIMATI = f"""Sen bir ders çalışma asistanısın.
Sana bir ders transkripti verilecek. Her satır "[saniye] metin" biçimindedir.
Öğrencinin sınava hazırlanması için Türkçe çalışma materyali hazırla.
Kurallar:
- sorular: 10 çoktan seçmeli soru. Her soruda tam {SECENEK_SAYISI} seçenek olsun, dogru_indeks 0'dan başlasın.
- Doğru seçeneğin yeri sorular arasında değişsin; yanlış seçenekler inandırıcı olsun.
- aciklama: doğru cevabın neden doğru olduğunu 1-2 cümleyle anlat.
- kartlar: 15 bilgi kartı. on bir kavram ya da kısa soru, arka kısa ve net cevap olsun.
- kaynak_sn: bilginin geçtiği satırın saniye değeri; transkriptten al, uydurma.
- Yalnızca transkriptteki bilgileri kullan. Sorular dersin tamamına yayılsın.
- Transkriptte tanıma hataları olabilir; terimleri bağlamdan düzelterek yaz.
"""

SORU_TALIMATI = """Sen bir ders asistanısın.
Sana bir ders transkripti ve öğrencinin sorusu verilecek. Transkriptte her satır "[saniye] metin" biçimindedir.
Kurallar:
- Soruyu yalnızca transkripte dayanarak, kısa ve açık Türkçeyle cevapla.
- Cevap transkriptte yoksa bulundu=false yap, cevapta bunu söyle, kendi bilginle tamamlama.
- kaynak_sn: cevabın dayandığı en önemli 1-3 satırın saniye değeri; transkriptten al, uydurma.
- Transkriptte tanıma hataları olabilir; terimleri bağlamdan düzelterek yaz.
"""


def calisma_setini_temizle(veri, parcalar):
    """Bozuk soruları atar, kaynak saniyelerini gerçek transkript parçalarına oturtur."""
    sorular = [
        {**s, "kaynak_sn": parcaya_oturt(parcalar, s["kaynak_sn"])}
        for s in veri["sorular"]
        if len(s["secenekler"]) >= 2 and 0 <= s["dogru_indeks"] < len(s["secenekler"])
    ]
    kartlar = [{**k, "kaynak_sn": parcaya_oturt(parcalar, k["kaynak_sn"])} for k in veri["kartlar"]]
    return {"sorular": sorular, "kartlar": kartlar}


def calisma_seti_uret(transkript):
    """Transkriptten quiz ve bilgi kartları üretir."""
    metin = transkripti_metne_cevir(transkript)
    veri, _ = llm_json(metin, CALISMA_TALIMATI, CalismaSeti, sicaklik=0.4)
    return calisma_setini_temizle(veri, transkript["parcalar"])


def cevabi_temizle(veri, parcalar):
    """Kaynakları gerçek parçalara oturtur, tekrarları atar; cevap bulunmadıysa kaynak bırakmaz."""
    kaynaklar = []
    if veri["bulundu"]:
        for sn in veri["kaynak_sn"]:
            oturan = parcaya_oturt(parcalar, sn)
            if oturan not in kaynaklar:
                kaynaklar.append(oturan)
    return {"bulundu": veri["bulundu"], "cevap": veri["cevap"], "kaynak_sn": kaynaklar[:EN_FAZLA_KAYNAK]}


def soru_cevapla(transkript, soru):
    """Soruyu yalnızca transkripte dayanarak, zaman damgalı kaynaklarla cevaplar."""
    icerik = f"TRANSKRİPT:\n{transkripti_metne_cevir(transkript)}\n\nSORU: {soru}"
    veri, _ = llm_json(icerik, SORU_TALIMATI, Cevap)
    return cevabi_temizle(veri, transkript["parcalar"])
