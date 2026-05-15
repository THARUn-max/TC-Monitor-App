import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import io

# --- PAGE SETUP ---
st.set_page_config(page_title="Varuna TC Monitor", layout="wide")
st.title("🚢 Varuna System: Thermal Cycle Monitor")

# --- REAL PRESENT TIME FALLBACK LOGIC ---
# Dynamically pulls the live system clock parameters on initialization
now = datetime.now()
current_hour = now.strftime("%I")       
current_minute = now.strftime("%M")     
current_period = now.strftime("%p")     

# Track if the graph has been generated to control sidebar visibility
if "generated" not in st.session_state:
    st.session_state.generated = False

# --- DYNAMIC DATA ENTRY CONTAINER ---
# If the graph is generated, the sidebar inputs fold into a closed layout to clear screen space
with st.sidebar:
    if st.session_state.generated:
        input_container = st.expander("⚙️ Adjust Profile Parameters", expanded=False)
    else:
        input_container = st.container()

with input_container:
    st.header("1. Baseline Setup")
    u_date = st.date_input("Start Date", now.date())

    st.subheader("Set Start Time")
    col1, col2, col3 = st.columns([2, 2, 2])

    hour_list = [f"{i:02d}" for i in range(1, 13)]
    try:
        default_hour_idx = hour_list.index(current_hour)
    except ValueError:
        default_hour_idx = 0

    with col1:
        hour_choice = st.selectbox("Hour", hour_list, index=default_hour_idx)

    minute_list = [f"{i:02d}" for i in range(0, 60, 1)]
    try:
        default_minute_idx = minute_list.index(current_minute)
    except ValueError:
        default_minute_idx = 0

    with col2:
        minute_choice = st.selectbox("Minute", minute_list, index=default_minute_idx)

    period_list = ["AM", "PM"]
    try:
        default_period_idx = period_list.index(current_period)
    except ValueError:
        default_period_idx = 0

    with col3:
        period_choice = st.selectbox("AM/PM", period_list, index=default_period_idx)

    st.header("2. Profile Configuration")
    u_ramp = st.number_input("Ramp Rate (°C/min)", value=1.0, min_value=0.1, step=0.1, format="%.1f")
    u_dwell_low = st.number_input("Low Dwell Duration (minutes)", value=10, min_value=1, step=1)
    u_dwell_high = st.number_input("High Dwell Duration (minutes)", value=10, min_value=1, step=1)

    generate_btn = st.button("Generate Profile Graph", type="primary")

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

# --- GRAPH RENDER MANAGEMENT ---
if generate_btn:
    st.session_state.generated = True
    st.rerun()

if st.session_state.generated:
    time_string = f"{hour_choice}:{minute_choice} {period_choice}"
    u_time = datetime.strptime(time_string, "%I:%M %p").time()
    
    df = generate_custom_data(u_time)
    
    # Matplotlib Industrial Plotting Configuration
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(24, 10))
    
    # Plot profile
    ax.plot(df['Time'], df['Temp'], color='#00FFCC', linewidth=2, marker='o', markersize=4, alpha=0.8)

    # Big Date Headers logic across midnight transitions
    unique_days = df['Time'].dt.date.unique()
    for day in unique_days:
        day_data = df[df['Time'].dt.date == day]
        center_time = day_data['Time'].iloc[len(day_data)//2]
        ax.text(center_time, 72, day.strftime('%B %d, %Y'), 
                color='white', fontsize=14, fontweight='bold', ha='center',
                bbox=dict(facecolor='#333333', alpha=0.5, edgecolor='none', pad=6))
        
        midnight = datetime.combine(day, datetime.min.time())
        if midnight > df['Time'].min():
            ax.axvline(x=midnight, color='white', linestyle=':', alpha=0.3)

    # --- ADJUSTED LABELS LOGIC WITH ENHANCED SPACING ---
    for i, row in df.iterrows():
        if row['Type'] in ['Start', 'End']:
            continue
            
        ts = row['Time'].strftime('%I:%M %p')
        
        # Shift DwellStart markers rightward/downward toward the flat line segment
        if row['Type'] == 'DwellStart':
            x_off, ha = 8, 'left'
            y_off = -15 if row['Temp'] > 0 else 8
        else:
            # Shift DwellEnd markers slightly rightward and out of the way
            x_off, ha = 6, 'left'
            y_off = 12 if row['Temp'] > 0 else -18
            
        ax.annotate(ts, (row['Time'], row['Temp']), textcoords="offset points", 
                    xytext=(x_off, y_off), rotation=45, fontsize=9, color='#FFCC00', fontweight='bold', ha=ha)

    # Explicit pointer labels pinning Initial Ambient vs Final Shutdown boundaries
    ax.annotate('Ambient (25°C)', (df['Time'].iloc[0], 25.0), textcoords="offset points", 
                xytext=(-20, 15), color='#FFFFFF', fontweight='bold', arrowprops=dict(arrowstyle="->", color='white'))
    
    ax.annotate('Shutdown (25°C)', (df['Time'].iloc[-1], 25.0), textcoords="offset points", 
                xytext=(10, 15), color='#FFFFFF', fontweight='bold', arrowprops=dict(arrowstyle="->", color='white'))

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

    # Show chart on web screen
    st.pyplot(fig)

    # Handle file downloads
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    
    st.download_button(
        label="📥 Download Profile Graph", 
        data=buf.getvalue(), 
        file_name=f"TC_Report_{u_date}.png", 
        mime="image/png"
    )
else:
    st.warning("👋 Control Panel Ready. Verify parameters match your test conditions, then hit 'Generate Profile Graph'.")
