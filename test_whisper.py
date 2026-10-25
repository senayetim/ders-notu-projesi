import time
from faster_whisper import WhisperModel

# Model: "small" orta boy, işlemcide (CPU) rahat çalışır
model = WhisperModel("small", device="cpu", compute_type="int8")

baslangic = time.time()
segments, info = model.transcribe("test.mp3", language="tr")

print(f"Algılanan dil: {info.language}, ses süresi: {info.duration:.1f} sn\n")

for seg in segments:
    print(f"[{seg.start:7.1f} -> {seg.end:7.1f}] {seg.text}")

print(f"\nToplam işlem süresi: {time.time() - baslangic:.1f} sn")