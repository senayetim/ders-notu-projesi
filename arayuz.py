"""Arayüzün HTML parçaları. Yapay zekâdan ya da kayıttan gelen her metin burada kaçışlanır."""
import base64
from html import escape
from pathlib import Path

from bolumle import sn_to_dk

CSS_YOLU = Path(__file__).parent / "assets" / "stil.css"
RENKLER = ["#0F6B5F", "#C8862A", "#B4533C", "#6B4E8E", "#3B6C94", "#6F7F3A"]


def renk(i):
    return RENKLER[i % len(RENKLER)]


def uzun_sure(sn):
    """Süreyi okunur metne çevirir: 1 sa 9 dk, 20 dk."""
    dakika = round(sn / 60)
    if dakika >= 60:
        return f"{dakika // 60} sa {dakika % 60} dk"
    return f"{max(dakika, 1)} dk"


LOGO_YOLU = Path(__file__).parent / "assets" / "logo.png"
# st.html satır içi <svg>'yi temizlediği için logo <img> içinde data URI olarak verilir
LOGO_IMG = (
    '<img src="data:image/svg+xml;base64,'
    + base64.b64encode((Path(__file__).parent / "assets" / "logo.svg").read_bytes()).decode()
    + '" width="34" height="34" alt="" style="display:block">'
)


def marka():
    return (
        f'<div class="marka"><div class="marka-rozet">{LOGO_IMG}</div>'
        '<div><div class="marka-ad">EchoNote</div><div class="marka-alt">Ders kaydından çalışma notuna</div></div></div>'
    )


def hero(ders_sayisi, toplam_sn, bolum_sayisi):
    sayilar = ""
    if ders_sayisi:
        sayilar = (
            '<div class="hero-sayilar">'
            f'<div class="hero-sayi"><b>{ders_sayisi}</b><span>ders</span></div>'
            f'<div class="hero-sayi"><b>{uzun_sure(toplam_sn)}</b><span>kayıt</span></div>'
            f'<div class="hero-sayi"><b>{bolum_sayisi}</b><span>konu bölümü</span></div>'
            "</div>"
        )
    return (
        '<h1 class="hero-baslik">Dersi sen dinle,<br><mark>notları</mark> biz çıkaralım.</h1>'
        '<p class="hero-metin">Kaydını yükle; yazıya dökülsün, konulara ayrılsın. '
        "Sonra özetlerden çalış, kendini sına, aklına takılanı sor.</p>"
        f"{sayilar}"
    )


def adimlar():
    veri = [
        ("1", "Yükle", "Ders kaydını seç: mp3, wav, m4a, mp4."),
        ("2", "Bekle", "Ses yazıya dökülür, yapay zekâ konulara böler."),
        ("3", "Çalış", "Özet oku, quiz çöz, soru sor, istediğin saniyeden dinle."),
    ]
    icerik = "".join(
        f'<div class="adim"><span class="adim-no">0{no}</span><b>{baslik}</b><p>{metin}</p></div>'
        for no, baslik, metin in veri
    )
    return f'<div class="adimlar">{icerik}</div>'


def seridi(oranlar, yukseklik=7):
    """Bir dersin bölümlerini oranlarına göre renkli bir şerit olarak çizer."""
    if not oranlar:
        return f'<div class="seridi"><span class="seridi-bos" style="height:{yukseklik}px"></span></div>'
    parcalar = "".join(
        f'<span style="flex:{o:.4f} 1 0;height:{yukseklik}px;background:{renk(i)}"></span>'
        for i, o in enumerate(oranlar)
    )
    return f'<div class="seridi">{parcalar}</div>'


def ders_karti(ozet):
    bilgi = [uzun_sure(ozet["sure_sn"]), f"{ozet['bolum_sayisi']} bölüm", ozet["model"]]
    rozetler = ""
    if ozet["calisma_var"]:
        rozetler += '<span class="durum">Quiz hazır</span>'
    if ozet["gomme_var"]:
        rozetler += '<span class="durum">Anlamsal arama</span>'
    if not ozet["ses_var"]:
        rozetler += '<span class="durum durum-uyari">Ses dosyası yok</span>'
    return (
        f'{seridi(ozet["oranlar"])}'
        f'<div class="kart-ad">{escape(ozet["ad"])}</div>'
        f'<p class="kart-bilgi">{" · ".join(escape(b) for b in bilgi)}</p>'
        f'<div class="kart-rozetler">{rozetler}</div>'
    )


def ders_basligi(ad, t, bolum_sayisi):
    bilgiler = [
        f"<span><b>{uzun_sure(t['ses_suresi_sn'])}</b> kayıt</span>",
        f"<span><b>{bolum_sayisi}</b> bölüm</span>",
        f"<span><b>{len(t['parcalar'])}</b> transkript satırı</span>",
    ]
    return f'<h1 class="ders-baslik">{escape(ad)}</h1><div class="ders-bilgi">{"".join(bilgiler)}</div>'


