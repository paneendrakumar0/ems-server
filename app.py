import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import paho.mqtt.client as mqtt
import time
import json
import threading
from scipy.optimize import linprog
from sklearn.neural_network import MLPRegressor

# ==========================================
# 0. STREAMLIT PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Smart EMS Digital Twin", layout="wide")

# --- THE BRIDGE: Global State for Background Thread ---
@st.cache_resource
def get_ha_state():
    return {"override": False}

ha_state = get_ha_state()

# ==========================================
# 1. MQTT BACKGROUND LISTENER (The 2-Way IoT Link)
# ==========================================
def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8")
    if payload == "ON":
        ha_state["override"] = True
    elif payload == "OFF":
        ha_state["override"] = False

@st.cache_resource
def start_mqtt_listener():
    def mqtt_listen():
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "EMS_Listener")
            client.on_message = on_message
            client.connect("127.0.0.1", 1883, 60)
            client.subscribe("home/ems/control/smart_shift/set")
            client.loop_forever()
        except Exception as e:
            pass
    listener_thread = threading.Thread(target=mqtt_listen, daemon=True)
    listener_thread.start()
    return True

# Initialize listener once
start_mqtt_listener()

# ==========================================
# 2. UI HEADER
# ==========================================
st.title("⚡ Advanced Building Energy Management System (EMS)")
st.markdown("**Developed by Paneendra Kumar | Supervised by Prof. Carlo Cecati**")

# ==========================================
# 3. SIDEBAR CONTROLS & APPLIANCE SELECTION
# ==========================================
st.sidebar.header("⚙️ System Parameters")

optimization_mode = st.sidebar.radio("EMS Brain", ["Rule-Based Heuristic", "MPC Solver (Perfect Knowledge)", "Neural Network MPC (Realistic)"])

# BI-DIRECTIONAL LOGIC: Home Assistant overrides the local checkbox
st.sidebar.markdown("---")
st.sidebar.subheader("📡 Remote Command Status")
if ha_state["override"]:
    st.sidebar.success("🟢 Home Assistant Override: ACTIVE")
    smart_shift = True
else:
    st.sidebar.info("🔴 Home Assistant Override: INACTIVE")
    smart_shift = st.sidebar.checkbox("Enable Local AI Smart Load Shifting", value=False)

st.sidebar.markdown("---")
st.sidebar.subheader("🌤️ Environmental Conditions")
weather = st.sidebar.selectbox("Weather Condition", ["Sunny (Ideal)", "Cloudy (Intermittent)", "Rainy/Winter (Low Yield)"])
pv_peak = st.sidebar.slider("PV Array Size (kWp)", 10.0, 40.0, 25.0, 1.0)

st.sidebar.markdown("---")
st.sidebar.subheader("🔌 Household Appliances")
APPLIANCE_LIB = {
    'Refrigerator (Always On)': {'profile': np.array([0.2]*24), 'shiftable': False},
    'HVAC / Heat Pump': {'profile': np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.5, 2.0, 2.0, 2.0, 2.5, 3.0, 3.0, 3.0, 3.0, 3.0, 2.5, 2.0, 2.0, 2.0, 1.5, 1.5, 1.0, 1.0, 1.0]), 'shiftable': False},
    'Electric Water Heater': {'profile': np.array([0,0,0,0,0,3.0,3.0,0,0,0,0,0,0,0,0,0,0,0,3.0,3.0,0,0,0,0]), 'shiftable': True, 'power': 3.0, 'duration': 4},
    'Washing Machine': {'profile': np.array([0,0,0,0,0,0,0,0,0,0,2.0,2.0,0,0,0,0,0,0,0,0,0,0,0,0]), 'shiftable': True, 'power': 2.0, 'duration': 2},
    'Clothes Dryer': {'profile': np.array([0,0,0,0,0,0,0,0,0,0,0,0,3.0,3.0,0,0,0,0,0,0,0,0,0,0]), 'shiftable': True, 'power': 3.0, 'duration': 2},
    'Dishwasher': {'profile': np.array([0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1.5,1.5,0]), 'shiftable': True, 'power': 1.5, 'duration': 2},
    'Induction Cooktop (Dinner)': {'profile': np.array([0]*18 + [3.5, 3.5] + [0]*4), 'shiftable': False},
    'Electric Oven (Baking)': {'profile': np.array([0]*19 + [2.5] + [0]*4), 'shiftable': False},
    'Entertainment Center / TV': {'profile': np.array([0]*18 + [0.4]*4 + [0]*2), 'shiftable': False},
    'Sim Racing / Gaming Rig': {'profile': np.array([0]*20 + [0.8]*3 + [0]*1), 'shiftable': False},
    'CAD Workstation / 3D Printer': {'profile': np.array([0]*14 + [0.6]*6 + [0]*4), 'shiftable': False},
    'Pool Pump': {'profile': np.array([0]*2 + [1.5]*6 + [0]*16), 'shiftable': True, 'power': 1.5, 'duration': 6},
}

