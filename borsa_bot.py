import datetime
import yfinance as yf
import requests
import pandas as pd
import traceback
import sys
import yaml
import pytz
import os
import time   # ekledik, yeniden deneme için

# --- USER-AGENT AYARI (Yahoo Finance’in engellemesini aşmak için) ---
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
})
yf.set_requests_session(session)   # yfinance'a özel session'ı veriyoruz

# --- CONFIG YÜKLEME ---
try:
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    TOKEN = config.get('telegram', {}).get('token') or os.environ.get('TELEGRAM_TOKEN')
    CHAT_ID = config.get('telegram', {}).get('chat_id') or os.environ.get('TELEGRAM_CHAT_ID')
    PORTFOY = config['portfoy']
    BENCHMARKS = config['benchmarks']
except Exception as e:
    print(f"❌ Config dosyası yüklenemedi: {e}")
    sys.exit()

# --- FONKSİYONLAR ---

def get_portfolio_summary_basic():
    """
    Basit toplam getiri hesaplar (her hissenin son iki işlem gününe bakar).
    Hata durumunda o hisseyi atlar ve log yazar.
    """
    toplam_getiri = 0
    basarili_hisse_sayisi = 0
    for sembol, agirlik in PORTFOY.items():
        try:
            # Son 5 işlem gününü al, böylece tatil/eksik gün sorununu azalt
            ticker = yf.Ticker(sembol)
            hist = ticker.history(period="5d")
            if len(hist) < 2:
                print(f"⚠️ {sembol} için yeterli veri yok (sadece {len(hist)} gün)")
                continue
            # En son iki kapanış fiyatını al
            close_values = hist['Close'].iloc[-2:].values
            change = (close_values[1] - close_values[0]) / close_values[0]
            toplam_getiri += change * agirlik
            basarili_hisse_sayisi += 1
        except Exception as e:
            print(f"❌ {sembol} hesaplanırken hata: {e}")
            continue
    if basarili_hisse_sayisi == 0:
        print("⚠️ Hiçbir hisse için veri alınamadı, toplam getiri 0 döndü.")
        return 0.0
    return toplam_getiri * 100

def get_benchmark_returns():
    """Endeks ve emtia getirilerini hesaplar."""
    bench_report = []
    for name, symbol in BENCHMARKS.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if len(hist) < 2:
                bench_report.append(f"❓ {name}: Veri yok")
                continue
            close_values = hist['Close'].iloc[-2:].values
            change = ((close_values[1] - close_values[0]) / close_values[0]) * 100
            icon = "🟢" if change >= 0 else "🔴"
            bench_report.append(f"{icon} {name}: `{change:.2f}%`")
        except Exception as e:
            print(f"❌ {name} benchmark hatası: {e}")
            bench_report.append(f"❓ {name}: Hata")
    return "\n".join(bench_report)

def get_detailed_portfolio_info():
    """
    Detaylı portföy getirisi ve en iyi/en kötü katkıyı hesaplar.
    """
    toplam_getiri = 0
    hisse_detaylari = []
    for sembol, agirlik in PORTFOY.items():
        try:
            ticker = yf.Ticker(sembol)
            hist = ticker.history(period="5d")
            if len(hist) < 2:
                print(f"⚠️ {sembol} için detaylı veri yok (gün sayısı: {len(hist)})")
                continue
            close_values = hist['Close'].iloc[-2:].values
            hisse_getirisi = (close_values[1] - close_values[0]) / close_values[0]
            toplam_getiri += hisse_getirisi * agirlik
            hisse_detaylari.append({
                'sembol': sembol.replace(".IS", ""),
                'yuzde': hisse_getirisi * 100,
                'portfoy_katkisi': hisse_getirisi * agirlik
            })
        except Exception as e:
            print(f"❌ {sembol} detay hatası: {e}")
            continue

    if not hisse_detaylari:
        print("⚠️ Hiçbir hisse için detay verisi alınamadı.")
        return 0, "⚠️ Veri çekilemedi. (Tüm hisseler başarısız)"

    # En iyi ve en kötü katkıyı bul
    en_iyi = max(hisse_detaylari, key=lambda x: x['portfoy_katkisi'])
    en_kotu = min(hisse_detaylari, key=lambda x: x['portfoy_katkisi'])

    detay_msg = (
        f"🚀 *En İyi Katkı:* {'🟢' if en_iyi['yuzde'] >= 0 else '🔴'} {en_iyi['sembol']}: `{en_iyi['yuzde']:.2f}%`\n"
        f"⚠️ *En Kötü Katkı:* {'🟢' if en_kotu['yuzde'] >= 0 else '🔴'} {en_kotu['sembol']}: `{en_kotu['yuzde']:.2f}%`"
    )
    return toplam_getiri * 100, detay_msg

def send_telegram(msg):
    """Telegram'a mesaj gönderir, hata durumunda log yazar."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    params = {
        'chat_id': CHAT_ID,
        'text': msg,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            print(f"❌ Telegram gönderimi başarısız, kod: {response.status_code}")
    except Exception as e:
        print(f"❌ Telegram gönderilemedi: {e}")

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

        if 10 <= hour < 19:
            print("Mod: RUTİN DURUM MODU aktif.")
            getiri_oran = get_portfolio_summary_basic()
            mesaj = f"🕒 *Anlık Portföy Durumu*\n📈 Toplam Getiri: `{getiri_oran:.2f}%`"
            send_telegram(mesaj)
            print("Rutin rapor başarıyla gönderildi.")
        else:
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

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ KRİTİK HATA OLUŞTU:\n{error_trace}")
        try:
            send_telegram(f"⚠️ *BOT ÇÖKTÜ!*\n\n`{error_trace[-500:]}`")
        except:
            print("Telegram üzerinden hata gönderilemedi.")
