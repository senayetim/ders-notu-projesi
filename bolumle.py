import json
import os
import sys
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()

# Model adı değişirse sadece bu satırı değiştir. 404 hatası alırsan "gemini-2.5-flash" dene.
MODEL = "gemini-3.5-flash"


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


def bolumle(transkript):
    """Transkripti LLM ile konu bölümlerine ayırır. (bölümler, ölçümler) döner."""
    istemci = genai.Client()  # GEMINI_API_KEY ortam değişkenini kendisi okur
    metin = transkripti_metne_cevir(transkript)

    baslangic = time.time()
    yanit = istemci.models.generate_content(
        model=MODEL,
        contents=metin,
        config=types.GenerateContentConfig(
            system_instruction=SISTEM_TALIMATI,
            response_mime_type="application/json",
            response_schema=list[Bolum],
            temperature=0.2,
        ),
    )
    sure = time.time() - baslangic

    bolumler = json.loads(yanit.text)
    kullanim = yanit.usage_metadata
    olcumler = {
        "model": MODEL,
        "gecikme_sn": round(sure, 2),
        "girdi_token": kullanim.prompt_token_count,
        "cikti_token": kullanim.candidates_token_count,
    }
    return bolumler, olcumler


def sn_to_dk(sn):
    sn = int(sn)
    return f"{sn // 60:02d}:{sn % 60:02d}"


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