default_devices = ['Refrigerator (Always On)', 'HVAC / Heat Pump', 'Electric Water Heater', 'Washing Machine', 'Dishwasher', 'Induction Cooktop (Dinner)', 'Sim Racing / Gaming Rig']
selected_devices = st.sidebar.multiselect("Active Devices", list(APPLIANCE_LIB.keys()), default=default_devices)

st.sidebar.markdown("---")
st.sidebar.subheader("🔋 Stationary Battery")
house_bat_cap = st.sidebar.slider("Capacity (kWh)", 10.0, 50.0, 30.0, step=5.0)

st.sidebar.markdown("---")
st.sidebar.subheader("🚗 Electric Vehicle (V2G)")
ev_capacity = st.sidebar.slider("EV Battery Capacity (kWh)", 30.0, 100.0, 60.0, step=5.0)
ev_arrival = st.sidebar.slider("EV Arrival Time (Hour)", 12, 23, 18)
ev_departure = st.sidebar.slider("EV Departure Time (Hour)", 0, 11, 7)
ev_initial_soc = st.sidebar.slider("EV Arrival Charge (%)", 10, 100, 80, step=10) / 100.0

st.sidebar.markdown("---")
st.sidebar.subheader("📡 Hardware Deployment")
mqtt_broker = st.sidebar.text_input("MQTT Broker IP", value="127.0.0.1")
run_broadcast = st.sidebar.button("🚀 Broadcast to Home Assistant")

# ==========================================
# 4. NEURAL NETWORK TRAINING (The ML Forecaster)
# ==========================================
@st.cache_resource
def train_neural_network(pv_peak_val):
    np.random.seed(42)
    X_train, y_train = [], []
    for day in range(60):
        w_type = np.random.choice([0, 1, 2])
        for h in range(24):
            if w_type == 0:
                pv = np.clip(pv_peak_val * np.sin(np.pi * (h - 6) / 12), 0, None)
            elif w_type == 1:
                pv = np.clip((pv_peak_val * 0.6) * np.sin(np.pi * (h - 6) / 12), 0, None) * np.random.uniform(0.5, 1.0)
            else:
                pv = np.clip((pv_peak_val * 0.25) * np.sin(np.pi * (h - 7) / 10), 0, None)
            X_train.append([h, w_type])
            y_train.append(pv + np.random.normal(0, 0.5)) 
            
    model = MLPRegressor(hidden_layer_sizes=(32, 16), max_iter=1000, random_state=42)
    model.fit(X_train, y_train)
    return model

nn_model = train_neural_network(pv_peak)

# ==========================================
# 5. ENVIRONMENT & PREDICTIONS
# ==========================================
hours = np.arange(24)
tou_rates = np.array([0.10]*7 + [0.20]*11 + [0.35]*4 + [0.10]*2)
export_rate = 0.08 

