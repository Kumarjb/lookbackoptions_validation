#!/usr/bin/env python
# coding: utf-8

# In[5]:


import numpy as np
import pandas as pd
import pyarrow as pa
from qablet_contracts.timetable import py_to_ts
from qablet_contracts.timetable import TS_EVENT_SCHEMA
from localvol import LVMCModel

# Creating a look-back put option timetable with custom lookbacks
def lookback_put_timetable(ticker, strike, start_date, maturity, num_points):
    fix_dates = pd.date_range(start=start_date, end=maturity, periods=num_points)
    events = [
        {
            "track": "",
            "time": fix_dates[0],
            "op": None,
            "quantity": 0,
            "unit": "INIT",
        }
    ]
    
    for fixing_time in fix_dates[1:]:
        events.append(
            {
                "track": "",
                "time": fixing_time,
                "op": None,
                "quantity": 0,
                "unit": "UPDATE",  
            }
        )
    
    events.append(
        {
            "track": "",
            "time": maturity,
            "op": None,
            "quantity": 0,
            "unit": "FIX",  
        }
    )
    
    events.append(
        {
            "track": "",
            "time": maturity,
            "op": "+",
            "quantity": 1,
            "unit": "LOOKBACK", 
        }
    )
    # Defining look-back put payoff function

    def lookback_put_pay_fn(inputs):
        [s_min, k] = inputs
        return [np.maximum(k - s_min, 0)]

    # Defining the strike phrase, which is a fixed strike price
    def strike_fn(inputs):
        return [strike]

    events_table = pa.RecordBatch.from_pylist(events, schema=TS_EVENT_SCHEMA)
    return {
        "events": events_table,
        "expressions": {
            "LOOKBACK": {
                "type": "phrase",
                "inp": ["MIN_PRICE", "K"],
                "fn": lookback_put_pay_fn,
            },
            "UPDATE": {
                "type": "snapper",
                "inp": [ticker, "MIN_PRICE"],
                "fn": lambda inputs: [np.minimum(inputs[0], inputs[1])],
                "out": ["MIN_PRICE"],
            },
            "INIT": {
                "type": "snapper",
                "inp": [ticker],
                "fn": lambda inputs: [inputs[0]],
                "out": ["MIN_PRICE"],
            },
            "FIX": {
                "type": "snapper",
                "inp": [ticker],
                "fn": strike_fn,
                "out": ["K"],
            },
        },
    }

MC_PARAMS = {
    "PATHS": 100_000,
    "TIMESTEP": 1 / 250,
    "SEED": 1,
}

# Provided data functions
def basic_info():

    return {
        "prc_dt": datetime(2005, 9, 14),
        "ticker": "SPX",
        "ccy": "USD",
        "spot": 100,  # Using spot price as 100
    }

def assets_data(rate=0.1):
    info = basic_info()

    div_rate = 0.02
    times = np.array([0.0, 5.0])
    rates = np.array([rate, rate])
    discount_data = ("ZERO_RATES", np.column_stack((times, rates)))

    fwds = info["spot"] * np.exp((rates - div_rate) * times)
    fwd_data = ("FORWARDS", np.column_stack((times, fwds)))

    return {info["ccy"]: discount_data, info["ticker"]: fwd_data}

def localvol_data(rate=0.1, vol_file="spx_svi_2005_09_15.csv"):
    info = basic_info()

    svidf = pd.read_csv(vol_file)

    return {
        "BASE": "USD",
        "PRICING_TS": py_to_ts(info["prc_dt"]).value,
        "ASSETS": assets_data(rate=rate),
        "MC": MC_PARAMS,
        "LV": {"ASSET": "SPX", "VOL": svidf},
    }

# Validation of Local Vol for parameters S0=100, r=0.1, T=0.2 Yrs, m=4
ticker = "SPX"
strike = 100 
start_date = datetime(2005, 9, 14)
maturity = start_date + timedelta(days=0.2*365)  # T = 0.2 years
num_points = 4  

# Creating a look-back put option timetable
timetable = lookback_put_timetable(ticker, strike, start_date, maturity, num_points)
print(timetable["events"].to_pandas())

# Pricing with Local Volatility Model
localvol_dataset = localvol_data(rate=0.1, vol_file="spx_svi_2005_09_15.csv")  
localvol_model = LVMCModel()  
price, _ = localvol_model.price(timetable, localvol_dataset)
print(f"LocalVol put price for Table 2 parameters: {price}")

# Validation of Local Vol for parameters S0=100, r=0.1, T=0.5yrs with varying m
m_values = [5, 10, 20, 40, 80, 160]  
maturity = start_date + timedelta(days=0.5*365)  # T = 0.5 years

for m in m_values:
    timetable = lookback_put_timetable(ticker, strike, start_date, maturity, m)
    print(f"\nTimetable for m={m}:\n", timetable["events"].to_pandas())

    # Pricing with Local Volatility Model
    price, _ = localvol_model.price(timetable, localvol_dataset)
    print(f"LocalVol put price for m={m}: {price}")


# In[ ]:




