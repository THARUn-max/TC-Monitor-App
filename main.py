import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import io

# --- PAGE SETUP ---
st.set_page_config(page_title="Varuna TC Monitor", layout="wide")
st.title("🚢 Varuna System: Thermal Cycle Monitor")

# --- DATA ENTRY SECTION ---
st.sidebar.header("1. Baseline Setup")
u_date = st.sidebar.date_input("Start Date", datetime.now().date())

st.sidebar.subheader("Set Start Time")
col1, col2, col3 = st.sidebar.columns([2, 2, 2])

with col1:
    # Use a blank placeholder item as index 0 to ensure it starts empty
    hour_choice = st.selectbox("Hour", ["--", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"], index=0)
with col2:
    minute_choices = ["--"] + [f"{i:02d}" for i in range(0, 60, 5)]
    minute_choice = st.selectbox("Minute", minute_choices, index=0)
with col3:
    period_choice = st.selectbox("AM/PM", ["--", "AM", "PM"], index=0)

st.sidebar.header("2. Profile Configuration")
u_ramp = st.sidebar.number_input("Ramp Rate (°C/min)", value=1.0, min_value=0.1, step=0.1, format="%.1f")
u_dwell_low = st.sidebar.number_input("Low Dwell Duration (minutes)", value=10, min_value=1, step=1)
u_dwell_high = st.sidebar.number_input("High Dwell Duration (minutes)", value=10, min_value=1, step=1)

# Trigger button for generation
generate_btn = st.sidebar.button("Generate Profile Graph", type="primary")

# --- CALCULATOR ENGINE ---
def generate_custom_data(valid_time):
    start_dt = datetime.combine(u_date, valid_time)
    data = []
    curr_time, curr_temp = start_dt, 25.0
    data.append({'Time': curr_time, 'Temp': curr_temp, 'Type': 'Start'})

    for c in range(1, 13): # 12 Cycles
        # 1. Ramp Down to -30°C
        curr_time += timedelta(minutes=abs(curr_temp - (-30.0)) / u_ramp)
        curr_temp = -30.0
        data.append({'Time': curr_time, 'Temp': curr_temp, 'Type': 'DwellStart'})
        
        # 2. Variable Low Dwell
        curr_time += timedelta(minutes=u_dwell_low)
        data.append({'Time': curr_time, 'Temp': curr_temp, 'Type': 'DwellEnd'})
        
        # 3. Ramp Up to 55°C (Peak)
        curr_time += timedelta(minutes=abs(curr_temp - 55.0) / u_ramp)
        curr_temp = 55.0
        data.append({'Time': curr_time, 'Temp': curr_temp, 'Type': 'DwellStart'})
        
        # 4. Variable High Dwell
        curr_time += timedelta(minutes=u_dwell_high)
        data.append({'Time': curr_time, 'Temp': curr_temp, 'Type': 'DwellEnd'})

    # Final Shutdown phase back to Ambient (25°C)
    curr_time += timedelta(minutes=abs(curr_temp - 25.0) / u_ramp)
    data.append({'Time': curr_time, 'Temp': 25.0, 'Type': 'End'})
    return pd.DataFrame(data)

# --- USER INPUT ENFORCEMENT VALIDATION ---
if generate_btn:
    # Check if any of the time drop-downs are still unselected
    if hour_choice == "--" or minute_choice == "--" or period_choice == "--":
        st.error("⚠️ Data Entry Error: Please select a valid Hour, Minute, and AM/PM marker before generating the profile.")
    else:
        # If valid, clean and parse inputs
        time_string = f"{hour_choice}:{minute_choice} {period_choice}"
        u_time = datetime.strptime(time_string, "%I:%M %p").time()
        
        df = generate_custom_data(u_time)
        
        # Matplotlib Industrial Plotting
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(24, 10))
        ax.plot(df['Time'], df