if weather == "Sunny (Ideal)":
    pv_gen_actual = np.clip(pv_peak * np.sin(np.pi * (hours - 6) / 12), 0, None)
    w_code = 0
elif weather == "Cloudy (Intermittent)":
    base_pv = np.clip((pv_peak * 0.6) * np.sin(np.pi * (hours - 6) / 12), 0, None)
    pv_gen_actual = base_pv * np.random.uniform(0.4, 1.0, size=24)
    w_code = 1
elif weather == "Rainy/Winter (Low Yield)":
    pv_gen_actual = np.clip((pv_peak * 0.25) * np.sin(np.pi * (hours - 7) / 10), 0, None)
    w_code = 2

X_predict = [[h, w_code] for h in hours]
pv_gen_predicted = np.clip(nn_model.predict(X_predict), 0, None)

appliance_loads = {}
base_unshifable_load = np.zeros(24)
shiftable_queue = []

for device in selected_devices:
    data = APPLIANCE_LIB[device]
    if data['shiftable'] and smart_shift:
        shiftable_queue.append(device)
        appliance_loads[device] = np.zeros(24) 
    else:
        appliance_loads[device] = data['profile'].copy()
        base_unshifable_load += data['profile']

if smart_shift and shiftable_queue:
    net_power = pv_gen_predicted - base_unshifable_load
    for device in shiftable_queue:
        req_dur = APPLIANCE_LIB[device]['duration']
        req_pow = APPLIANCE_LIB[device]['power']
        best_hours = np.argsort(net_power)[::-1]
        hours_allocated = 0
        for h in best_hours:
            if hours_allocated < req_dur:
                appliance_loads[device][h] = req_pow
                net_power[h] -= req_pow 
                hours_allocated += 1

total_load = sum(appliance_loads.values()) if appliance_loads else np.zeros(24)
results = []

class StorageSystem:
    def __init__(self, capacity_kwh, max_power_kw, initial_soc=0.5):
        self.capacity = capacity_kwh
        self.max_power = max_power_kw
        self.energy = capacity_kwh * initial_soc  
        
    def get_soc(self):
        return self.energy / self.capacity
        
    def charge(self, power_available, dt=1):
        power_to_take = min(power_available, self.max_power)
        actual_energy_taken = min(power_to_take * dt, self.capacity - self.energy)
        self.energy += actual_energy_taken
        return actual_energy_taken / dt 
        
    def discharge(self, power_needed, dt=1, min_soc=0.1):
        power_to_give = min(power_needed, self.max_power)
        available_energy = max(0, self.energy - (self.capacity * min_soc))
        actual_energy_given = min(power_to_give * dt, available_energy)
        self.energy -= actual_energy_given
        return actual_energy_given / dt 

if optimization_mode == "Rule-Based Heuristic":
    house_battery = StorageSystem(capacity_kwh=house_bat_cap, max_power_kw=10, initial_soc=0.2) 
    ev_battery = StorageSystem(capacity_kwh=ev_capacity, max_power_kw=11, initial_soc=ev_initial_soc)    
    for t in hours:
        p_pv = pv_gen_actual[t]
        p_load = total_load[t] if isinstance(total_load, np.ndarray) else 0
        ev_plugged_in = (t >= ev_arrival) or (t <= ev_departure)
        p_battery = p_v2g = p_grid = cost_hour = 0
        net_l = p_load - p_pv 
        
        if net_l > 0: 
            p_battery = house_battery.discharge(net_l)
            shortfall = net_l - p_battery
            if shortfall > 0 and ev_plugged_in:
                p_v2g = ev_battery.discharge(shortfall, min_soc=0.5) 
                shortfall -= p_v2g
            p_grid = shortfall
            cost_hour = p_grid * tou_rates[t] 
        elif net_l < 0: 
            surplus = abs(net_l)
            p_battery_charge = house_battery.charge(surplus)
            surplus -= p_battery_charge
            p_battery = -p_battery_charge 
            if surplus > 0 and ev_plugged_in:
                p_ev_charge = ev_battery.charge(surplus)
                surplus -= p_ev_charge
                p_v2g = -p_ev_charge
            p_grid = -surplus 
            cost_hour = p_grid * export_rate 

        results.append({
            'Hour': int(t), 'Load': float(p_load), 'PV': float(p_pv), 'Battery': float(p_battery), 'V2G': float(p_v2g), 
            'Grid': float(p_grid), 'House_SoC': float(house_battery.get_soc() * 100), 
            'EV_SoC': float(ev_battery.get_soc() * 100), 'Grid_Cost': float(cost_hour)
        })

