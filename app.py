import hashlib
import json
from pathlib import Path

import streamlit as st

import anlamsal
import arayuz
from bolumle import MODEL as LLM_MODEL
from bolumle import bolumle, sinirlari_duzelt, sn_to_dk
from calisma import calisma_seti_uret, soru_cevapla
from disari_aktar import notlari_docx, notlari_pdf
from kutuphane import ders_oku, ders_ozeti, dersleri_listele, tum_derslerde_ara
from transkript import transkript_et
from yardimci import bolum_bul, iceriyor, vurgula

st.set_page_config(page_title="EchoNote", page_icon=str(arayuz.LOGO_YOLU), layout="wide")
st.html(arayuz.CSS_YOLU)

YUKLEME_DIZINI = Path("yuklenenler")
CIKTI_DIZINI = Path("cikti")
YUKLEME_DIZINI.mkdir(exist_ok=True)
CIKTI_DIZINI.mkdir(exist_ok=True)

SES_FORMATLARI = {
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
    ".mp4": "audio/mp4", ".ogg": "audio/ogg", ".flac": "audio/flac",
}
ARAMA_SINIRI = 50
ONERILEN_SORULAR = [
    "Bu dersin ana fikri nedir?",
    "Sınavda çıkabilecek noktalar neler?",
    "En önemli kavramları kısaca açıkla.",
]

for anahtar, deger in {
    "transkript": None, "bolumler": [], "olcumler": None, "ses_yol": None,
    "ses_format": "audio/mpeg", "dosya_adi": "", "baslangic_sn": 0, "otomatik": False,
    "oynatma_no": 0, "bolum_hatasi": None, "anahtar": None, "sohbet": [], "quiz_kontrol": False,
    "kart_no": 0, "kart_arka": False, "bekleyen_soru": None,
}.items():
    st.session_state.setdefault(anahtar, deger)


# ---------- Yardımcı fonksiyonlar ----------
def git(sn):
    st.session_state.baslangic_sn = int(sn)
    st.session_state.otomatik = True
    st.session_state.oynatma_no += 1


def notlari_md(dosya_adi, bolumler):
    satirlar = [f"# {dosya_adi}\n"]
    for b in bolumler:
        satirlar.append(f"## [{sn_to_dk(b['baslangic_sn'])} - {sn_to_dk(b['bitis_sn'])}] {b['baslik']}\n")
        satirlar.append(f"{b['ozet']}\n")
        satirlar.append(f"*Anahtar kelimeler:* {', '.join(b['anahtar_kelimeler'])}\n")
    return "\n".join(satirlar)


def transkript_txt(t):
    return "\n".join(f"[{sn_to_dk(p['baslangic'])}] {p['metin']}" for p in t["parcalar"])


@st.cache_data(show_spinner=False)
def word_notlari(dosya_adi, bolumler):
    return notlari_docx(dosya_adi, bolumler)


@st.cache_data(show_spinner=False)
def pdf_notlari(dosya_adi, bolumler):
    return notlari_pdf(dosya_adi, bolumler)


@st.cache_data(show_spinner=False)
def sorgu_vektoru(model, sorgu):
    return anlamsal.sorgu_vektoru(model, sorgu)


def dersi_goster(anahtar, transkript, bolumler, olcumler, hata, ses_yol):
    st.session_state.anahtar = anahtar
    st.session_state.transkript = transkript
    st.session_state.bolumler = bolumler
    st.session_state.olcumler = olcumler
    st.session_state.ses_yol = ses_yol
    st.session_state.ses_format = SES_FORMATLARI.get(Path(ses_yol).suffix.lower(), "audio/mpeg")
    st.session_state.dosya_adi = Path(ses_yol).name
    st.session_state.baslangic_sn = 0
    st.session_state.otomatik = False
    st.session_state.bolum_hatasi = hata
    st.session_state.sohbet = []
    st.session_state.quiz_kontrol = False
    st.session_state.kart_no = 0
    st.session_state.kart_arka = False


def ders_ac(anahtar, sn=None):
    transkript, bolumler, olcumler = ders_oku(CIKTI_DIZINI, anahtar)
    dersi_goster(anahtar, transkript, bolumler, olcumler, None, transkript["ses_dosyasi"])
    if sn is not None:
        git(sn)


