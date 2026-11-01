import json
import sys
import time

from google.genai import errors
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()

# Sırayla denenir: ilki yoğunsa ya da bulunamazsa sıradakine geçilir
MODELLER = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-3.5-flash-lite"]
MODEL = MODELLER[0]  # app.py kenar çubuğunda göstermek için
DENEME_SAYISI = 3


class Bolum(BaseModel):
    baslik: str
    baslangic_sn: float
    bitis_sn: float
    ozet: str
    anahtar_kelimeler: list[str]


SISTEM_TALIMATI = """Sen bir ders kaydı analiz asistanısın.
Sana bir ders transkripti verilecek. Her satır "[saniye] metin" biçimindedir,
köşeli parantez içindeki sayı o cümlenin başlangıç saniyesidir.

Görevin transkripti konu bütünlüğüne göre ardışık bölümlere ayırmak.
Kurallar:
- Bölümler zaman sırasında olsun, birbiriyle çakışmasın, tüm kaydı kapsasın.
- Bir bölüm yeni bir alt konu başladığında biter; çok kısa (30 saniyeden kısa) bölümler oluşturma.
- baslik: en fazla 8 kelime, konuyu net anlatsın.
- ozet: 2-4 cümlelik, öğrencinin çalışma notu gibi Türkçe özet. Transkriptte olmayan bilgi ekleme.
- anahtar_kelimeler: 3-6 adet, bölümde geçen önemli terimler.
- baslangic_sn ve bitis_sn değerlerini transkriptteki saniye değerlerinden al, uydurma.
- Transkriptte tanıma hataları olabilir (yanlış yazılmış teknik terimler); bağlamdan düzelterek yaz.
"""


def transkripti_metne_cevir(transkript):
    satirlar = [f"[{int(p['baslangic'])}] {p['metin']}" for p in transkript["parcalar"]]
    return "\n".join(satirlar)


def sinirlari_duzelt(bolumler, toplam_sn):
    """LLM'in verdiği sınırları boşluksuz ve tüm kaydı kapsayacak hale getirir."""
    sirali = sorted(bolumler, key=lambda b: b["baslangic_sn"])
    duzeltilmis = []
    for i, b in enumerate(sirali):
        baslangic = 0 if i == 0 else b["baslangic_sn"]
        bitis = sirali[i + 1]["baslangic_sn"] if i + 1 < len(sirali) else toplam_sn
        if bitis > baslangic:
            duzeltilmis.append({**b, "baslangic_sn": baslangic, "bitis_sn": bitis})
    return duzeltilmis


def llm_json(icerik, talimat, sema, sicaklik=0.2):
    """LLM'den şemaya uygun JSON ister, modeller arasında yedekli dener. (veri, ölçümler) döner."""
    istemci = genai.Client()  # GEMINI_API_KEY ortam değişkenini kendisi okur
    config = types.GenerateContentConfig(
        system_instruction=talimat,
        response_mime_type="application/json",
        response_schema=sema,
        temperature=sicaklik,
    )

    hatalar = []
    toplam_deneme = 0
    for model in MODELLER:
        for deneme in range(1, DENEME_SAYISI + 1):
            toplam_deneme += 1
            try:
                baslangic = time.time()
                yanit = istemci.models.generate_content(model=model, contents=icerik, config=config)
                sure = time.time() - baslangic

                if not yanit.text:
                    raise RuntimeError("Model boş yanıt döndürdü")
                veri = json.loads(yanit.text)
                if not veri:
                    raise RuntimeError("Model boş sonuç döndürdü")

                kullanim = yanit.usage_metadata
                olcumler = {
                    "model": model,
                    "gecikme_sn": round(sure, 2),
                    "girdi_token": kullanim.prompt_token_count,
                    "cikti_token": kullanim.candidates_token_count,
                    "toplam_deneme": toplam_deneme,
                }
                return veri, olcumler

            except errors.APIError as e:
                hatalar.append(f"{model} (deneme {deneme}): {e.code}")
                if e.code in (500, 503, 429) and deneme < DENEME_SAYISI:
                    time.sleep(3 * deneme)   # 3 sn, 6 sn bekle, tekrar dene
                    continue
                break                         # 404 vb.: bu modeli bırak, sıradakine geç
            except (RuntimeError, json.JSONDecodeError) as e:
                hatalar.append(f"{model} (deneme {deneme}): {e}")
                if deneme < DENEME_SAYISI:
                    continue
                break

    raise RuntimeError("Hiçbir model yanıt veremedi: " + " | ".join(hatalar))


def bolumle(transkript):
    """Transkripti LLM ile konu bölümlerine ayırır. (bölümler, ölçümler) döner."""
    metin = transkripti_metne_cevir(transkript)
    bolumler, olcumler = llm_json(metin, SISTEM_TALIMATI, list[Bolum])
    return sinirlari_duzelt(bolumler, transkript["ses_suresi_sn"]), olcumler


def sn_to_dk(sn):
    sn = int(sn)
    saat, dakika, saniye = sn // 3600, sn // 60 % 60, sn % 60
    if saat:
        return f"{saat}:{dakika:02d}:{saniye:02d}"
    return f"{dakika:02d}:{saniye:02d}"


if __name__ == "__main__":
    yol = sys.argv[1] if len(sys.argv) > 1 else "test_transkript.json"
    with open(yol, encoding="utf-8") as f:
        transkript = json.load(f)

    bolumler, olcumler = bolumle(transkript)

    cikti = yol.replace("_transkript.json", "_bolumler.json")
    with open(cikti, "w", encoding="utf-8") as f:
        json.dump({"bolumler": bolumler, "olcumler": olcumler}, f, ensure_ascii=False, indent=2)

    for b in bolumler:
        print(f"[{sn_to_dk(b['baslangic_sn'])} - {sn_to_dk(b['bitis_sn'])}] {b['baslik']}")
        print(f"    {b['ozet']}\n")
    print(f"Ölçümler: {olcumler}")
    print(f"Kaydedildi: {cikti}")