else:
    if optimization_mode == "MPC Solver (Perfect Knowledge)":
        optimizer_pv = pv_gen_actual 
    else:
        optimizer_pv = pv_gen_predicted 
        
    net_demand_forecast = total_load - optimizer_pv
    
    c = np.concatenate([tou_rates, -export_rate * np.ones(24), np.zeros(24), np.zeros(24)])
    A_eq = []
    b_eq = []
    for t in range(24):
        eq = np.zeros(96)
        eq[t] = 1 
        eq[24+t] = -1 
        eq[48+t] = 1 
        eq[72+t] = 1 
        A_eq.append(eq)
        b_eq.append(net_demand_forecast[t])
    
    bounds = []
    for t in range(24): bounds.append((0, 50))
    for t in range(24): bounds.append((0, 50))
    for t in range(24): bounds.append((-10, 10))
    for t in range(24):
        if (t >= ev_arrival) or (t <= ev_departure):
            bounds.append((-11, 11))
        else:
            bounds.append((0, 0))
            
    res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    
    house_soc = 0.2 * house_bat_cap
    ev_soc = ev_initial_soc * ev_capacity
    
    for t in range(24):
        p_bat_planned = res.x[48+t] if res.success else 0
        p_v2g_planned = res.x[72+t] if res.success else 0
        
        house_soc -= p_bat_planned
        house_soc = np.clip(house_soc, 0.1*house_bat_cap, house_bat_cap)
        ev_soc -= p_v2g_planned
        ev_soc = np.clip(ev_soc, 0.5*ev_capacity, ev_capacity)
        
        actual_net = total_load[t] - pv_gen_actual[t]
        p_grid_actual = actual_net + p_bat_planned + p_v2g_planned
        
        if p_grid_actual >= 0:
            cost_hour = p_grid_actual * tou_rates[t]
        else:
            cost_hour = p_grid_actual * export_rate
        
        results.append({
            'Hour': int(t), 'Load': float(total_load[t]), 'PV': float(pv_gen_actual[t]), 'Battery': float(p_bat_planned), 'V2G': float(p_v2g_planned), 
            'Grid': float(p_grid_actual), 'House_SoC': float((house_soc/house_bat_cap) * 100), 
            'EV_SoC': float((ev_soc/ev_capacity) * 100), 'Grid_Cost': float(cost_hour)
        })

df = pd.DataFrame(results)

# ==========================================
# 6. DATA ANALYSIS & VISUALIZATION
# ==========================================
plot_base_load = np.zeros(24)
plot_shift_load = np.zeros(24)

for device in selected_devices:
    if APPLIANCE_LIB[device]['shiftable']:
        plot_shift_load += appliance_loads[device]
    else:
        plot_base_load += appliance_loads[device]

st.subheader("📊 System Performance Analysis")

total_energy_needed = df['Load'].sum()
total_grid_import = df[df['Grid'] > 0]['Grid'].sum() 
total_daily_cost = df['Grid_Cost'].sum()
grid_independence = 100 * (1 - (total_grid_import / total_energy_needed)) if total_energy_needed > 0 else 100

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Home Load", f"{total_energy_needed:.1f} kWh")
col2.metric("Actual PV Generation", f"{df['PV'].sum():.1f} kWh")
col3.metric("Grid Imported", f"{total_grid_import:.1f} kWh")
col4.metric("Grid Independence", f"{grid_independence:.1f}%")
col5.metric("Daily Grid Cost", f"€{total_daily_cost:.2f}")

