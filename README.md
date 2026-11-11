# EchoNote

Ders kayıtlarını yazıya döken, konulara bölüp özetleyen ve zaman damgasıyla aranabilir hale getiren Streamlit uygulaması. Ses faster-whisper ile yazıya dökülür, bölümleme ve özetleme Gemini ile yapılır.

## Özellikler

- **Bölümler:** Konu başlıkları, özetler, anahtar kelimeler. Notlar `.md`, `.docx` ve `.pdf` olarak indirilebilir.
- **Kütüphane:** İşlenen dersler yan menüden yeniden yüklemeden açılır.
- **Çalış:** Dersten quiz ve bilgi kartları üretilir, her biri kaynağı olan saniyeye bağlıdır.
- **Soru sor:** Cevaplar yalnızca transkripte dayanır ve zaman damgalı kaynakla gelir.
- **Arama:** Bu derste, tüm derslerde ya da anlama göre (kelime birebir geçmese de) arama.
- **Özel terimler:** Derse özgü kelimeler Whisper'a verilerek doğru yazılması sağlanır.

Arayüzün görünümü `assets/stil.css`, HTML parçaları `arayuz.py` dosyasındadır. Yazı tipleri Google Fonts'tan yüklenir; internet yoksa sistem yazı tipleri kullanılır.

Quiz, soru sorma ve anlamsal arama Gemini API'sini kullanır. PDF çıktısı için Türkçe harfleri içeren bir sistem yazı tipi gerekir (Arial ya da DejaVu Sans).

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

## Docker ile çalıştırma

Başka bir bilgisayarda Python kurmadan çalıştırmak için yalnızca [Docker Desktop](https://www.docker.com/products/docker-desktop/) gerekir.

1. Projeyi kopyala ve klasörde yukarıdaki gibi bir `.env` dosyası oluştur.
2. Çalıştır:

   ```powershell
   docker compose up -d --build
   ```

3. Tarayıcıda http://localhost:8501 adresini aç.

Durdurmak için `docker compose down`. `cikti/` ve `yuklenenler/` klasörleri konteynere bağlanır; işlenen dersler bilgisayarda kalır ve başka bir bilgisayara bu klasörler kopyalanarak taşınabilir. İndirilen Whisper modelleri `modeller` adlı Docker volume'unda saklanır, her açılışta yeniden inmez.

Konteyner Whisper'ı CPU'da çalıştırır.

## Testler

```powershell
pip install -r requirements-dev.txt
pytest
```
