import pandas as pd
import os

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────
CSV_FILE = "aegis_data.csv"
MAX_ROWS = 50  # Latest rows to read from CSV

# ──────────────────────────────────────────────
# COMMAND PATTERNS
# If user input contains any of these phrases,
# that command is triggered
# ──────────────────────────────────────────────
COMMANDS = {
    "summary": [
        "summary", "situation", "current status", "what is inside",
        "full report", "overall", "what has been found", "give me a report",
        "status report", "what's happening", "whats happening", "report"
    ],
    "victims": [
        "victim", "survivor", "person", "people", "how many",
        "who is inside", "bodies", "found", "detected"
    ],
    "environment": [
        "temperature", "temp", "smoke", "humidity", "environmental",
        "air quality", "heat", "conditions", "fire spread", "fire level", "fire"
    ],
    "zone": [
        "zone a", "zone b", "zone c", "zone_a", "zone_b", "zone_c"
    ],
    "hello": [
        "hello", "hi", "hey", "hello aegis", "hi aegis",
        "wake up", "start", "activate", "good morning", "yo aegis",
        "aegis", "hello robot"
    ],
    "bye": [
        "bye", "goodbye", "exit", "quit", "shutdown",
        "turn off", "deactivate", "see you", "ok bye", "that's all",
        "done", "stop"
    ],
    "help": [
        "help", "what can you do", "commands", "options",
        "what do you know", "how to use", "guide"
    ]
}

# ──────────────────────────────────────────────
# COMMAND DETECTOR
# ──────────────────────────────────────────────
def detect_command(user_input):
    text = user_input.lower().strip()
    for command, phrases in COMMANDS.items():
        for phrase in phrases:
            if phrase in text:
                return command
    return "unknown"

# ──────────────────────────────────────────────
# DATA READER
# ──────────────────────────────────────────────
def read_data():
    if not os.path.exists(CSV_FILE):
        return None, "No data file found. Make sure data_simulator.py is running."
    # df = pd.read_csv(CSV_FILE)
    df = pd.read_csv(
    "aegis_data.csv", 
    header=None, 
    names=[
        "timestamp", 
        "x_coord", 
        "y_coord", 
        "zone", 
        "victim_detected", 
        "victim_count", 
        "victim_status", 
        "fire_detected", 
        "fire_status", 
        "distance", 
        "temperature", 
        "sensor_status"
    ]
)
    if df.empty:
        return None, "Data file exists but contains no entries yet."
    return df.tail(MAX_ROWS), None

# ──────────────────────────────────────────────
# RESPONSE HANDLERS
# All pure Python — instant, accurate, no LLM
# ──────────────────────────────────────────────

def handle_hello():
    return (
        "AEGIS online.\n"
        "All systems operational.\n"
        "Awaiting rescue team queries."
    )

def handle_bye():
    return "AEGIS signing off. Stay safe."

def handle_help():
    return (
        "AEGIS — Available Commands:\n"
        "  'Give me the summary'            → Full situation report\n"
        "  'How many victims?'              → Victim count and locations\n"
        "  'Environmental report'           → Temperature, smoke, fire data\n"
        "  'Situation in Zone A / B / C'    → Zone specific report\n"
        "  'Hello' / 'Hi'                   → Activate AEGIS\n"
        "  'Bye' / 'Exit'                   → Deactivate AEGIS\n"
        "  'Help'                           → Show this menu"
    )

