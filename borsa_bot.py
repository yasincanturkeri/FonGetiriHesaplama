import yfinance as yf
import pandas_market_calendars as mcal
import requests
import datetime

# AYARLAR
TOKEN = '8985851282:AAHz4O3Ygyp9herlBfq0JSRG3Ps3tGFxVZ8' 
CHAT_ID = '1402340669' 

# PORTFÖY (Hisse Kodu: Ağırlık)
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
# ==========================================================

def is_borsa_acik_mi():
    try:
        bist = mcal.get_calendar('XIDX') 
        now = datetime.datetime.now(datetime.timezone.utc)
        schedule = bist.schedule(end_date=now, start_date=now)
        if schedule.empty:
            return False
        
        tr_now = datetime.datetime.now()
        tr_hour = tr_now.hour
        # Borsa işlem saatleri kontrolü (09:00 - 18:00 arası)
        return 9 <= tr_hour < 19
    except:
        return False

def get_portfolio_return():
    toplam_getiri = 0
    basarili_hisse_sayisi = 0
    
    for sembol, agirlik in PORTFOY.items():
        try:
            ticker = yf.Ticker(sembol)
            hist = ticker.history(period="2d")
            
            if len(hist) < 2:
                continue
            
            guncel_fiyat = hist['Close'].iloc[-1]
            gecmis_fiyat = hist['Close'].iloc[-2]
            
            # Getiri: ((Yeni - Eski) / Eski) * Ağırlık
            getiri = ((guncel_fiyat - gecmis_fiyat) / gecmis_fiyat) * agirlik
            toplam_getiri += getiri
            basarili_hisse_sayisi += 1
            
        except Exception as e:
            print(f"{sembol} hatası: {e}")
            continue
            
    return toplam_getiri, basarili_hisse_sayisi

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    try:
        requests.get(url)
    except:
        pass

if __name__ == "__main__":
    if is_borsa_acik_mi():
        getiri_oran, sayi = get_portfolio_return()
        
        if sayi > 0:
            mesaj = f"📊 *Günlük Portföy Raporu*\n\n" \
                    f"📈 *Toplam Getiri:* `%{getiri_oran*100:.2f}`\n" \
                    f"🕒 *Saat:* {datetime.datetime.now().strftime('%H:%M')}\n" \
                    f"✅ *Hisse Sayısı:* {sayi}"
            send_telegram(mesaj)
    else:
        print("Borsa kapalı.")
