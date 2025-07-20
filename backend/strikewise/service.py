# strikewise/service.py

from strikewise.models import AnalysisRequest, AnalysisResponse
from strikewise.utils import (
    compute_option_risk_reward_all_strikes,
    get_nifty_spot_price,
    get_live_option_chain,
    select_best_contracts
)
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from pathlib import Path
import numpy as np

# Load .env and extract access token
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
if not ACCESS_TOKEN:
    raise RuntimeError("UPSTOX_ACCESS_TOKEN is missing or empty in the .env file")

INTEREST_RATE = 0.065
LOT_SIZE = 75

def run_option_analysis(request: AnalysisRequest) -> AnalysisResponse:
    print("Running option analysis for:", request.instrument_key, request.expiry_date)
    print("Received option_type:", request.option_type)

    # Fetch current spot
    current_spot = get_nifty_spot_price(ACCESS_TOKEN, request.instrument_key)
    if current_spot is None:
        raise ValueError("Failed to fetch spot price from Upstox")

    print("Current Spot:", current_spot)

    # Fetch live option chain
    option_chain_df = get_live_option_chain(ACCESS_TOKEN, request.instrument_key, request.expiry_date)
    if option_chain_df is None or option_chain_df.empty:
        raise ValueError("Failed to fetch option chain or option chain is empty")

    print("Fetched option chain with", len(option_chain_df), "rows")

    # Calculate target and stop-loss spot values
    spot_target = current_spot + request.spot_target_gain
    spot_sl = current_spot - request.spot_sl_loss
    print("Spot Target:", spot_target, "| Spot SL:", spot_sl)

    # Time to expiry in years
    expiry_datetime = datetime.strptime(f"{request.expiry_date} 15:30:00", "%Y-%m-%d %H:%M:%S")
    T = (expiry_datetime - (datetime.now() + timedelta(minutes=request.minutes_to_hit_target))).total_seconds() / (365 * 24 * 60 * 60)
    print("Time to expiry (in years):", round(T, 6))

    # Ensure numeric types
    analysis_df = option_chain_df.apply(pd.to_numeric, errors='coerce')

    # Determine which column to use
    option_type = "call" if request.option_type == "CE" else "put"
    ltp_column = f"{option_type.capitalize()} LTP"
    iv_col = "Call IV" if option_type == "call" else "Put IV"
    oi_col = "Call OI" if option_type == "call" else "Put OI"

    if ltp_column not in analysis_df.columns:
        raise ValueError(f"Missing column in option chain: {ltp_column}")

    # Prepare trade dataframe
    trade_df = analysis_df[["Strike", ltp_column, iv_col, oi_col]].rename(columns={
        ltp_column: "LTP",
        iv_col: iv_col,
        oi_col: "OI"})
    
    print("📊 Trade DF Sample:")
    print(trade_df.head(10).to_string(index=False))

    print("Prepared trade data with", len(trade_df), "rows")

    # Compute projections using BSM + estimated IV
    projections_df = compute_option_risk_reward_all_strikes(
        trade_df,
        spot_target,
        spot_sl,
        current_spot,
        T,
        INTEREST_RATE,
        LOT_SIZE,
        option_type
    )

    print("Projections computed:", len(projections_df), "rows")
    projections_df.to_csv("projections_output.csv", index=False)
    
    # Sanitize projections
    projections_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    critical_cols = ["Profit_", "Loss_", "Delta", "Gamma", "IV_Used"]
    valid_projections_df = projections_df.dropna(subset=critical_cols)

    if valid_projections_df.empty:
        print("⚠️ No valid projections. Likely due to IV backsolve failure or invalid premiums.")
        return AnalysisResponse(projections=[], selected_contracts=[])
    print(valid_projections_df.head())
    projections = valid_projections_df.to_dict(orient="records")
    print("✅ Final projections sent:", len(projections))

    # Select best contracts within capital and risk limits
    selected_contracts_df = select_best_contracts(
        valid_projections_df,
        capital=request.capital,
        risk_limit=request.risk_tolerance
    )

    selected_contracts_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    selected_contracts_df.dropna(inplace=True)
    selected_contracts = selected_contracts_df.to_dict(orient="records")
    print("✅ Final selected contracts:", len(selected_contracts))

    return AnalysisResponse(
        projections=projections,
        selected_contracts=selected_contracts
    )