def ana_sayfaya_don():
    st.session_state.transkript = None
    st.session_state.anahtar = None


def isle(ses_bayt, dosya_adi, whisper_modeli, yeniden_t, yeniden_b, terimler=""):
    """Kaydı işleyip dersi açar. Transkript üretilemezse False döner."""
    yol = YUKLEME_DIZINI / dosya_adi
    yol.write_bytes(ses_bayt)
    # İçerik özeti anahtara girer: aynı adlı farklı kayıtlar birbirinin sonucunu almasın
    anahtar = f"{yol.stem}_{hashlib.sha256(ses_bayt).hexdigest()[:8]}_{whisper_modeli}"
    t_yol = CIKTI_DIZINI / f"{anahtar}_transkript.json"
    b_yol = CIKTI_DIZINI / f"{anahtar}_bolumler.json"

    bolumler, olcumler, hata = [], None, None
    with st.status("İşleniyor...", expanded=True) as durum:
        if t_yol.exists() and not yeniden_t:
            st.write("Kayıtlı transkript bulundu, Whisper atlanıyor.")
            transkript = json.loads(t_yol.read_text(encoding="utf-8"))
        else:
            st.write("Ses yazıya dökülüyor (ilk seferde model indirilir, lütfen bekle)...")
            cubuk = st.progress(0.0)
            try:
                transkript = transkript_et(
                    str(yol), whisper_modeli, terimler,
                    lambda oran: cubuk.progress(oran, f"%{int(oran * 100)}"),
                )
            except Exception as e:
                durum.update(label="Transkript üretilemedi", state="error", expanded=True)
                st.error(f"Ses yazıya dökülemedi: {e}")
                return False
            t_yol.write_text(json.dumps(transkript, ensure_ascii=False, indent=2), encoding="utf-8")
            b_yol.unlink(missing_ok=True)  # eski bölümlerin zamanları yeni transkripte uymaz

        if b_yol.exists() and not yeniden_b:
            st.write("Kayıtlı bölümleme bulundu, Gemini atlanıyor.")
            kayit = json.loads(b_yol.read_text(encoding="utf-8"))
            bolumler = sinirlari_duzelt(kayit["bolumler"], transkript["ses_suresi_sn"])
            olcumler = kayit["olcumler"]
        else:
            st.write("Konulara bölünüyor (Gemini)...")
            try:
                bolumler, olcumler = bolumle(transkript)
                b_yol.write_text(
                    json.dumps({"bolumler": bolumler, "olcumler": olcumler}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception as e:
                hata = str(e)
                st.error(f"Bölümleme başarısız oldu: {e}")
        durum.update(label="Hazır", state="complete", expanded=bool(hata))

    dersi_goster(anahtar, transkript, bolumler, olcumler, hata, str(yol))
    return True


# ---------- Kenar çubuğu ----------
def kenar_cubugu(dersler):
    with st.sidebar:
        st.html(arayuz.marka())
        acik = st.session_state.anahtar
        st.button(
            "Ana sayfa", icon=":material/home:", key="yan_ana", on_click=ana_sayfaya_don,
            type="primary" if not acik else "tertiary", width="stretch",
        )
        if dersler:
            st.html('<p class="yan-etiket">Dersler</p>')
            for i, d in enumerate(dersler):
                st.button(
                    d["ad"], key=f"yan_ders_{i}", on_click=ders_ac, args=(d["anahtar"],),
                    type="primary" if d["anahtar"] == acik else "tertiary", width="stretch",
                )
        kullanilan = st.session_state.olcumler
        model = kullanilan["model"] if kullanilan else LLM_MODEL
        


# ---------- Ana sayfa ----------
def ana_sayfa(dersler):
    ozetler = [ders_ozeti(CIKTI_DIZINI, d) for d in dersler]
    toplam_sn = sum(o["sure_sn"] for o in ozetler)
    toplam_bolum = sum(o["bolum_sayisi"] for o in ozetler)

    sol, sag = st.columns([1.1, 1], gap="large", vertical_alignment="center")
    sol.html(arayuz.hero(len(ozetler), toplam_sn, toplam_bolum))
    with sag.container(key="yukleme"):
        yuklenen = st.file_uploader(
            "Yeni ders kaydı", type=["mp3", "wav", "m4a", "mp4", "ogg", "flac"],
        )
        with st.expander("Gelişmiş ayarlar", icon=":material/tune:"):
            whisper_modeli = st.selectbox(
                "Whisper modeli", ["small", "medium", "large-v3"], index=1,
                help="Büyük model daha doğru ama daha yavaş çalışır.",
            )
            terimler = st.text_area(
                "Özel terimler", placeholder="tımar, ikta, Karahanlılar", height=80,
                help="Virgülle ayır. Whisper bu kelimeleri daha doğru yazar. "
                     "Daha önce işlenmiş kayıtlarda 'Transkripti yeniden üret' seçeneğini de işaretle.",
            )
            yeniden_t = st.checkbox("Transkripti yeniden üret")
            yeniden_b = st.checkbox("Bölümlemeyi yeniden üret")
        if yuklenen and st.button("Dersi işle", type="primary", width="stretch"):
            if isle(yuklenen.getvalue(), yuklenen.name, whisper_modeli, yeniden_t, yeniden_b, terimler):
                st.rerun()

    st.space("small")
    if not ozetler:
        st.html(arayuz.adimlar())
        return

    baslik, arama = st.columns([1.1, 1], gap="large", vertical_alignment="bottom")
    baslik.html('<p class="alt-baslik">Kütüphanen</p>')
    sorgu = arama.text_input(
        "Tüm derslerde ara", placeholder="Tüm derslerde ara: tımar, ikta...", label_visibility="collapsed",
    ).strip()
    if sorgu:
        tum_derslerde(sorgu)
        return

    for sira in range(0, len(ozetler), 3):
        for kolon, ozet, no in zip(st.columns(3), ozetler[sira:sira + 3], range(sira, sira + 3)):
            with kolon.container(key=f"ders-kart-{no}"):
                st.html(arayuz.ders_karti(ozet))
                st.button("Dersi aç", key=f"ac_{no}", on_click=ders_ac, args=(ozet["anahtar"],), width="stretch")


# ---------- Ders sayfası ----------
def bolumler_sekmesi(t, bolumler):
    if not bolumler:
        if st.session_state.bolum_hatasi:
            st.error(f"Bölümleme hatası: {st.session_state.bolum_hatasi}")
        else:
            st.html(arayuz.bos_durum("Bu derste bölüm yok", "Kaydı yeniden işleyerek bölümleri üretebilirsin."))
        return

    st.html(arayuz.zaman_seridi(bolumler, t["ses_suresi_sn"]))
    d1, d2, d3, _ = st.columns([1, 1, 1, 1.6])
    d1.download_button(
        "Markdown", icon=":material/download:", width="stretch",
        data=notlari_md(st.session_state.dosya_adi, bolumler),
        file_name="ders_notlari.md", mime="text/markdown",
    )
    d2.download_button(
        "Word", icon=":material/download:", width="stretch",
        data=word_notlari(st.session_state.dosya_adi, bolumler),
        file_name="ders_notlari.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    pdf = pdf_notlari(st.session_state.dosya_adi, bolumler)
    if pdf:
        d3.download_button(
            "PDF", icon=":material/download:", width="stretch",
            data=pdf, file_name="ders_notlari.pdf", mime="application/pdf",
        )

    caliniyor = bolum_bul(bolumler, st.session_state.baslangic_sn) if st.session_state.otomatik else None
    for i, b in enumerate(bolumler):
        with st.container(key=f"bolum-kart-{i}"):
            sol, sag = st.columns([6, 1.1])
            sol.html(arayuz.bolum_karti(i, b, bool(caliniyor) and caliniyor[0] == i))
            sag.button(
                "Oynat", icon=":material/play_arrow:", key=f"bolum_{i}",
                on_click=git, args=(b["baslangic_sn"],), width="stretch",
            )


def kart_cevir():
    st.session_state.kart_arka = not st.session_state.kart_arka


def kart_git(adim, toplam):
    st.session_state.kart_no = (st.session_state.kart_no + adim) % toplam
    st.session_state.kart_arka = False


def calisma_sekmesi(t, anahtar):
    yol = CIKTI_DIZINI / f"{anahtar}_calisma.json"
    seti = json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else None

    if not seti:
        st.html(arayuz.bos_durum(
            "Kendini sınamaya hazır mısın?",
            "Bu dersten çoktan seçmeli sorular ve bilgi kartları üretelim. Her biri dersin ilgili anına bağlıdır.",
        ))
        st.space("small")
    _, orta, _ = st.columns([1.3, 1, 1.3]) if not seti else (None, st.container(), None)
    etiket = "Quiz ve kartları üret" if not seti else "Yeni set üret"
    if orta.button(etiket, key="calisma_uret", type="secondary" if seti else "primary", width="stretch" if not seti else "content"):
        try:
            with st.spinner("Çalışma seti hazırlanıyor..."):
                seti = calisma_seti_uret(t)
            yol.write_text(json.dumps(seti, ensure_ascii=False, indent=2), encoding="utf-8")
            for i in range(len(seti["sorular"])):
                st.session_state.pop(f"q_{anahtar}_{i}", None)
            st.session_state.quiz_kontrol = False
            st.session_state.kart_no = 0
            st.session_state.kart_arka = False
        except Exception as e:
            st.error(f"Çalışma seti üretilemedi: {e}")
    if not seti:
        return

    sekme_q, sekme_k = st.tabs([f"Quiz ({len(seti['sorular'])})", f"Bilgi kartları ({len(seti['kartlar'])})"])
    with sekme_q:
        quiz_gorunumu(seti["sorular"], anahtar)
    with sekme_k:
        kart_gorunumu(seti["kartlar"])


def quiz_gorunumu(sorular, anahtar):
    with st.container(key=f"quiz-{anahtar}"):
        with st.form(f"quiz_formu_{anahtar}"):
            secimler = [
                st.radio(
                    f"{i + 1}. {q['soru']}",
                    range(len(q["secenekler"])),
                    format_func=lambda n, q=q: q["secenekler"][n],
                    index=None,
                    key=f"q_{anahtar}_{i}",
                )
                for i, q in enumerate(sorular)
            ]
            if st.form_submit_button("Cevapları kontrol et", type="primary"):
                st.session_state.quiz_kontrol = True

    if st.session_state.quiz_kontrol:
        dogru = sum(s == q["dogru_indeks"] for s, q in zip(secimler, sorular))
        cevaplanan = sum(s is not None for s in secimler)
        st.html(arayuz.skor(dogru, len(sorular), cevaplanan))
        for i, (secim, q) in enumerate(zip(secimler, sorular)):
            with st.container(key=f"sonuc-{i}"):
                sol, sag = st.columns([6, 1.1], vertical_alignment="center")
                sol.html(arayuz.quiz_sonucu(
                    i + 1, secim == q["dogru_indeks"], q["secenekler"][q["dogru_indeks"]], q["aciklama"],
                ))
                sag.button(
                    "Dinle", icon=":material/play_arrow:", key=f"quiz_oynat_{i}",
                    on_click=git, args=(q["kaynak_sn"],), width="stretch",
                )


def kart_gorunumu(kartlar):
    toplam = len(kartlar)
    no = st.session_state.kart_no % toplam
    kart = kartlar[no]
    arka = st.session_state.kart_arka
    st.html(arayuz.bilgi_karti(kart["arka"] if arka else kart["on"], no + 1, toplam, arka))
    st.space("small")
    _, g, c, d, o, _ = st.columns([0.6, 1, 1.2, 1, 1, 0.6])
    g.button("Önceki", icon=":material/arrow_back:", key="kart_geri", on_click=kart_git, args=(-1, toplam), width="stretch")
    c.button("Cevabı gör" if not arka else "Soruya dön", key="kart_cevir", type="primary", on_click=kart_cevir, width="stretch")
    d.button("Sonraki", icon=":material/arrow_forward:", key="kart_ileri", on_click=kart_git, args=(1, toplam), width="stretch")
    o.button(
        sn_to_dk(kart["kaynak_sn"]), icon=":material/play_arrow:", key="kart_oynat",
        on_click=git, args=(kart["kaynak_sn"],), width="stretch", help="Dersin bu anını dinle",
    )


def soru_sec(soru):
    st.session_state.bekleyen_soru = soru


def soru_sekmesi(t):
    with st.form("soru_formu", clear_on_submit=True):
        sol, sag = st.columns([6, 1], vertical_alignment="bottom")
        yazilan = sol.text_input(
            "Derse dair sorun", placeholder="Derste anlamadığın bir şeyi sor...", label_visibility="collapsed",
        )
        gonderildi = sag.form_submit_button("Sor", type="primary", width="stretch")

    soru = st.session_state.bekleyen_soru or (yazilan.strip() if gonderildi else "")
    st.session_state.bekleyen_soru = None
    if soru:
        try:
            with st.spinner("Transkript taranıyor..."):
                cevap = soru_cevapla(t, soru)
            st.session_state.sohbet.insert(0, {"soru": soru, **cevap})
        except Exception as e:
            st.error(f"Soru cevaplanamadı: {e}")

    if not st.session_state.sohbet:
        st.html('<p class="kaynak-etiketi">Cevaplar yalnızca bu dersin transkriptine dayanır. Başlamak için bir öneri seç:</p>')
        for kolon, oneri, i in zip(st.columns(3), ONERILEN_SORULAR, range(3)):
            kolon.button(oneri, key=f"oneri_{i}", on_click=soru_sec, args=(oneri,), width="stretch")

    toplam = len(st.session_state.sohbet)
    for i, kayit in enumerate(st.session_state.sohbet):
        st.html(arayuz.baloncuk(kayit["soru"], "soru"))
        st.html(arayuz.baloncuk(kayit["cevap"], "cevap" if kayit["bulundu"] else "yok"))
        if kayit["kaynak_sn"]:
            for kolon, sn in zip(st.columns([1, 1, 1, 3]), kayit["kaynak_sn"]):
                kolon.button(
                    sn_to_dk(sn), icon=":material/play_arrow:", key=f"soru_{toplam - i}_{sn}",
                    on_click=git, args=(sn,), width="stretch",
                )
        st.space("small")


def sonuc_satiri(sira, zaman, govde, dugme_etiketi, on_click, args):
    with st.container(key=f"sonuc-kart-{sira}"):
        c1, c2, c3 = st.columns([0.9, 6, 1.2], vertical_alignment="center")
        c1.html(f'<span class="zaman">{sn_to_dk(zaman)}</span>')
        c2.html(govde)
        c3.button(dugme_etiketi, icon=":material/play_arrow:", key=f"dugme_{sira}", on_click=on_click, args=args, width="stretch")


def sonuc_sayisi(sonuclar):
    if not sonuclar:
        st.html(arayuz.bos_durum("Sonuç bulunamadı", "Farklı bir kelime dene ya da anlama göre aramayı kullan."))
        return
    ek = f" (ilk {ARAMA_SINIRI} gösteriliyor)" if len(sonuclar) > ARAMA_SINIRI else ""
    st.html(f'<p class="kaynak-etiketi">{len(sonuclar)} sonuç{ek}</p>')


def bu_derste_ara(t, bolumler, sorgu):
    sonuclar = [p for p in t["parcalar"] if iceriyor(p["metin"], sorgu)]
    sonuc_sayisi(sonuclar)
    for i, p in enumerate(sonuclar[:ARAMA_SINIRI]):
        bulunan = bolum_bul(bolumler, p["baslangic"])
        rozet = (bulunan[1]["baslik"], arayuz.renk(bulunan[0])) if bulunan else None
        govde = arayuz.bulunan(vurgula(p["metin"], sorgu), rozet=rozet)
        sonuc_satiri(f"bu-{i}", p["baslangic"], govde, "Oynat", git, (p["baslangic"],))


def tum_derslerde(sorgu):
    sonuclar = tum_derslerde_ara(CIKTI_DIZINI, sorgu)
    sonuc_sayisi(sonuclar)
    for i, p in enumerate(sonuclar[:ARAMA_SINIRI]):
        govde = arayuz.bulunan(vurgula(p["metin"], sorgu), kaynak=p["ad"])
        sonuc_satiri(f"tum-{i}", p["baslangic"], govde, "Aç", ders_ac, (p["anahtar"], p["baslangic"]))


def anlama_gore_ara(t, anahtar, sorgu):
    yol = CIKTI_DIZINI / f"{anahtar}_gomme.npz"
    if not yol.exists():
        st.html(arayuz.bos_durum(
            "Anlamsal arama hazır değil",
            "Kelimesi birebir geçmese de anlamca yakın yerleri bulmak için ders bir kez hazırlanır.",
        ))
        st.space("small")
        _, orta, _ = st.columns([1.3, 1, 1.3])
        if not orta.button("Anlamsal aramayı hazırla", key="dizin_hazirla", type="primary", width="stretch"):
            return
        try:
            with st.spinner("Hazırlanıyor..."):
                anlamsal.dizin_kaydet(yol, anlamsal.dizin_olustur(t))
        except Exception as e:
            st.error(f"Anlamsal arama hazırlanamadı: {e}")
            return

    if not sorgu:
        st.html('<p class="kaynak-etiketi">Yukarıya bir kavram ya da cümle yaz; en yakın 5 yeri getirelim.</p>')
        return
    try:
        dizin = anlamsal.dizin_oku(yol)
        sonuclar = anlamsal.en_benzerler(dizin, sorgu_vektoru(dizin["model"], sorgu))
    except Exception as e:
        st.error(f"Arama yapılamadı: {e}")
        return
    st.html('<p class="kaynak-etiketi">Anlamca en yakın 5 yer</p>')
    for i, p in enumerate(sonuclar):
        sonuc_satiri(f"an-{i}", p["baslangic"], arayuz.bulunan(vurgula(p["metin"], "")), "Oynat", git, (p["baslangic"],))


def arama_sekmesi(t, bolumler, anahtar):
    sorgu = st.text_input(
        "Ne arıyorsun?", placeholder="Ne arıyorsun? Örn. tımar, ordu, toprak sistemi", label_visibility="collapsed",
    ).strip()
    kapsam = st.segmented_control(
        "Arama türü", ["Bu derste", "Tüm derslerde", "Anlama göre"], default="Bu derste",
        label_visibility="collapsed",
    ) or "Bu derste"
    if kapsam == "Anlama göre":
        anlama_gore_ara(t, anahtar, sorgu)
    elif not sorgu:
        st.html('<p class="kaynak-etiketi">Bir kelime yaz; geçtiği yerleri zaman damgasıyla listeleyelim. Türkçe karakter farkı önemsenmez.</p>')
    elif kapsam == "Bu derste":
        bu_derste_ara(t, bolumler, sorgu)
    else:
        tum_derslerde(sorgu)


def transkript_sekmesi(t, bolumler):
    st.download_button(
        "Transkripti indir", icon=":material/download:",
        data=transkript_txt(t), file_name="transkript.txt", mime="text/plain",
    )
    st.html(arayuz.transkript_okuma(t["parcalar"], bolumler))


def ders_sayfasi(t, dersler):
    bolumler = st.session_state.bolumler
    anahtar = st.session_state.anahtar
    ad = next((d["ad"] for d in dersler if d["anahtar"] == anahtar), st.session_state.dosya_adi)

    st.button("Tüm dersler", icon=":material/arrow_back:", key="geri", on_click=ana_sayfaya_don, type="tertiary")
    st.html(arayuz.ders_basligi(ad, t, len(bolumler)))

    if Path(st.session_state.ses_yol).exists():
        with st.container(key="oynatici"):
            bulunan = bolum_bul(bolumler, st.session_state.baslangic_sn)
            st.html(arayuz.simdi_caliniyor(st.session_state.baslangic_sn, bulunan[1] if bulunan else None))
            # Oynatıcı aynı başlangıca tekrar sarmaz; alt değişince yeniden kurulup baştan çalar
            st.audio(
                st.session_state.ses_yol,
                format=st.session_state.ses_format,
                start_time=st.session_state.baslangic_sn,
                autoplay=st.session_state.otomatik,
                alt=f"Ders kaydı {st.session_state.oynatma_no}",
            )
    else:
        st.warning("Bu dersin ses dosyası bulunamadı; notlar açık ama dinleme düğmeleri çalışmaz.")

    sekmeler = st.tabs(["Bölümler", "Çalış", "Soru sor", "Arama", "Transkript"])
    with sekmeler[0]:
        bolumler_sekmesi(t, bolumler)
    with sekmeler[1]:
        calisma_sekmesi(t, anahtar)
    with sekmeler[2]:
        soru_sekmesi(t)
    with sekmeler[3]:
        arama_sekmesi(t, bolumler, anahtar)
    with sekmeler[4]:
        transkript_sekmesi(t, bolumler)


# ---------- Sayfa seçimi ----------
dersler = dersleri_listele(CIKTI_DIZINI)
kenar_cubugu(dersler)
t = st.session_state.transkript
if t:
    ders_sayfasi(t, dersler)
else:
    ana_sayfa(dersler)
