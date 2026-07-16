import datetime
import yfinance as yf
import requests
import pandas as pd
import traceback
import sys
import yaml
import pytz
import os

# ============================================
# 1. PROXY AYARI - Burayı değiştirin!
# ============================================
# Çalışan bir proxy adresi bulup aşağıya yazın.
# Örnek format: "http://123.123.123.123:8080"
# Ücretsiz proxy bulmak için: https://free-proxy-list.net/ adresini kullanabilirsiniz.
PROXY = "http://93.113.63.11:3128"   # <--- BURAYI DEĞİŞTİRİN
# ============================================

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

# --- YARDIMCI FONKSİYON (Proxy ile veri çeker) ---
def get_price_data(symbol, period="5d"):
    """
    yf.download() kullanarak veri çeker.
    Proxy desteği eklendi.
    """
    try:
        # Proxy'yi kullanarak download et
        df = yf.download(
            symbol, 
            period=period, 
            progress=False, 
            auto_adjust=False, 
            threads=False,
            proxy=PROXY   # <--- PROXY EKLENDİ
        )
        if df.empty:
            # auto_adjust=True dene
            df = yf.download(
                symbol, 
                period=period, 
                progress=False, 
                auto_adjust=True, 
                threads=False,
                proxy=PROXY   # <--- PROXY EKLENDİ
            )
        return df
    except Exception as e:
        print(f"⚠️ {symbol} indirme hatası: {e}")
        return pd.DataFrame()

# --- FONKSİYONLAR (değişmedi) ---

def get_portfolio_summary_basic():
    toplam_getiri = 0
    basarili_hisse_sayisi = 0
    for sembol, agirlik in PORTFOY.items():
        hist = get_price_data(sembol, period="5d")
        if hist.empty or len(hist) < 2:
            print(f"⚠️ {sembol} için yeterli veri yok (gün sayısı: {len(hist)})")
            continue
        
        close_values = hist['Close'].iloc[-2:].values
        change = (close_values[1] - close_values[0]) / close_values[0]
        toplam_getiri += change * agirlik
        basarili_hisse_sayisi += 1

    if basarili_hisse_sayisi == 0:
        print("⚠️ Hiçbir hisse için veri alınamadı, toplam getiri 0 döndü.")
        return 0.0
    return toplam_getiri * 100

def get_benchmark_returns():
    bench_report = []
    for name, symbol in BENCHMARKS.items():
        hist = get_price_data(symbol, period="5d")
        if hist.empty or len(hist) < 2:
            bench_report.append(f"❓ {name}: Veri yok")
            continue
        
        close_values = hist['Close'].iloc[-2:].values
        change = ((close_values[1] - close_values[0]) / close_values[0]) * 100
        icon = "🟢" if change >= 0 else "🔴"
        bench_report.append(f"{icon} {name}: `{change:.2f}%`")
    
    return "\n".join(bench_report)

def get_detailed_portfolio_info():
    toplam_getiri = 0
    hisse_detaylari = []
    
    for sembol, agirlik in PORTFOY.items():
        hist = get_price_data(sembol, period="5d")
        if hist.empty or len(hist) < 2:
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

    if not hisse_detaylari:
        return 0, "⚠️ Veri çekilemedi. (Tüm hisseler başarısız)"

    en_iyi = max(hisse_detaylari, key=lambda x: x['portfoy_katkisi'])
    en_kotu = min(hisse_detaylari, key=lambda x: x['portfoy_katkisi'])

    detay_msg = (
        f"🚀 *En İyi Katkı:* {'🟢' if en_iyi['yuzde'] >= 0 else '🔴'} {en_iyi['sembol']}: `{en_iyi['yuzde']:.2f}%`\n"
        f"⚠️ *En Kötü Katkı:* {'🟢' if en_kotu['yuzde'] >= 0 else '🔴'} {en_kotu['sembol']}: `{en_kotu['yuzde']:.2f}%`"
    )
    return toplam_getiri * 100, detay_msg

def send_telegram(msg):
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

# --- ANA ÇALIŞTIRICI (değişmedi) ---
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