def simdi_caliniyor(sn, bolum):
    baslik = f"<b>{escape(bolum['baslik'])}</b>" if bolum else "<b>Baştan başla</b>"
    return f'<div class="simdi"><span class="zaman">{sn_to_dk(sn)}</span>{baslik}</div>'


def zaman_seridi(bolumler, toplam_sn):
    parcalar = ""
    for i, b in enumerate(bolumler):
        ipucu = escape(f"{sn_to_dk(b['baslangic_sn'])} · {b['baslik']}", quote=True)
        pay = (b["bitis_sn"] - b["baslangic_sn"]) / toplam_sn
        parcalar += f'<span title="{ipucu}" style="flex:{pay:.4f} 1 0;background:{renk(i)}"></span>'
    return f'<div class="zaman-seridi">{parcalar}</div>'


def bolum_karti(i, b, caliniyor):
    aralik = f"{sn_to_dk(b['baslangic_sn'])} – {sn_to_dk(b['bitis_sn'])}"
    canli = '<span class="durum durum-canli">Şimdi çalıyor</span>' if caliniyor else ""
    etiketler = "".join(f'<span class="etiket">{escape(k)}</span>' for k in b["anahtar_kelimeler"])
    return (
        f'<div class="bolum-ust"><span class="bolum-no" style="background:{renk(i)}">{i + 1}</span>'
        f'<span class="zaman">{aralik}</span>{canli}</div>'
        f'<div class="bolum-baslik">{escape(b["baslik"])}</div>'
        f'<p class="bolum-ozet">{escape(b["ozet"])}</p>'
        f"<div>{etiketler}</div>"
    )


def istatistikler(veri):
    icerik = "".join(
        f'<div class="istatistik"><span>{escape(ad)}</span><b>{escape(str(deger))}</b></div>'
        for ad, deger in veri
    )
    return f'<div class="istatistikler">{icerik}</div>'


def bos_durum(baslik, metin):
    return f'<div class="bos"><b>{escape(baslik)}</b><p>{escape(metin)}</p></div>'


def skor(dogru, toplam, cevaplanan):
    oran = dogru / toplam if toplam else 0
    if oran >= 0.8:
        yorum = "Harika, bu konu sende."
    elif oran >= 0.5:
        yorum = "İyi gidiyor, yanlışlarını gözden geçir."
    else:
        yorum = "Yanlışların kaynağını dinleyip yeniden dene."
    bos = toplam - cevaplanan
    ek = f" {bos} soru boş kaldı." if bos else ""
    return (
        f'<div class="skor"><div class="skor-halka" style="background:conic-gradient(var(--vurgu) {oran * 360:.0f}deg, var(--yuzey-2) 0)">'
        f"<i>%{round(oran * 100)}</i></div>"
        f"<div><b>{dogru} / {toplam} doğru</b><p>{yorum}{ek}</p></div></div>"
    )


def quiz_sonucu(no, dogru_mu, dogru_cevap, aciklama):
    isaret = '<span class="sonuc-isaret iyi">✓</span>' if dogru_mu else '<span class="sonuc-isaret kotu">✗</span>'
    return (
        f'<p class="sonuc-dogru">{isaret}{no}. {escape(dogru_cevap)}</p>'
        f'<p class="sonuc-aciklama">{escape(aciklama)}</p>'
    )


def bilgi_karti(metin, sira, toplam, arka):
    sinif, tur = ("kart-yuz arka", "Cevap") if arka else ("kart-yuz", "Soru")
    return (
        f'<div class="deste"><div class="{sinif}">'
        f'<span class="kart-tur">{tur}</span><span class="kart-sira">{sira} / {toplam}</span>'
        f'<p class="kart-metin">{escape(metin)}</p></div></div>'
    )


def baloncuk(metin, tur):
    return f'<div class="baloncuk baloncuk-{tur}">{escape(metin)}</div>'


def bulunan(vurgulu_metin, kaynak="", rozet=None):
    """Arama sonucu gövdesi; vurgulu_metin vurgula() çıktısıdır, zaten kaçışlanmıştır."""
    html = f'<p class="bulunan-metin">{vurgulu_metin}</p>'
    if kaynak:
        html += f'<p class="bulunan-kaynak">{escape(kaynak)}</p>'
    if rozet:
        html += f'<span class="rozet" style="background:{rozet[1]}">{escape(rozet[0])}</span>'
    return html


def transkript_okuma(parcalar, bolumler):
    """Transkripti bölüm başlıklarıyla ayrılmış, okunur bir metin olarak verir."""
    satirlar, bolum_no = [], 0
    for p in parcalar:
        while bolum_no < len(bolumler) and p["baslangic"] >= bolumler[bolum_no]["baslangic_sn"]:
            satirlar.append(f"<h4>{escape(bolumler[bolum_no]['baslik'])}</h4>")
            bolum_no += 1
        satirlar.append(
            f'<div class="okuma-satir"><span class="zaman">{sn_to_dk(p["baslangic"])}</span>'
            f"<span>{escape(p['metin'])}</span></div>"
        )
    return f'<div class="okuma">{"".join(satirlar)}</div>'
