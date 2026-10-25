import html
import json
from pathlib import Path

import streamlit as st

from bolumle import MODEL as LLM_MODEL
from bolumle import bolumle, sn_to_dk
from transkript import transkript_et

st.set_page_config(page_title="Ders Notu Asistanı", page_icon="🎓", layout="wide")

YUKLEME_DIZINI = Path("yuklenenler")
CIKTI_DIZINI = Path("cikti")
YUKLEME_DIZINI.mkdir(exist_ok=True)
CIKTI_DIZINI.mkdir(exist_ok=True)

SES_FORMATLARI = {
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
    ".mp4": "audio/mp4", ".ogg": "audio/ogg", ".flac": "audio/flac",
}
RENKLER = ["#4F46E5", "#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"]

st.markdown(
    """
    <style>
    .block-container {padding-top: 2.2rem; max-width: 1100px;}
    .hero-baslik {font-size: 2.2rem; font-weight: 800; margin: 0; color: #1F2937;}
    .hero-alt {color: #6B7280; margin: 4px 0 18px 0;}
    .rozet {display: inline-block; padding: 2px 10px; border-radius: 999px;
            font-size: 0.8rem; font-weight: 600; color: white;}
    .etiket {display: inline-block; padding: 1px 9px; margin: 2px 4px 0 0;
             border-radius: 6px; font-size: 0.78rem; background: #EEF0FB; color: #4338CA;}
    .bolum-baslik {font-size: 1.05rem; font-weight: 700; margin-left: 6px;}
    </style>
    """,
    unsafe_allow_html=True,
)

for anahtar, deger in {
    "transkript": None, "bolumler": [], "olcumler": None, "ses_bayt": None,
    "ses_format": "audio/mpeg", "dosya_adi": "", "baslangic_sn": 0, "otomatik": False,
    "bolum_hatasi": None,
}.items():
    st.session_state.setdefault(anahtar, deger)


# ---------- Yardımcı fonksiyonlar ----------
def sadelestir(metin):
    """Küçük harfe çevirir ve Türkçe karakterleri sadeleştirir (arama için)."""
    metin = metin.replace("İ", "i").replace("I", "ı").lower()
    return metin.translate(str.maketrans("çğıöşü", "cgiosu"))


def vurgula(metin, sorgu):
    m, s = sadelestir(metin), sadelestir(sorgu)
    if not s:
        return metin
    sonuc, i = "", 0
    while True:
        j = m.find(s, i)
        if j == -1:
            return sonuc + metin[i:]
        sonuc += metin[i:j] + "**" + metin[j:j + len(s)] + "**"
        i = j + len(s)


def bolum_bul(bolumler, sn):
    """Verilen saniyenin hangi bölümde olduğunu (sıra, bölüm) olarak döner."""
    for i, b in enumerate(bolumler):
        if b["baslangic_sn"] <= sn < b["bitis_sn"]:
            return i, b
    return None


def git(sn):
    st.session_state.baslangic_sn = int(sn)
    st.session_state.otomatik = True


def rozet(metin, renk):
    return f'<span class="rozet" style="background:{renk}">{html.escape(metin)}</span>'


def zaman_cizelgesi(bolumler, toplam_sn):
    if not toplam_sn:
        return
    parcalar = ""
    for i, b in enumerate(bolumler):
        genislik = max((b["bitis_sn"] - b["baslangic_sn"]) / toplam_sn * 100, 0.5)
        ipucu = html.escape(f"{sn_to_dk(b['baslangic_sn'])} · {b['baslik']}")
        parcalar += (
            f'<div title="{ipucu}" style="width:{genislik}%;'
            f'background:{RENKLER[i % len(RENKLER)]};height:14px"></div>'
        )
    st.markdown(
        f'<div style="display:flex;border-radius:8px;overflow:hidden;margin:6px 0 18px 0">{parcalar}</div>',
        unsafe_allow_html=True,
    )


def notlari_md(dosya_adi, bolumler):
    satirlar = [f"# {dosya_adi}\n"]
    for b in bolumler:
        satirlar.append(f"## [{sn_to_dk(b['baslangic_sn'])} - {sn_to_dk(b['bitis_sn'])}] {b['baslik']}\n")
        satirlar.append(f"{b['ozet']}\n")
        satirlar.append(f"*Anahtar kelimeler:* {', '.join(b['anahtar_kelimeler'])}\n")
    return "\n".join(satirlar)


