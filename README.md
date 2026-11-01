# Ders Notu Asistanı

Ders kayıtlarını yazıya döken, konulara bölüp özetleyen ve zaman damgasıyla aranabilir hale getiren Streamlit uygulaması. Ses faster-whisper ile yazıya dökülür, bölümleme ve özetleme Gemini ile yapılır.

## Kurulum

Python 3.12 ile denendi.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

NVIDIA ekran kartıyla çalıştırmak için ayrıca `pip install -r requirements-gpu.txt` komutunu çalıştır. GPU yoksa uygulama CPU'ya geçer.

Proje klasöründe bir `.env` dosyası oluştur:

```
GEMINI_API_KEY=anahtarın
```

## Çalıştırma

```powershell
streamlit run app.py
```

İlk çalıştırmada seçilen Whisper modeli indirilir. Sonuçlar `cikti/` klasörüne kaydedilir; aynı dosya aynı modelle tekrar işlenirse kayıtlı sonuç kullanılır.

Adımlar komut satırından da çalıştırılabilir:

```powershell
python transkript.py ders.mp3
python bolumle.py ders_transkript.json
```

## Testler

```powershell
pip install -r requirements-dev.txt
pytest
```