def handle_summary(df):
    victim_rows      = df[df["victim_detected"] == True]
    total_victims    = int(victim_rows["victim_count"].sum())
    conscious_locs   = int(victim_rows[victim_rows["victim_status"] == "conscious"].shape[0])
    unconscious_locs = int(victim_rows[victim_rows["victim_status"] == "unconscious"].shape[0])
    avg_temp         = round(df["temperature"].mean(), 1)
    max_temp         = round(df["temperature"].max(), 1)
    fire_count       = int(df[df["fire_detected"] == True].shape[0])
    high_smoke       = int(df[df["smoke_density"] == "high"].shape[0])
    zones            = df["zone"].value_counts().to_dict()
    last_updated     = df["timestamp"].iloc[-1]
    total_entries    = len(df)

    zone_str = " | ".join([f"{k}: {v} entries" for k, v in zones.items()])

    return (
        f"┌─────────────────────────────────────┐\n"
        f"│         AEGIS STATUS REPORT         │\n"
        f"└─────────────────────────────────────┘\n"
        f"  Last Updated     : {last_updated}\n"
        f"  Entries Analyzed : {total_entries}\n"
        f"\n"
        f"  VICTIMS\n"
        f"  ├─ Total Detected     : {total_victims}\n"
        f"  ├─ Conscious Spots    : {conscious_locs}\n"
        f"  └─ Unconscious Spots  : {unconscious_locs}\n"
        f"\n"
        f"  ENVIRONMENT\n"
        f"  ├─ Avg Temperature   : {avg_temp}°C\n"
        f"  ├─ Max Temperature   : {max_temp}°C\n"
        f"  ├─ High Smoke Zones  : {high_smoke} entries\n"
        f"  └─ Fire Detected In  : {fire_count} entries\n"
        f"\n"
        f"  ZONES EXPLORED\n"
        f"  └─ {zone_str}"
    )

def handle_victims(df):
    victim_rows = df[df["victim_detected"] == True]

    if victim_rows.empty:
        return "No victims detected in current data."

    total             = int(victim_rows["victim_count"].sum())
    conscious_count   = int(victim_rows[victim_rows["victim_status"] == "conscious"]["victim_count"].sum())
    unconscious_count = int(victim_rows[victim_rows["victim_status"] == "unconscious"]["victim_count"].sum())

    lines = [
        f"┌─────────────────────────────────────┐",
        f"│           VICTIM REPORT             │",
        f"└─────────────────────────────────────┘",
        f"  Total Victims   : {total}",
        f"  Conscious       : {conscious_count}",
        f"  Unconscious     : {unconscious_count}",
        f"",
        f"  VICTIM LOCATIONS:"
    ]

    for _, row in victim_rows.iterrows():
        status_tag = "CONSCIOUS" if row["victim_status"] == "conscious" else "UNCONSCIOUS"
        lines.append(
            f"  [{row['timestamp']}] "
            f"Location ({row['x_coord']}, {row['y_coord']}) | "
            f"{row['zone']} | "
            f"{int(row['victim_count'])} victim(s) | "
            f"{status_tag}"
        )

    return "\n".join(lines)

def handle_environment(df):
    avg_temp = round(df["temperature"].mean(), 1)
    max_temp = round(df["temperature"].max(), 1)
    min_temp = round(df["temperature"].min(), 1)
    avg_hum  = round(df["humidity"].mean(), 1)
    smoke    = df["smoke_density"].value_counts().to_dict()

    fire_rows = df[df["fire_detected"] == True]
    spread    = fire_rows["fire_spread"].value_counts().to_dict() if not fire_rows.empty else {}
    spread_str = " | ".join([f"{k}: {v}" for k, v in spread.items()]) if spread else "No fire detected"
    smoke_str  = " | ".join([f"{k}: {v}" for k, v in smoke.items()])

    return (
        f"┌─────────────────────────────────────┐\n"
        f"│       ENVIRONMENTAL REPORT          │\n"
        f"└─────────────────────────────────────┘\n"
        f"  TEMPERATURE\n"
        f"  ├─ Average  : {avg_temp}°C\n"
        f"  ├─ Maximum  : {max_temp}°C\n"
        f"  └─ Minimum  : {min_temp}°C\n"
        f"\n"
        f"  HUMIDITY\n"
        f"  └─ Average  : {avg_hum}%\n"
        f"\n"
        f"  SMOKE DENSITY\n"
        f"  └─ {smoke_str}\n"
        f"\n"
        f"  FIRE SPREAD\n"
        f"  └─ {spread_str}"
    )

