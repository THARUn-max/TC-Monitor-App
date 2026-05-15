import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import io

# --- PAGE SETUP ---
st.set_page_config(page_title="Varuna TC Monitor", layout="wide")
st.title("🚢 Varuna BBRx System: TC 12-Cycle Monitor")

# --- DATA ENTRY SECTION ---
st.sidebar.header("1. Baseline Setup")
u_date = st.sidebar.date_input("Start Date", datetime(2026, 5, 15))

# This widget triggers the native mobile/browser interactive clock layout diagram
u_time = st.sidebar.time_input("Select Start Time", datetime.strptime("21:40", "%H:%M").time())

st.sidebar.header("2. Profile Configuration")
u_ramp = st.sidebar.number_input("Ramp Rate (°C/min)", value=1.0, min_value=0.1, step=0.1, format="%.1f")
u_dwell_low = st.sidebar.number_input("Low Dwell Duration (minutes)", value=10, min_value=1, step=1)
u_dwell_high = st.sidebar.number_input("High Dwell Duration (minutes)", value=10, min_value=1, step=1)

# Trigger button for generation
generate_btn = st.sidebar.button("Generate Profile Graph", type="primary")

# --- CALCULATOR ENGINE ---
def generate_custom_data():
    start_dt = datetime.combine(u_date, u_time)
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
        
        # 3. Ramp Up to 55°C
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

# --- GRAPH GENERATION & DISPLAY ---
if generate_btn:
    df = generate_custom_data()
    
    # Matplotlib Industrial Plotting
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(24, 10))
    ax.plot(df['Time'], df['Temp'], color='#00FFCC', linewidth=2, marker='o', markersize=4, alpha=0.8)

    # Big Date Headers logic
    unique_days = df['Time'].dt.date.unique()
    for day in unique_days:
        day_data = df[df['Time'].dt.date == day]
        center_time = day_data['Time'].iloc[len(day_data)//2]
        ax.text(center_time, 70, day.strftime('%B %d, %Y'), 
                color='white', fontsize=14, fontweight='bold', ha='center',
                bbox=dict(facecolor='#333333', alpha=0.5, edgecolor='none', pad=6))
        
        # Line indicator for midnight change
        midnight = datetime.combine(day, datetime.min.time())
        if midnight > df['Time'].min():
            ax.axvline(x=midnight, color='white', linestyle=':', alpha=0.3)

    # Left/Right 12-Hour Diagonal Labels
    for i, row in df.iterrows():
        ts = row['Time'].strftime('%I:%M %p')
        x_off, ha = (-12, 'right') if row['Type'] == 'DwellStart' else (12, 'left')
        ax.annotate(ts, (row['Time'], row['Temp']), textcoords="offset points", 
                    xytext=(x_off, 12), rotation=45, fontsize=9, color='#FFCC00', fontweight='bold', ha=ha)

    # Graph Bounds & Limits
    ax.set_ylim(-45, 85)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))
    ax.set_ylabel("Temperature (°C)", fontsize=12)
    ax.axhline(y=55, color='red', linestyle='--', alpha=0.25)
    ax.axhline(y=-30, color='cyan', linestyle='--', alpha=0.25)
    ax.grid(True, alpha=0.05)

    # Show chart on web screen
    st.pyplot(fig)

    # Buffer data handling to allow download
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    
    st.download_button(
        label="📥 Download Tailored Profile Graph", 
        data=buf.getvalue(), 
        file_name=f"Custom_TC_Report_{u_date}.png", 
        mime="image/png"
    )
else:
    # Display current selection in 12-hour AM/PM format on the dashboard greeting
    formatted_preview = u_time.strftime('%I:%M %p')
    st.info(f"👋 System Ready. Current configuration targets a start at {formatted_preview}. Click 'Generate Profile Graph' to update.")
