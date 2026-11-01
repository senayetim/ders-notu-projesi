import numpy as np
from google import genai
from google.genai import errors, types

# Sırayla denenir. Farklı modellerin vektörleri karışamaz, bu yüzden dizinle birlikte model de saklanır.
GOMME_MODELLERI = ["gemini-embedding-2", "gemini-embedding-001"]
PARCA_HEDEF_SN = 45
GRUP_BOYUTU = 100


def parcalari_birlestir(parcalar, hedef_sn=PARCA_HEDEF_SN):
    """Kısa transkript parçalarını anlamı taşıyacak uzunlukta bloklara toplar."""
    bloklar = []
    for p in parcalar:
        if bloklar and p["bitis"] - bloklar[-1]["baslangic"] <= hedef_sn:
            bloklar[-1]["metin"] += " " + p["metin"]
        else:
            bloklar.append({"baslangic": p["baslangic"], "metin": p["metin"]})
    return bloklar


def _normalize(vektorler):
    return vektorler / np.linalg.norm(vektorler, axis=-1, keepdims=True)


def _gom(istemci, model, metinler, gorev):
    vektorler = []
    for i in range(0, len(metinler), GRUP_BOYUTU):
        # Her metin ayrı Content olmalı: düz liste verilirse gemini-embedding-2 hepsini tek vektörde birleştirir
        grup = [types.Content(parts=[types.Part(text=m)]) for m in metinler[i:i + GRUP_BOYUTU]]
        yanit = istemci.models.embed_content(
            model=model,
            contents=grup,
            config=types.EmbedContentConfig(task_type=gorev),
        )
        if len(yanit.embeddings) != len(grup):
            raise RuntimeError(f"{len(grup)} metin için {len(yanit.embeddings)} vektör döndü")
        vektorler += [e.values for e in yanit.embeddings]
    return _normalize(np.array(vektorler, dtype=np.float32))


def dizin_olustur(transkript):
    """Transkripti anlamsal aramaya hazırlar."""
    bloklar = parcalari_birlestir(transkript["parcalar"])
    metinler = [b["metin"] for b in bloklar]
    istemci = genai.Client()
    hatalar = []
    for model in GOMME_MODELLERI:
        try:
            vektorler = _gom(istemci, model, metinler, "RETRIEVAL_DOCUMENT")
            return {
                "model": model,
                "baslangic": np.array([b["baslangic"] for b in bloklar]),
                "metin": np.array(metinler),
                "vektor": vektorler,
            }
        except errors.APIError as e:
            hatalar.append(f"{model}: {e.code}")
        except RuntimeError as e:
            hatalar.append(f"{model}: {e}")
    raise RuntimeError("Hiçbir gömme modeli yanıt veremedi: " + " | ".join(hatalar))


def dizin_kaydet(yol, dizin):
    np.savez(yol, **dizin)


def dizin_oku(yol):
    with np.load(yol) as veri:
        return {
            "model": str(veri["model"]),
            "baslangic": veri["baslangic"],
            "metin": veri["metin"],
            "vektor": veri["vektor"],
        }


def sorgu_vektoru(model, sorgu):
    return _gom(genai.Client(), model, [sorgu], "RETRIEVAL_QUERY")[0]


def en_benzerler(dizin, vektor, adet=5):
    """Sorguya anlamca en yakın blokları benzerlik sırasıyla döner."""
    benzerlik = dizin["vektor"] @ vektor
    sira = np.argsort(benzerlik)[::-1][:adet]
    return [
        {
            "baslangic": float(dizin["baslangic"][i]),
            "metin": str(dizin["metin"][i]),
            "benzerlik": float(benzerlik[i]),
        }
        for i in sira
    ]
