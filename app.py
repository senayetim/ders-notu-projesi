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

for anahtar, deger in {
    "transkript": None, "bolumler": [], "olcumler": None, "ses_bayt": None,
    "ses_format": "audio/mpeg", "dosya_adi": "", "baslangic_sn": 0, "otomatik": False,
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
    for b in bolumler:
        if b["baslangic_sn"] <= sn < b["bitis_sn"]:
            return b
    return None


def git(sn):
    st.session_state.baslangic_sn = int(sn)
    st.session_state.otomatik = True


def notlari_md(dosya_adi, bolumler):
    satirlar = [f"# {dosya_adi}\n"]
    for b in bolumler:
        satirlar.append(f"## [{sn_to_dk(b['baslangic_sn'])} - {sn_to_dk(b['bitis_sn'])}] {b['baslik']}\n")
        satirlar.append(f"{b['ozet']}\n")
        satirlar.append(f"*Anahtar kelimeler:* {', '.join(b['anahtar_kelimeler'])}\n")
    return "\n".join(satirlar)


def isle(ses_bayt, dosya_adi, whisper_modeli, yeniden_t, yeniden_b):
    yol = YUKLEME_DIZINI / dosya_adi
    yol.write_bytes(ses_bayt)
    anahtar = f"{yol.stem}_{whisper_modeli}"
    t_yol = CIKTI_DIZINI / f"{anahtar}_transkript.json"
    b_yol = CIKTI_DIZINI / f"{anahtar}_bolumler.json"

    bolumler, olcumler = [], None
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
                st.error(f"Bölümleme başarısız oldu: {e}")
        durum.update(label="Hazır", state="complete", expanded=False)

    st.session_state.transkript = transkript
    st.session_state.bolumler = bolumler
    st.session_state.olcumler = olcumler
    st.session_state.ses_bayt = ses_bayt
    st.session_state.ses_format = SES_FORMATLARI.get(Path(dosya_adi).suffix.lower(), "audio/mpeg")
    st.session_state.dosya_adi = dosya_adi
    st.session_state.baslangic_sn = 0
    st.session_state.otomatik = False


# ---------- Kenar çubuğu ----------
with st.sidebar:
    st.header("Ayarlar")
    whisper_modeli = st.selectbox("Whisper modeli", ["small", "medium", "large-v3"], index=1)
    yeniden_t = st.checkbox("Transkripti yeniden üret")
    yeniden_b = st.checkbox("Bölümlemeyi yeniden üret")
    st.caption(f"LLM: {LLM_MODEL}")

# ---------- Ana sayfa ----------
st.title("🎓 Ders Kaydından Bölümlenmiş Not")
st.caption("Ders kaydını yükle; yazıya dökelim, konulara bölelim, zaman damgasıyla arayalım.")

yuklenen = st.file_uploader("Ses dosyası", type=["mp3", "wav", "m4a", "mp4", "ogg", "flac"])
if yuklenen and st.button("İşle", type="primary"):
    isle(yuklenen.getvalue(), yuklenen.name, whisper_modeli, yeniden_t, yeniden_b)

t = st.session_state.transkript
if t:
    st.divider()
    st.audio(
        st.session_state.ses_bayt,
        format=st.session_state.ses_format,
        start_time=st.session_state.baslangic_sn,
        autoplay=st.session_state.otomatik,
    )
    bolumler = st.session_state.bolumler
    sekme_b, sekme_a, sekme_t, sekme_o = st.tabs(["📚 Bölümler", "🔎 Arama", "📝 Tam transkript", "📊 Ölçümler"])

    with sekme_b:
        if not bolumler:
            st.info("Bölüm bilgisi yok. Gemini hatasını yukarıda kontrol et; transkript ve arama yine çalışır.")
        else:
            st.download_button(
                "Notları indir (.md)",
                data=notlari_md(st.session_state.dosya_adi, bolumler),
                file_name="ders_notlari.md",
                mime="text/markdown",
            )
            for i, b in enumerate(bolumler):
                aralik = f"{sn_to_dk(b['baslangic_sn'])} – {sn_to_dk(b['bitis_sn'])}"
                with st.expander(f"{aralik} · {b['baslik']}"):
                    st.write(b["ozet"])
                    st.caption("Anahtar kelimeler: " + ", ".join(b["anahtar_kelimeler"]))
                    st.button("▶ Buradan oynat", key=f"bolum_{i}", on_click=git, args=(b["baslangic_sn"],))

    with sekme_a:
        sorgu = st.text_input("Ne arıyorsun?", placeholder="örn. sinir ağı, aktivasyon fonksiyonu")
        if sorgu.strip():
            s = sadelestir(sorgu.strip())
            sonuclar = [p for p in t["parcalar"] if s in sadelestir(p["metin"])]
            st.write(f"**{len(sonuclar)}** sonuç bulundu.")
            for i, p in enumerate(sonuclar[:50]):
                c1, c2, c3 = st.columns([1, 6, 2])
                c1.markdown(f"`{sn_to_dk(p['baslangic'])}`")
                c2.markdown(vurgula(p["metin"], sorgu.strip()))
                bolum = bolum_bul(bolumler, p["baslangic"])
                if bolum:
                    c2.caption(f"Bölüm: {bolum['baslik']}")
                c3.button("▶ Oynat", key=f"ara_{i}", on_click=git, args=(p["baslangic"],))
            if len(sonuclar) > 50:
                st.caption("İlk 50 sonuç gösteriliyor.")

    with sekme_t:
        st.dataframe(
            [{"Zaman": sn_to_dk(p["baslangic"]), "Metin": p["metin"]} for p in t["parcalar"]],
            hide_index=True,
        )

    with sekme_o:
        st.subheader("Whisper")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Model / cihaz", f"{t['model']} / {t['cihaz']}")
        k2.metric("Ses süresi", f"{t['ses_suresi_sn']} sn")
        k3.metric("İşlem süresi", f"{t['islem_suresi_sn']} sn")
        hiz = t["ses_suresi_sn"] / t["islem_suresi_sn"] if t["islem_suresi_sn"] else 0
        k4.metric("Hız", f"{hiz:.1f}x gerçek zaman")
        o = st.session_state.olcumler
        if o:
            st.subheader("LLM")
            l1, l2, l3, l4 = st.columns(4)
            l1.metric("Model", o["model"])
            l2.metric("Gecikme", f"{o['gecikme_sn']} sn")
            l3.metric("Girdi token", o["girdi_token"])
            l4.metric("Çıktı token", o["cikti_token"])