def handle_zone(df, user_input):
    # Detect which zone was asked about
    zone_name = None
    for z in ["zone_a", "zone_b", "zone_c", "zone a", "zone b", "zone c"]:
        if z in user_input.lower():
            zone_name = z.replace(" ", "_").upper()
            break

    if not zone_name:
        return "Please specify a zone. Example: 'Situation in Zone A'"

    zone_df = df[df["zone"].str.upper() == zone_name]

    if zone_df.empty:
        return f"No data found for {zone_name} yet."

    # Compute zone stats
    latest        = zone_df.iloc[-1]
    victim_rows   = zone_df[zone_df["victim_detected"] == True]
    total_victims = int(victim_rows["victim_count"].sum())
    conscious     = int(victim_rows[victim_rows["victim_status"] == "conscious"]["victim_count"].sum())
    unconscious   = int(victim_rows[victim_rows["victim_status"] == "unconscious"]["victim_count"].sum())
    avg_temp      = round(zone_df["temperature"].mean(), 1)
    max_temp      = round(zone_df["temperature"].max(), 1)
    smoke         = zone_df["smoke_density"].value_counts().to_dict()
    smoke_str     = " | ".join([f"{k}: {v}" for k, v in smoke.items()])
    fire_entries  = int(zone_df[zone_df["fire_detected"] == True].shape[0])

    return (
        f"┌─────────────────────────────────────┐\n"
        f"│           {zone_name} REPORT{' ' * (25 - len(zone_name))}│\n"
        f"└─────────────────────────────────────┘\n"
        f"  Entries Recorded : {len(zone_df)}\n"
        f"\n"
        f"  VICTIMS\n"
        f"  ├─ Total         : {total_victims}\n"
        f"  ├─ Conscious     : {conscious}\n"
        f"  └─ Unconscious   : {unconscious}\n"
        f"\n"
        f"  ENVIRONMENT\n"
        f"  ├─ Avg Temp      : {avg_temp}°C\n"
        f"  ├─ Max Temp      : {max_temp}°C\n"
        f"  ├─ Smoke         : {smoke_str}\n"
        f"  └─ Fire Entries  : {fire_entries}\n"
        f"\n"
        f"  LAST READING\n"
        f"  ├─ Time          : {latest['timestamp']}\n"
        f"  ├─ Location      : ({latest['x_coord']}, {latest['y_coord']})\n"
        f"  ├─ Temperature   : {latest['temperature']}°C\n"
        f"  └─ Fire Present  : {latest['fire_detected']}"
    )

# ──────────────────────────────────────────────
# MAIN CHAT LOOP
# ──────────────────────────────────────────────
def run_chatbot():
    print("=" * 55)
    print("   AEGIS Tactical Chatbot — Text Mode")
    print("   Type 'help' to see available commands.")
    print("   Type 'bye' to exit.")
    print("=" * 55)
    print()

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        command = detect_command(user_input)

        # ── Instant commands (no CSV needed) ──
        if command == "hello":
            print(f"\nAEGIS:\n{handle_hello()}\n")
            continue

        if command == "bye":
            print(f"\nAEGIS: {handle_bye()}\n")
            break

        if command == "help":
            print(f"\nAEGIS:\n{handle_help()}\n")
            continue

        if command == "unknown":
            print(f"\nAEGIS: I only respond to rescue operation queries. Type 'help' to see available commands.\n")
            continue

        # ── Data commands (read CSV) ──
        df, error = read_data()

        if error:
            print(f"\nAEGIS: {error}\n")
            continue

        if command == "summary":
            response = handle_summary(df)
        elif command == "victims":
            response = handle_victims(df)
        elif command == "environment":
            response = handle_environment(df)
        elif command == "zone":
            response = handle_zone(df, user_input)
        else:
            response = "I only respond to rescue operation queries. Type 'help' to see available commands."

        print(f"\nAEGIS:\n{response}\n")

# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────
if __name__ == "__main__":
    run_chatbot()
