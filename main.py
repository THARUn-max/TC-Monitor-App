import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import io

# --- PAGE SETUP ---
st.set_page_config(page_title="Varuna TC Monitor", layout="wide")
st.title("🚢 Varuna BBRx System: Thermal Cycle Monitor")

# --- DATA ENTRY SECTION ---
st.sidebar.header("1. Baseline Setup")
u_date = st.sidebar.date_input("Start Date", datetime.now().date())

# --- NATIVE CLOCK DIAGRAM EXPERIENCE ---
st.sidebar.subheader("Set Start Time")
# We use a text/html wrapper to inject a native browser clock picker that forces a 12-hour AM/PM overlay interface
time_picker_html = """
<input type="time" id="appt-time" name="appt-time" step="60"
       style="width: 100%; padding: 10px; background-color: #262730; color: white; border: 1px solid #464855; border-radius: 4px; font-size: 16px;">
"""

# Because Streamlit inputs run server-side, using the built-in time_input component 
# is the most stable way to invoke the device's native graphical clock wheel/face overlay:
u_time = st.sidebar.time_input("Tap to open Clock Diagram", value=None)

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
    # Check if the user has actually interacted with and picked a time yet
    if u_time is None:
        st.error("⚠️ Data Entry Error: Please tap the clock picker and select a valid start time before generating the profile.")
    else:
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
            
            # Line indicator for midnight boundary crossings
            midnight = datetime.combine(day, datetime.min.time())
            if midnight > df['Time'].min():
                ax.axvline(x=midnight, color='white', linestyle=':', alpha=0.3)

        # Left/Right 12-Hour Diagonal Timeline Marker Annotations
        for i, row in df.iterrows():
            ts = row['Time'].strftime('%I:%M %p')
            x_off, ha = (-12, 'right') if row['Type'] == 'DwellStart' else (12, 'left')
            ax.annotate(ts, (row['Time'], row['Temp']), textcoords="offset points", 
                        xytext=(x_off, 12), rotation=45, fontsize=9, color='#FFCC00', fontweight='bold', ha=ha)

        # Contextual pointer labels
        ax.annotate('Ambient (25°C)', (df['Time'].iloc[0], 25.0), textcoords="offset points", 
                    xytext=(-15, -25), color='#FFFFFF', fontweight='bold', arrowprops=dict(arrowstyle="->", color='white'))
        
        ax.annotate('Shutdown (25°C)', (df['Time'].iloc[-1], 25.0), textcoords="offset points", 
                    xytext=(15, -25), color='#FFFFFF', fontweight='bold', arrowprops=dict(arrowstyle="->", color='white'))

        # Graph Boundary Constraints & Label Mapping
        ax.set_ylim(-45, 85)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))
        ax.set_ylabel("Temperature (°C)", fontsize=12)
        
        # Peak Temperature Reference Line
        ax.axhline(y=55, color='red', linestyle='--', alpha=0.4)
        ax.text(df['Time'].min(), 57, 'PEAK TEMPERATURE LIMIT (55°C)', color='red', fontsize=10, fontweight='bold')
        
        # Minimum Temperature Reference Line
        ax.axhline(y=-30, color='cyan', linestyle='--', alpha=0.4)
        ax.text(df['Time'].min(), -34, 'MINIMUM TEMPERATURE LIMIT (-30°C)', color='cyan', fontsize=10, fontweight='bold')
        
        # Display the built diagram
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
    st.warning("⚠️ Waiting for user input. Please tap the clock widget in the sidebar to open the visual layout, choose your start time, and hit 'Generate Profile Graph'.")