st.markdown("---")

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 16), sharex=True)

ax1.stackplot(hours, [plot_base_load, plot_shift_load], labels=['Fixed Base Load', 'AI-Managed Shiftable Load'], colors=['#4A90E2', '#50E3C2'], alpha=0.85)
ax1.plot(hours, df['PV'], label='Actual PV Generation (kW)', color='#F5A623', linewidth=4)
ax1.plot(hours, pv_gen_predicted, label='Neural Network Forecast (kW)', color='#bd10e0', linewidth=3, linestyle=':')
ax1.set_title(f'Dynamic Load vs. PV Generation ({weather})', fontsize=16, fontweight='bold')
ax1.set_ylabel('Power (kW)', fontsize=12)
ax1.legend(loc='upper right', fontsize=12)
ax1.grid(True, alpha=0.3)

ax2.bar(hours, df['Grid'], label='Grid Draw (+ Import / - Export)', color='#D0021B', alpha=0.7)
ax2.plot(hours, df['Battery'], label='Stationary Flow', color='#4A90E2', linewidth=2.5, marker='o')
ax2.plot(hours, df['V2G'], label='EV V2G Flow', color='#417505', linewidth=2.5, marker='s')
ax2.set_title('Energy Management System (EMS) Action', fontsize=16, fontweight='bold')
ax2.set_ylabel('Power Flow (kW)', fontsize=12)
ax2.legend(loc='upper right', fontsize=12)
ax2.axhline(0, color='black', linewidth=1)
ax2.grid(True, alpha=0.3)

ax3.plot(hours, df['House_SoC'], label='Stationary SoC (%)', color='#4A90E2', linewidth=3.5)
ax3.plot(hours, df['EV_SoC'], label='EV Battery SoC (%)', color='#417505', linewidth=3.5)
ax3.set_title('Storage Buffers State of Charge (SoC)', fontsize=16, fontweight='bold')
ax3.set_ylabel('State of Charge (%)', fontsize=12)
ax3.set_xlabel('Hour of the Day (0-23)', fontsize=14)
ax3.set_ylim(0, 105)
ax3.legend(loc='upper right', fontsize=12)
ax3.grid(True, alpha=0.3)
ax3.set_xticks(hours)

plt.tight_layout()
st.pyplot(fig)

# ==========================================
# 7. MQTT BROADCAST ROUTINE
# ==========================================
if run_broadcast:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "EMS_Digital_Twin_Pub")
    try:
        client.connect(mqtt_broker, 1883, 60)
        client.publish("home/ems/control/smart_shift/state", "ON" if smart_shift else "OFF", retain=True)

        st.info("📡 Connecting to MQTT Broker...")
        st.success(f"Connected to Broker at {mqtt_broker}. Broadcasting 24-hour cycle...")
        live_data_box = st.empty()
        
        for hour_data in results:
            client.publish("home/ems/hour", hour_data['Hour'])
            client.publish("home/ems/load", hour_data['Load'])
            client.publish("home/ems/pv", hour_data['PV'])
            client.publish("home/ems/grid", hour_data['Grid'])
            client.publish("home/ems/house_soc", hour_data['House_SoC'])
            client.publish("home/ems/ev_soc", hour_data['EV_SoC'])
            client.publish("home/ems/cost", hour_data['Grid_Cost'])
            live_data_box.code(f"Transmitting Data for Hour {hour_data['Hour']}:\n" + 
                               json.dumps(hour_data, indent=2), language='json')
            time.sleep(1)
        client.disconnect()
        st.success("✅ 24-Hour Broadcast Complete!")
    except Exception as e:
        st.error(f"❌ Connection Failed: {e}. Is Mosquitto running on your machine?")