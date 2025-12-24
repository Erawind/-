import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time
from datetime import datetime
from colorama import Fore, Style, init

# 初始化顏色輸出
init(autoreset=True)

class NasdaqBot:
    def __init__(self, ticker="NQ=F", interval="5m", period="1d"):
        """
        初始化機器人
        :param ticker: 股票代號 (NQ=F 為小納期貨, MNQ=F 為微型小納)
        :param interval: K線週期 (建議 5m 或 15m)
        """
        self.ticker = ticker
        self.interval = interval
        self.period = period
        # 策略參數
        self.bb_length = 20
        self.bb_std = 2.3  # 根據目前 VIX 調整過的標準差
        self.ema_length = 50

    def fetch_data(self):
        """從 Yahoo Finance 獲取數據"""
        print(f"{Fore.CYAN}[系統] 正在獲取 {self.ticker} 數據...")
        try:
            df = yf.download(self.ticker, period=self.period, interval=self.interval, progress=False)
            if df.empty:
                print(f"{Fore.RED}[錯誤] 無法獲取數據，請檢查網路或代號。")
                return None
            return df
        except Exception as e:
            print(f"{Fore.RED}[錯誤] {e}")
            return None

    def analyze(self, df):
        """計算技術指標"""
        # 1. 計算 EMA 50
        df['EMA_50'] = ta.ema(df['Close'], length=self.ema_length)

        # 2. 計算布林帶 (Bollinger Bands)
        bb = ta.bbands(df['Close'], length=self.bb_length, std=self.bb_std)
        # pandas_ta 的欄位命名通常是 BBL_20_2.3, BBM_20_2.3, BBU_20_2.3
        # 我們動態獲取欄位名稱
        df['BB_Upper'] = bb[f'BBU_{self.bb_length}_{self.bb_std}']
        df['BB_Lower'] = bb[f'BBL_{self.bb_length}_{self.bb_std}']
        df['BB_Mid']   = bb[f'BBM_{self.bb_length}_{self.bb_std}']

        return df

    def check_signal(self, df):
        """判斷最新一根 K 線的訊號"""
        # 取得最後一筆完整數據 (倒數第二筆，因為倒數第一筆可能還沒收盤)
        # 如果是實盤，我們通常看當下這筆(iloc[-1])的即時突破，但為了穩健，這裡看上一筆收盤(iloc[-2])
        last_candle = df.iloc[-2] 
        current_price = df.iloc[-1]['Close'] # 當前即時價格

        # 提取數值
        close = last_candle['Close']
        upper = last_candle['BB_Upper']
        lower = last_candle['BB_Lower']
        ema   = last_candle['EMA_50']
        
        timestamp = last_candle.name

        print(f"\n{Style.BRIGHT}--- 分析報告 ({timestamp}) ---")
        print(f"收盤價: {close:.2f} | 目前價: {current_price:.2f}")
        print(f"布林上軌: {upper:.2f} | EMA 50: {ema:.2f} | 布林下軌: {lower:.2f}")

        # --- 策略邏輯 ---
        
        # 多頭訊號：收盤價 > 布林上軌 AND 收盤價 > EMA 50
        if close > upper and close > ema:
            return "LONG"
        
        # 空頭訊號：收盤價 < 布林下軌 AND 收盤價 < EMA 50
        elif close < lower and close < ema:
            return "SHORT"
        
        else:
            return "NEUTRAL"

    def run(self):
        """執行主迴圈"""
        print(f"{Fore.YELLOW}=== 股市大師 NQ 當沖機器人啟動 ===")
        print(f"監控標的: {self.ticker} | 週期: {self.interval}")
        
        while True:
            df = self.fetch_data()
            if df is not None and len(df) > self.ema_length:
                df = self.analyze(df)
                signal = self.check_signal(df)

                # 輸出訊號
                if signal == "LONG":
                    print(f"{Fore.GREEN}{Style.BRIGHT}🔥 觸發多單訊號 (BUY SIGNAL) 🔥")
                    print(f"建議：進場做多，停損設於 {df.iloc[-2]['Close'] - 40} 點")
                elif signal == "SHORT":
                    print(f"{Fore.RED}{Style.BRIGHT}🔥 觸發空單訊號 (SELL SIGNAL) 🔥")
                    print(f"建議：進場做空，停損設於 {df.iloc[-2]['Close'] + 40} 點")
                else:
                    print(f"{Fore.WHITE}市場盤整中 (Neutral)... 等待突破")
            
            print(f"{Fore.CYAN}[系統] 等待 60 秒後進行下一次掃描...")
            time.sleep(60) # 每60秒檢查一次

if __name__ == "__main__":
    # NQ=F 是小納斯達克期貨代號
    bot = NasdaqBot(ticker="NQ=F", interval="5m")
    try:
        bot.run()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}程式已手動停止。")
