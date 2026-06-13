import datetime
import yfinance as yf
import requests
import pandas as pd
import traceback
import sys


# --- AYARLAR ---
TOKEN = '8985851282:AAHz4O3Ygyp9herlBfq0JSRG3Ps3tGFxVZ8' 
CHAT_ID = '1402340669' 
PORTFOY = {
    "DSTKF.IS": 0.1771,
    "OZATD.IS": 0.1716,
    "UKA.IS":   0.1284,
    "TERA.IS":  0.1150,
    "PEKGY.IS": 0.0989,
    "TRHOL.IS": 0.0659,
    "TEHOL.IS": 0.0550,
    "ANELE.IS": 0.0215,
    "HMV.IS":   0.0120,
    "ALKLC.IS": 0.0066,
    "SVGYO.IS": 0.0055,
    "TMPOL.IS": 0.0033,
    "HEDEF.IS": 0.0028,
    "EUPWR.IS": 0.0003,
    "CWENE.IS": 0.0003,
    "T3B.IS":   0.0002
}
BENCHMARKS = {
    "BIST 100": "XU100.IS",
    "ALTIN": "GC=F",
    "DOLAR": "USDTRY=X",
    "BIST BANKA": "XBANK.IS"
}

# --- FONKSİYONLAR ---
def get_portfolio_summary_basic():
    """Rutin Mod: Sadece toplam getiriyi döner"""
    toplam_getiri = 0
    for sembol, agirlik in PORTFOY.items():
        try:
            ticker = yf.Ticker(sembol)
            hist = ticker.history(period="2d")
            if len(hist) < 2: continue
            change = (hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]
            toplam_getiri += change * agirlik
        except: continue
    return toplam_getiri * 100

def get_benchmark_returns():
    """Endeks değişimlerini döner"""
    bench_report = []
    for name, symbol in BENCHMARKS.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            if len(hist) < 2:
                bench_report.append(f"❓ {name}: Veri yok")
                continue
            change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
            icon = "🟢" if change >= 0 else "🔴"
            bench_report.append(f"{icon} {name}: `{change:.2f}%`")
        except:
            bench_report.append(f"❓ {name}: Hata")
    return "\n".join(bench_report)

def get_detailed_portfolio_info():
    """Özet Mod: Detaylı analiz döner"""
    toplam_getiri = 0
    hisse_detaylari = []

    for sembol, agirlik in PORTFOY.items():
        try:
            ticker = yf.Ticker(sembol)
            hist = ticker.history(period="2d")
            if len(hist) < 2: continue
            guncel, gecmis = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
            hisse_getirisi = (guncel - gecmis) / gecmis
            toplam_getiri += hisse_getirisi * agirlik
            
            hisse_detaylari.append({
                'sembol': sembol.replace(".IS", ""),
                'yuzde': hisse_getirisi * 100,
                'portfoy_katkisi': hisse_getirisi * agirlik
            })
        except: continue

    if not hisse_detaylari: 
        return 0, "⚠️ Veri çekilemedi."

    # Portföye en çok katkı sağlayan ve en çok zarar ettiren hisseler
    en_iyi = max(hisse_detaylari, key=lambda x: x['portfoy_katkisi'])
    en_kotu = min(hisse_detaylari, key=lambda x: x['portfoy_katkisi'])

    detay_msg = (
        f"🚀 *En İyi Katkı:* {'🟢' if en_iyi['yuzde'] >= 0 else '🔴'} {en_iyi['sembol']}: `{en_iyi['yuzde']:.2f}%`\n"
        f"⚠️ *En Kötü Katkı:* {'🟢' if en_kotu['yuzde'] >= 0 else '🔴'} {en_kotu['sembol']}: `{en_kotu['yuzde']:.2f}%`"
    )
    return toplam_getiri * 100, detay_msg

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    try:
        requests.get(url, timeout=10)
    except Exception as e:
        print(f"Telegram gönderilemedi: {e}")

# --- ANA ÇALIŞTIRICI ---
if __name__ == "__main__":
    try:
        now = datetime.datetime.now()
        # weekday() -> Pazartesi: 0, Cumartesi: 5, Pazar: 6
        is_weekend = 0 

        if is_weekend:
            print(f"Saat: {now.strftime('%H:%M:%S')} - Bugün hafta sonu. Bot uyuyor.")
            sys.exit()

        hour = 19
        print(f"Sistem başlatıldı. Mevcut saat: {now.strftime('%H:%M:%S')}")

        # SENARYO A: Saat 19:00 (Detaylı Rapor + Endeksler)
        if hour == 19:
            print("Mod: DETAYLI ÖZET MODU aktif.")
            getiri, detaylar = get_detailed_portfolio_info()
            endeksler = get_benchmark_returns()
            
            mesaj = (
                f"📊 *GÜNLÜK KAPANIŞ RAPORU*\n\n"
                f"📈 *Toplam Portföy:* `{getiri:.2f}%`\n\n"
                f"{detaylar}\n\n"
                f"🏛️ *PİYASA DURUMU*\n"
                f"{endeksler}\n\n"
                f"🕒 *Saat:* {now.strftime('%H:%M')}"
            )
            send_telegram(mesaj)
            print("Detaylı rapor başarıyla gönderildi.")

        # SENARYO B: Saat 12:00 ile 18:59 arası (Rutin Mod)
        elif 12 <= hour < 19:
            print("Mod: RUTİN DURUM MODU aktif.")
            getiri_oran = get_portfolio_summary_basic()
            mesaj = f"🕒 *Anlık Portföy Durumu*\n📈 Toplam Getiri: `{getiri_oran:.2f}%`"
            send_telegram(mesaj)
            print("Rutin rapor başarıyla gönderildi.")

        # SENARYO C: Diğer saatler
        else:
            print(f"Mod: BEKLEME. (Saat {hour}, rapor saati değil)")

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ KRİTİK HATA OLUŞTU:\n{error_trace}")
        try:
            send_telegram(f"⚠️ *BOT ÇÖKTÜ!*\n\n`{error_trace[-500:]}`") 
        except:
            print("Telegram üzerinden hata gönderilemedi.")
