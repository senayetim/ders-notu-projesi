import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import glob
import json
import site
import sys
import time
from functools import lru_cache


def _cuda_dll_yollari_ekle():
    """pip ile kurulan CUDA DLL'lerini Windows'a tanıt."""
    for sp in site.getsitepackages():
        for yol in glob.glob(os.path.join(sp, "nvidia", "*", "bin")):
            os.add_dll_directory(yol)
            os.environ["PATH"] = yol + os.pathsep + os.environ["PATH"]


_cuda_dll_yollari_ekle()

from faster_whisper import WhisperModel


@lru_cache(maxsize=1)  # sonraki dosyalarda model baştan yüklenmesin
def _model_yukle(model_boyutu, cihaz, hesap_tipi):
    print(f"Model yükleniyor: {model_boyutu} ({cihaz})...")
    return WhisperModel(model_boyutu, device=cihaz, compute_type=hesap_tipi)


def _calistir(ses_yolu, model_boyutu, cihaz, hesap_tipi, terimler, ilerleme):
    model = _model_yukle(model_boyutu, cihaz, hesap_tipi)
    print("Model yüklendi, transkripsiyon başlıyor...")
    baslangic = time.time()
    # condition_on_previous_text=False: aynı cümlenin art arda tekrarlanmasını önler
    segments, info = model.transcribe(
        ses_yolu, language="tr", vad_filter=True, condition_on_previous_text=False,
        hotwords=terimler or None,
    )
    parcalar = []
    for s in segments:
        parcalar.append(
            {"baslangic": round(s.start, 2), "bitis": round(s.end, 2), "metin": s.text.strip()}
        )
        print(f"  [{s.start:6.1f}] {s.text.strip()}")
        if ilerleme and info.duration:
            ilerleme(min(s.end / info.duration, 1.0))
    return parcalar, info, time.time() - baslangic


def terimleri_birlestir(metin):
    """Virgül ya da satırla ayrılmış terimleri Whisper'ın beklediği tek metne çevirir."""
    return ", ".join(t.strip() for t in metin.replace("\n", ",").split(",") if t.strip())


def transkript_et(ses_yolu, model_boyutu="medium", terimler="", ilerleme=None):
    """Önce GPU'yu dener, olmazsa CPU'ya düşer."""
    terimler = terimleri_birlestir(terimler)
    try:
        cihaz, tip = "cuda", "int8_float16"
        parcalar, info, sure = _calistir(ses_yolu, model_boyutu, cihaz, tip, terimler, ilerleme)
    except Exception as e:
        print(f"GPU çalışmadı ({e}), CPU'ya geçiliyor...")
        cihaz, tip = "cpu", "int8"
        parcalar, info, sure = _calistir(ses_yolu, model_boyutu, cihaz, tip, terimler, ilerleme)

    return {
        "ses_dosyasi": ses_yolu,
        "model": model_boyutu,
        "cihaz": cihaz,
        "terimler": terimler,
        "ses_suresi_sn": round(info.duration, 1),
        "islem_suresi_sn": round(sure, 1),
        "parcalar": parcalar,
    }


if __name__ == "__main__":
    ses = sys.argv[1] if len(sys.argv) > 1 else "test.mp3"
    sonuc = transkript_et(ses)

    cikti = os.path.splitext(ses)[0] + "_transkript.json"
    with open(cikti, "w", encoding="utf-8") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=2)

    print(f"Model: {sonuc['model']}, cihaz: {sonuc['cihaz']}")
    print(f"Ses süresi: {sonuc['ses_suresi_sn']} sn, işlem süresi: {sonuc['islem_suresi_sn']} sn")
    print(f"{len(sonuc['parcalar'])} parça bulundu. Kaydedildi: {cikti}")