def transkript_txt(t):
    return "\n".join(f"[{sn_to_dk(p['baslangic'])}] {p['metin']}" for p in t["parcalar"])


def isle(ses_bayt, dosya_adi, whisper_modeli, yeniden_t, yeniden_b):
    yol = YUKLEME_DIZINI / dosya_adi
    yol.write_bytes(ses_bayt)
    anahtar = f"{yol.stem}_{whisper_modeli}"
    t_yol = CIKTI_DIZINI / f"{anahtar}_transkript.json"
    b_yol = CIKTI_DIZINI / f"{anahtar}_bolumler.json"

    bolumler, olcumler, hata = [], None, None
    with st.status("İşleniyor...", expanded=True) as durum:
        if t_yol.exists() and not yeniden_t:
            st.write("Kayıtlı transkript bulundu, Whisper atlanıyor.")
            transkript = json.loads(t_yol.read_text(encoding="utf-8"))
        else:
            st.write("Ses yazıya dökülüyor (ilk seferde model indirilir, lütfen bekle)...")
            transkript = transkript_et(str(yol), whisper_modeli)
            t_yol.write_text(json.dumps(transkript, ensure_ascii=False, indent=2), encoding="utf-8")

        if b_yol.exists() and not yeniden_b:
            st.write("Kayıtlı bölümleme bulundu, Gemini atlanıyor.")
            kayit = json.loads(b_yol.read_text(encoding="utf-8"))
            bolumler, olcumler = kayit["bolumler"], kayit["olcumler"]
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

    st.session_state.transkript = transkript
    st.session_state.bolumler = bolumler
    st.session_state.olcumler = olcumler
    st.session_state.ses_bayt = ses_bayt
    st.session_state.ses_format = SES_FORMATLARI.get(Path(dosya_adi).suffix.lower(), "audio/mpeg")
    st.session_state.dosya_adi = dosya_adi
    st.session_state.baslangic_sn = 0
    st.session_state.otomatik = False
    st.session_state.bolum_hatasi = hata


# ---------- Kenar çubuğu ----------
with st.sidebar:
    st.header("Ayarlar")
    whisper_modeli = st.selectbox(
        "Whisper modeli", ["small", "medium", "large-v3"], index=1,
        help="Büyük model daha doğru ama daha yavaş çalışır.",
    )
    yeniden_t = st.checkbox("Transkripti yeniden üret")
    yeniden_b = st.checkbox("Bölümlemeyi yeniden üret")
    st.divider()
    st.caption(f"Özetleme modeli: {LLM_MODEL}")
    st.caption("Ses → yazı: faster-whisper")

# ---------- Başlık ----------
st.markdown('<p class="hero-baslik">🎓 Ders Notu Asistanı</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-alt">Ders kaydını yükle; yazıya dökelim, konulara bölelim, zaman damgasıyla arayalım.</p>',
    unsafe_allow_html=True,
)

yuklenen = st.file_uploader("Ses dosyası", type=["mp3", "wav", "m4a", "mp4", "ogg", "flac"])
if yuklenen and st.button("İşle", type="primary"):
    isle(yuklenen.getvalue(), yuklenen.name, whisper_modeli, yeniden_t, yeniden_b)

t = st.session_state.transkript

# ---------- Boş durum ----------
if not t:
    st.write("")
    c1, c2, c3 = st.columns(3)
    for kolon, no, baslik, aciklama in [
        (c1, "1", "Yükle", "Ders kaydını (mp3, wav, m4a, mp4) sürükle ya da seç."),
        (c2, "2", "İşle", "Whisper sesi yazıya döker, yapay zekâ konulara böler."),
        (c3, "3", "Keşfet", "Bölümlere göz at, kelime ara, tıklayınca o saniyeden dinle."),
    ]:
        with kolon.container(border=True):
            st.markdown(f"**{no}. {baslik}**")
            st.caption(aciklama)

