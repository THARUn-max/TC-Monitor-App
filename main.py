import flet as ft
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import io
import base64

# --- CALCULATOR ENGINE ---
def calculate_tc_data(start_date, start_time):
    start_dt = datetime.combine(start_date, start_time)
    data = []
    curr_time, curr_temp = start_dt, 25.0
    
    # Point 0
    data.append({'Time': curr_time, 'Temp': curr_temp, 'Type': 'Start'})

    for c in range(1, 13):
        # 1. Ramp down to -30
        curr_time += timedelta(minutes=abs(curr_temp - (-30.0)))
        curr_temp = -30.0
        data.append({'Time': curr_time, 'Temp': curr_temp, 'Type': 'DwellStart'})
        # 2. Dwell Low (10m)
        curr_time += timedelta(minutes=10)
        data.append({'Time': curr_time, 'Temp': curr_temp, 'Type': 'DwellEnd'})
        # 3. Ramp up to 55
        curr_time += timedelta(minutes=abs(curr_temp - 55.0))
        curr_temp = 55.0
        data.append({'Time': curr_time, 'Temp': curr_temp, 'Type': 'DwellStart'})
        # 4. Dwell High (10m)
        curr_time += timedelta(minutes=10)
        data.append({'Time': curr_time, 'Temp': curr_temp, 'Type': 'DwellEnd'})

    # Shutdown
    curr_time += timedelta(minutes=abs(curr_temp - 25.0))
    data.append({'Time': curr_time, 'Temp': 25.0, 'Type': 'End'})
    return pd.DataFrame(data)

# --- APP UI ---
def main(page: ft.Page):
    page.title = "TC System Monitor"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 450
    page.padding = 20

    # Local State
    state = {"date": datetime.now().date(), "time": datetime.now().time()}

    # UI Elements
    title = ft.Text("INDUSTRIAL TC MONITOR", size=24, weight="bold", color="cyan")
    status = ft.Text("Set Start Parameters", color="yellow")
    graph_container = ft.Column(visible=False)

    # Date/Time Selection Handlers
    def handle_date(e):
        state["date"] = e.control.value.date()
        btn_date.text = f"Date: {state['date'].strftime('%d %b %Y')}"
        page.update()

    def handle_time(e):
        state["time"] = e.control.value
        btn_time.text = f"Time: {state['time'].strftime('%I:%M %p')}"
        page.update()

    d_picker = ft.DatePicker(on_change=handle_date)
    t_picker = ft.TimePicker(on_change=handle_time)
    page.overlay.extend([d_picker, t_picker])

    btn_date = ft.OutlinedButton("Select Date", icon=ft.icons.CALENDAR_MONTH, on_click=lambda _: d_picker.pick_date())
    btn_time = ft.OutlinedButton("Select Time", icon=ft.icons.ACCESS_TIME, on_click=lambda _: t_picker.pick_time())

    def draw_graph(e):
        df = calculate_tc_data(state["date"], state["time"])
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(15, 8))
        
        # Plotting the Cyan line
        ax.plot(df['Time'], df['Temp'], color='#00FFCC', linewidth=2, marker='o', markersize=3)
        
        # Horizontal Date Headers
        for day in df['Time'].dt.date.unique():
            day_data = df[df['Time'].dt.date == day]
            ax.text(day_data['Time'].iloc[len(day_data)//2], 72, day.strftime('%B %d, %Y'), 
                    ha='center', fontweight='bold', bbox=dict(facecolor='#333333', alpha=0.5))

        # Diagonal 12hr Labels
        for i, row in df.iterrows():
            ts = row['Time'].strftime('%I:%M %p')
            x_off, ha = (-12, 'right') if row['Type'] == 'DwellStart' else (12, 'left')
            ax.annotate(ts, (row['Time'], row['Temp']), textcoords="offset points", 
                        xytext=(x_off, 12), rotation=45, fontsize=8, color='#FFCC00', fontweight='bold', ha=ha)

        ax.set_ylim(-45, 85)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))
        ax.axhline(y=55, color='red', linestyle='--', alpha=0.3)
        ax.axhline(y=-30, color='cyan', linestyle='--', alpha=0.3)
        
        # Convert to Image for Flet
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        
        graph_container.controls = [ft.Image(src_base64=img_base64, border_radius=10)]
        graph_container.visible = True
        status.value = "Profile Generated"
        page.update()

    btn_gen = ft.ElevatedButton("GENERATE GRAPH", on_click=draw_graph, bgcolor="cyan", color="black")

    page.add(
        title,
        status,
        ft.Row([btn_date, btn_time], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(),
        ft.Center(btn_gen),
        ft.Divider(),
        graph_container
    )

ft.app(target=main)
