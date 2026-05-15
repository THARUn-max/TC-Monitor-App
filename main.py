import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import io

# --- PAGE SETUP ---
st.set_page_config(page_title="Industrial TC Monitor", layout="wide")
st.title("🏗️ TC System: Variable 12-Cycle Monitor")

# --- REAL PRESENT TIME FOR DEFAULTS ---
now = datetime.now()
current_hour = now.strftime("%I")       
current_minute = now.strftime("%M")     
current_period = now.strftime("%p")     

# --- SIDEBAR CONTROL PANEL ---
st.sidebar.header("1. Baseline Setup")
u_date = st.sidebar.date_input("Start Date", now.date())

st.sidebar.subheader("Set Start Time")
col1, col2, col3 = st.sidebar.columns([2, 2, 2])

hour_list = [f"{i:02d}" for i in range(1, 13)]
try: default_hour_idx = hour_list.index(current_hour)
except ValueError: default_hour_idx = 0

with col1:
    hour_choice = st.selectbox("Hour", hour_list, index=default_hour_idx)

minute_list = [f"{i:02d}" for i in range(0, 60, 1)]
try: default_minute_idx = minute_list.index(current_minute)
except ValueError: default_minute_idx = 0

with col2:
    minute_choice = st.selectbox("Minute", minute_list, index=default_minute_idx)

period_list = ["AM", "PM"]
try: default_period_idx = period_list.index(current_period)
except ValueError: default_period_idx = 0

with col3:
    period_choice = st.selectbox("AM/PM", period_list, index=default_period_idx)

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

    for c in range(1, 13): 
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

# --- IMMEDIATE GRAPH GENERATION AND DISPLAY ---
if generate_btn:
    time_string = f"{hour_choice}:{minute_choice} {period_choice}"
    u_time = datetime.strptime(time_string, "%I:%M %p").time()
    
    df = generate_custom_data(u_time)
    
    # Matplotlib Industrial Plotting Configuration
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(24, 10))
    
    # Plot profile line
    ax.plot(df['Time'], df['Temp'], color='#00FFCC', linewidth=2, marker='o', markersize=4, alpha=0.8)

    # Big Date Headers logic across midnight transitions
    unique_days = df['Time'].dt.date.unique()
    for day in unique_days:
        day_data = df[df['Time'].dt.date == day]
        center_time = day_data['Time'].iloc[len(day_data)//2]
        ax.text(center_time, 74, day.strftime('%B %d, %Y'), 
                color='white', fontsize=14, fontweight='bold', ha='center',
                bbox=dict(facecolor='#333333', alpha=0.5, edgecolor='none', pad=6))
        
        midnight = datetime.combine(day, datetime.min.time())
        if midnight > df['Time'].min():
            ax.axvline(x=midnight, color='white', linestyle=':', alpha=0.3)

    # --- UNIFIED 45-DEGREE TIMESTAMPS OVERLAY ---
    for i, row in df.iterrows():
        ts = row['Time'].strftime('%I:%M %p')
        
        if row['Type'] == 'Start':
            # Initial Ambient timestamp annotation positioning
            ax.annotate(f"{ts}\n(Ambient)", (row['Time'], row['Temp']), textcoords="offset points", 
                        xytext=(-12, 15), rotation=45, fontsize=10, color='#FFFFFF', fontweight='bold', ha='right', va='bottom')
                        
        elif row['Type'] == 'End':
            # Final Shutdown timestamp annotation positioning
            ax.annotate(f"{ts}\n(Shutdown)", (row['Time'], row['Temp']), textcoords="offset points", 
                        xytext=(12, 15), rotation=45, fontsize=10, color='#FFFFFF', fontweight='bold', ha='left', va='bottom')
                        
        elif row['Type'] == 'DwellStart':
            # Dynamic alignment for Dwell Start points (shifts left)
            y_offset = 12 if row['Temp'] > 0 else -24
            ax.annotate(ts, (row['Time'], row['Temp']), textcoords="offset points", 
                        xytext=(-8, y_offset), rotation=45, fontsize=9, color='#FFCC00', fontweight='bold', ha='right')
                        
        elif row['Type'] == 'DwellEnd':
            # Dynamic alignment for Dwell End points (shifts right)
            y_offset = 12 if row['Temp'] > 0 else -24
            ax.annotate(ts, (row['Time'], row['Temp']), textcoords="offset points", 
                        xytext=(8, y_offset), rotation=45, fontsize=9, color='#FFCC00', fontweight='bold', ha='left')

    # Graph Boundary Constraints & Label Mapping
    ax.set_ylim(-45, 85)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))
    ax.set_ylabel("Temperature (°C)", fontsize=12)
    
    # Reference limits
    ax.axhline(y=55, color='red', linestyle='--', alpha=0.4)
    ax.text(df['Time'].min(), 57, 'PEAK TEMPERATURE LIMIT (55°C)', color='red', fontsize=10, fontweight='bold')
    
    ax.axhline(y=-30, color='cyan', linestyle='--', alpha=0.4)
    ax.text(df['Time'].min(), -34, 'MINIMUM TEMPERATURE LIMIT (-30°C)', color='cyan', fontsize=10, fontweight='bold')
    
    ax.grid(True, alpha=0.05)

    # Show chart on web screen immediately
    st.pyplot(fig)

    # Handle file downloads immediately underneath the image
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    
    st.download_button(
        label="📥 Download Profile Graph", 
        data=buf.getvalue(), 
        file_name=f"TC_Report_{u_date}.png", 
        mime="image/png"
    )
else:
    st.info("👋 System Ready. Configure your workspace parameters in the sidebar panel and select 'Generate Profile Graph' to view the profile.")
