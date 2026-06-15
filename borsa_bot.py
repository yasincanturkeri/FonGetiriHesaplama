import datetime
import yfinance as yf
import requests
import pandas as pd
import traceback
import sys
import yaml

# --- CONFIG YÜKLEME ---
try:
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    TOKEN = config['telegram']['token']
    CHAT_ID = config['telegram']['chat_id']
    PORTFOY = config['portfoy']
    BENCHMARKS = config['benchmarks']
except Exception as e:
    print(f"❌ Config dosyası yüklenemedi: {e}")
    sys.exit()

# --- FONKSİYONLAR ---
def get_portfolio_summary_basic():
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
        tsi = pytz.timezone('Europe/Istanbul')
        now = datetime.datetime.now(tsi)
        is_weekend = now.weekday() >= 5

        if is_weekend:
            print(f"Saat: {now.strftime('%H:%M:%S')} - Bugün hafta sonu. Bot uyuyor.")
            sys.exit()

        hour = now.hour
        print(f"Sistem başlatıldı. Mevcut saat: {now.strftime('%H:%M:%S')} (Simüle edilen saat: {hour})")

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

        elif 11 <= hour < 19:
            print("Mod: RUTİN DURUM MODU aktif.")
            getiri_oran = get_portfolio_summary_basic()
            mesaj = f"🕒 *Anlık Portföy Durumu*\n📈 Toplam Getiri: `{getiri_oran:.2f}%`"
            send_telegram(mesaj)
            print("Rutin rapor başarıyla gönderildi.")

        else:
            print(f"Mod: BEKLEME. (Saat {hour}, rapor saati değil)")

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ KRİTİK HATA OLUŞTU:\n{error_trace}")
        try:
            send_telegram(f"⚠️ *BOT ÇÖKTÜ!*\n\n`{error_trace[-500:]}`") 
        except:
            print("Telegram üzerinden hata gönderilemedi.")
