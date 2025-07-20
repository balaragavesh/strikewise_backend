import requests
import numpy as np
import pandas as pd
from scipy.stats import norm


def get_nifty_spot_price(access_token, instrument_key):
    url = "https://api.upstox.com/v2/market-quote/ltp"
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {'instrument_key': instrument_key}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()['data']
        return list(data.values())[0]['last_price']
    except:
        return None


def get_live_option_chain(access_token, instrument_key, expiry_date):
    url = "https://api.upstox.com/v2/option/chain"
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {'instrument_key': instrument_key, 'expiry_date': expiry_date}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        raw_data = response.json()

        data = raw_data.get("data", [])
        if not data:
            print("❌ No option chain data returned")
            return None

        df = pd.json_normalize(data, sep='.')

        df.rename(columns={
            'strike_price': 'Strike',
            'call_options.market_data.ltp': 'Call LTP',
            'put_options.market_data.ltp': 'Put LTP',
            'call_options.option_greeks.iv': 'Call IV',
            'put_options.option_greeks.iv': 'Put IV',
            'call_options.market_data.oi': 'Call OI',
            'put_options.market_data.oi': 'Put OI',
        }, inplace=True)

        required_columns = [
            'Strike',
            'Call LTP', 'Put LTP',
            'Call IV', 'Put IV',
            'Call OI', 'Put OI'
        ]

        for col in required_columns:
            if col not in df.columns:
                df[col] = np.nan  # Ensure all required columns exist

        df = df[required_columns].sort_values(by='Strike')

        # ✅ Show top 10 rows of the processed option chain
        print("🔍 Fetched Raw Option Chain Sample:")
        print(df.head(10).to_string(index=False))

        return df

    except Exception as e:
        print("❌ Error while fetching option chain:", e)
        return None


def implied_volatility(option_price, S, K, T, r, option_type, tol=1e-5, max_iter=100):
    if option_price <= 0 or T <= 0:
        return np.nan
    sigma = 0.2  # Initial guess
    for _ in range(max_iter):
        price, delta, _ = bsm_price_and_greeks(S, K, T, r, sigma, option_type)
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        vega = S * norm.pdf(d1) * np.sqrt(T)
        if vega < 1e-8:
            return np.nan
        price_diff = price - option_price
        if abs(price_diff) < tol:
            return sigma * 100
        sigma -= price_diff / vega
        if sigma <= 0:
            return np.nan
    return np.nan


def bsm_price_and_greeks(S, K, T, r, sigma, option_type):
    if T <= 0 or sigma <= 0:
        return np.nan, np.nan, np.nan
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "call":
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        delta = norm.cdf(d1)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        delta = -norm.cdf(-d1)

    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    return price, delta, gamma