# ---------- Sonuçlar ----------
else:
    st.divider()
    bolumler = st.session_state.bolumler
    st.caption(f"📁 {st.session_state.dosya_adi}")
    st.audio(
        st.session_state.ses_bayt,
        format=st.session_state.ses_format,
        start_time=st.session_state.baslangic_sn,
        autoplay=st.session_state.otomatik,
    )

    sekme_b, sekme_a, sekme_t, sekme_o = st.tabs(["Bölümler", "Arama", "Tam transkript", "Ölçümler"])

    # --- Bölümler ---
    with sekme_b:
        if not bolumler:
            if st.session_state.bolum_hatasi:
                st.error(f"Bölümleme hatası: {st.session_state.bolum_hatasi}")
            else:
                st.info("Bölüm bilgisi yok.")
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric("Süre", sn_to_dk(t["ses_suresi_sn"]))
            m2.metric("Bölüm sayısı", len(bolumler))
            m3.metric("Cümle sayısı", len(t["parcalar"]))

            zaman_cizelgesi(bolumler, t["ses_suresi_sn"])

            st.download_button(
                "⬇ Notları indir (.md)",
                data=notlari_md(st.session_state.dosya_adi, bolumler),
                file_name="ders_notlari.md",
                mime="text/markdown",
            )

            for i, b in enumerate(bolumler):
                renk = RENKLER[i % len(RENKLER)]
                aralik = f"{sn_to_dk(b['baslangic_sn'])} – {sn_to_dk(b['bitis_sn'])}"
                with st.container(border=True):
                    sol, sag = st.columns([6, 1.2])
                    sol.markdown(
                        f'{rozet(aralik, renk)}<span class="bolum-baslik">{html.escape(b["baslik"])}</span>',
                        unsafe_allow_html=True,
                    )
                    sag.button("▶ Oynat", key=f"bolum_{i}", on_click=git, args=(b["baslangic_sn"],))
                    st.write(b["ozet"])
                    etiketler = "".join(f'<span class="etiket">{html.escape(k)}</span>' for k in b["anahtar_kelimeler"])
                    st.markdown(etiketler, unsafe_allow_html=True)

    # --- Arama ---
    with sekme_a:
        sorgu = st.text_input("Ne arıyorsun?", placeholder="örn. koyun, resim, küçük prens")
        if sorgu.strip():
            s = sadelestir(sorgu.strip())
            sonuclar = [p for p in t["parcalar"] if s in sadelestir(p["metin"])]
            st.write(f"**{len(sonuclar)}** sonuç bulundu.")
            for i, p in enumerate(sonuclar[:50]):
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1, 6, 1.4])
                    c1.markdown(f"**{sn_to_dk(p['baslangic'])}**")
                    c2.markdown(vurgula(p["metin"], sorgu.strip()))
                    bulunan = bolum_bul(bolumler, p["baslangic"])
                    if bulunan:
                        idx, bolum = bulunan
                        c2.markdown(
                            rozet(bolum["baslik"], RENKLER[idx % len(RENKLER)]),
                            unsafe_allow_html=True,
                        )
                    c3.button("▶ Oynat", key=f"ara_{i}", on_click=git, args=(p["baslangic"],))
            if len(sonuclar) > 50:
                st.caption("İlk 50 sonuç gösteriliyor.")
        else:
            st.caption("Bir kelime yaz; geçtiği yerleri zaman damgasıyla listeleyelim. Türkçe karakter farkı önemsenmez.")

    # --- Tam transkript ---
    with sekme_t:
        st.download_button(
            "⬇ Transkripti indir (.txt)",
            data=transkript_txt(t),
            file_name="transkript.txt",
            mime="text/plain",
        )
        st.dataframe(
            [{"Zaman": sn_to_dk(p["baslangic"]), "Metin": p["metin"]} for p in t["parcalar"]],
            hide_index=True,
            use_container_width=True,
        )

    # --- Ölçümler ---
    with sekme_o:
        st.subheader("Ses → yazı (Whisper)")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Model / cihaz", f"{t['model']} / {t['cihaz']}")
        k2.metric("Ses süresi", f"{t['ses_suresi_sn']} sn")
        k3.metric("İşlem süresi", f"{t['islem_suresi_sn']} sn")
        hiz = t["ses_suresi_sn"] / t["islem_suresi_sn"] if t["islem_suresi_sn"] else 0
        k4.metric("Hız", f"{hiz:.1f}x gerçek zaman")
        o = st.session_state.olcumler
        if o:
            st.subheader("Bölümleme (LLM)")
            l1, l2, l3, l4 = st.columns(4)
            l1.metric("Model", o["model"])
            l2.metric("Gecikme", f"{o['gecikme_sn']} sn")
            l3.metric("Girdi token", o["girdi_token"])
            l4.metric("Çıktı token", o["cikti_token"])