def compute_option_risk_reward_all_strikes(df, spot_target, spot_sl, current_spot, T, r, lot_size, option_type):
    result = []

    for _, row in df.iterrows():
        strike = row["Strike"]
        entry_price = row.get("LTP", None)
        iv = row.get("IV", None)
        oi = row.get("OI", 0)

        if pd.isna(entry_price) or entry_price <= 0:
            result.append({
                "Strike": round(strike, 2),
                "LTP": entry_price,
                "Target_Premium": None,
                "SL_Premium": None,
                "Capital_Per_Lot": None,
                "Profit_Per_Lot": None,
                "Loss_Per_Lot": None,
                "Profit_": None,
                "Loss_": None,
                "Delta": None,
                "Gamma": None,
                "IV_Used": None,
                "OI": oi,
                "Lot_Size": lot_size
            })
            continue

        # Use implied volatility from API or backsolve if invalid
        if pd.isna(iv) or iv <= 0 or iv > 150:
            iv = implied_volatility(
                option_price=entry_price,
                S=current_spot,
                K=strike,
                T=T,
                r=r,
                option_type=option_type
            )

        if pd.isna(iv) or iv <= 0 or iv > 150:
            result.append({
                "Strike": round(strike, 2),
                "LTP": round(entry_price, 2),
                "Target_Premium": None,
                "SL_Premium": None,
                "Capital_Per_Lot": round(entry_price * lot_size, 2),
                "Profit_Per_Lot": None,
                "Loss_Per_Lot": None,
                "Profit_": None,
                "Loss_": None,
                "Delta": None,
                "Gamma": None,
                "IV_Used": None,
                "OI": oi,
                "Lot_Size": lot_size
            })
            continue

        sigma = iv / 100

        target_price, delta, gamma = bsm_price_and_greeks(
            S=spot_target, K=strike, T=T, r=r, sigma=sigma, option_type=option_type
        )
        sl_price, _, _ = bsm_price_and_greeks(
            S=spot_sl, K=strike, T=T, r=r, sigma=sigma, option_type=option_type
        )

        if pd.isna(target_price) or pd.isna(sl_price):
            result.append({
                "Strike": round(strike, 2),
                "LTP": round(entry_price, 2),
                "Target_Premium": None,
                "SL_Premium": None,
                "Capital_Per_Lot": round(entry_price * lot_size, 2),
                "Profit_Per_Lot": None,
                "Loss_Per_Lot": None,
                "Profit_": None,
                "Loss_": None,
                "Delta": None,
                "Gamma": None,
                "IV_Used": round(iv, 2),
                "OI": oi,
                "Lot_Size": lot_size
            })
            continue

        capital_per_lot = entry_price * lot_size
        if option_type == "call":
            profit_per_lot = (target_price - entry_price) * lot_size
            loss_per_lot = (entry_price - sl_price) * lot_size
        else:  # put
            profit_per_lot = (entry_price - target_price) * lot_size
            loss_per_lot = (sl_price - entry_price) * lot_size
        profit_pct = (profit_per_lot / capital_per_lot) * 100 if capital_per_lot > 0 else 0
        loss_pct = (loss_per_lot / capital_per_lot) * 100 if capital_per_lot > 0 else 0

        result.append({
            "Strike": round(strike, 2),
            "LTP": round(entry_price, 2),
            "Target_Premium": round(target_price, 2),
            "SL_Premium": round(sl_price, 2),
            "Capital_Per_Lot": round(capital_per_lot, 2),
            "Profit_Per_Lot": round(profit_per_lot, 2),
            "Loss_Per_Lot": round(loss_per_lot, 2),
            "Profit_": round(profit_pct, 2),
            "Loss_": round(loss_pct, 2),
            "Delta": round(delta, 4),
            "Gamma": round(gamma, 6),
            "IV_Used": round(iv, 2),
            "OI": oi,
            "Lot_Size": lot_size
        })

    return pd.DataFrame(result)


def select_best_contracts(df, capital, risk_limit):
    selected = []
    capital_remaining = capital
    risk_remaining = risk_limit

    df = df.copy()

    df = df[
        (df["Capital_Per_Lot"] > 0) &
        (df["Profit_Per_Lot"] > 0) &
        (df["Loss_Per_Lot"] > 0)
    ].dropna(subset=["Capital_Per_Lot", "Profit_Per_Lot", "Loss_Per_Lot"])

    if df.empty:
        return pd.DataFrame()

    df["Efficiency"] = df["Profit_Per_Lot"] / df["Capital_Per_Lot"]
    df.sort_values(by="Efficiency", ascending=False, inplace=True)

    for _, row in df.iterrows():
        reward = row["Profit_Per_Lot"]
        risk = row["Loss_Per_Lot"]
        cost = row["Capital_Per_Lot"]

        if pd.isna(reward) or reward <= 0 or pd.isna(risk) or risk <= 0 or pd.isna(cost) or cost <= 0:
            continue

        try:
            max_lots = min(int(capital_remaining // cost), int(risk_remaining // risk))
        except ValueError:
            continue

        if max_lots <= 0:
            continue

        total_cost = max_lots * cost
        total_reward = max_lots * reward
        total_risk = max_lots * risk

        selected.append({
            "Strike": round(row["Strike"], 2),
            "Lots": int(max_lots),
            "Entry_Price": round(row["LTP"], 2),
            "Target_Price": round(row["Target_Premium"], 2),
            "SL_Price": round(row["SL_Premium"], 2),
            "Total_Reward": round(total_reward, 2),
            "Total_Risk": round(total_risk, 2),
            "Total_Cost": round(total_cost, 2)
        })

        capital_remaining -= total_cost
        risk_remaining -= total_risk

        if capital_remaining < df["Capital_Per_Lot"].min() or risk_remaining <= 0:
            break

    return pd.DataFrame(selected)
