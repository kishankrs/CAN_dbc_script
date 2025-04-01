"""
============================================
CAN - Matrix CSV to DBC Converter Script
Author: Kishan Kumar
Version: 2.0
Date: 2025-04-01
Description: 
    This script converts a CAN signal matrix from a CSV file into a DBC file.
    It automatically detects the first CSV file in the script directory and 
    generates a corresponding DBC file with node, transmitter, Value table, 
    Comment and receiver information.

Dependencies:
    - Python 3.x
    - cantools
    - pandas

Usage:
    Place your CAN matrix CSV file in the same folder as this script.
    Run the script: : python script_can_csv_to_dbc.py 
    and it will generate an output DBC file in the same directory.

============================================
"""
import os
import glob
import pandas as pd
import cantools
from cantools.database import Database
from cantools.database.can import Message, Signal
from datetime import datetime

# ✅ Automatically find the first CSV file in the script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_files = glob.glob(os.path.join(script_dir, "*.csv"))

if not csv_files:
    print("❌ No CSV file found in the directory!")
    exit()

file_path = csv_files[0]  # Pick the first CSV file found
print(f"✅ Using CSV file: {file_path}")

# ✅ Load the CSV file
df = pd.read_csv(file_path)

# ✅ Create CAN database
db = Database()

# ✅ Extract unique nodes (Transmitters)
all_nodes = set(df["Node"].dropna().unique())

# ✅ Add nodes to the database
db.nodes.extend([cantools.database.can.Node(name=node) for node in all_nodes])

# ✅ Group messages by name
messages = {}

for _, row in df.iterrows():
    message_name = row["Message"]

    if message_name not in messages:
        messages[message_name] = {
            "id": int(row["Message ID"], 16) if isinstance(row["Message ID"], str) else int(row["Message ID"]),
            "signals": [],
            "length": 8,  # Default DLC (Data Length Code)
            "cycle_time": int(row["Cycle Time"]) if pd.notna(row["Cycle Time"]) else None,
            "send_type": row["Message Send Type"] if pd.notna(row["Message Send Type"]) else "",
            "node": row["Node"] if pd.notna(row["Node"]) else "",
        }

    # ✅ Extract scaling and offset
    scale = float(row["Factor"]) if "Factor" in row and pd.notna(
        row["Factor"]) else 1.0
    offset = float(row["Offset"]) if "Offset" in row and pd.notna(
        row["Offset"]) else 0.0

    # ✅ Extract value table (Choices) with proper formatting
    value_table = {}
    if pd.notna(row["Value Table"]):
        try:
            pairs = row["Value Table"].split(",")  # ✅ Split by comma
            for pair in pairs:
                pair = pair.strip()  # Remove extra spaces
                if " " in pair:
                    hex_val, text = pair.split(" ", 1)
                    value_table[int(hex_val, 16)] = text.strip()
        except Exception as e:
            print(
                f"⚠️ Warning: Failed to parse Value Table for {row['Signal']} -> {e}")

    # ✅ Extract the comment for the signal
    signal_comment = row["Comment"] if pd.notna(row["Comment"]) else ""

    # ✅ Create the signal object
    signal = Signal(
        name=row["Signal"],
        start=int(row["Startbit"]),
        length=int(row["Length [Bit]"]),
        minimum=float(row["Minimum"]) if "Minimum" in row and pd.notna(
            row["Minimum"]) else None,
        maximum=float(row["Maximum"]) if "Maximum" in row and pd.notna(
            row["Maximum"]) else None,
        unit=row["Unit"] if pd.notna(row["Unit"]) else "",
        is_signed=str(row["Value type"]).lower() == "signed",
        byte_order="little_endian" if str(
            row["Byte order"]).lower() == "intel" else "big_endian",
        receivers=[row["Receiver"]] if pd.notna(row["Receiver"]) else []
    )

    # ✅ Assign value table choices if available
    if value_table:
        signal.choices = value_table

    # ✅ Assign comment to signal
    if signal_comment:
        signal.comment = signal_comment

    messages[message_name]["signals"].append(signal)

# ✅ Create and add messages to the database
for message_name, data in messages.items():
    message = Message(
        frame_id=data["id"],
        name=message_name,
        length=data["length"],
        signals=data["signals"],
        cycle_time=data["cycle_time"],
        comment=f"Node: {data['node']}",
        senders=[data["node"]] if data["node"] else []
    )
    # ✅ FIX: Append messages instead of using add_message()
    db.messages.append(message)

# ✅ Save to DBC file with proper value table formatting
dbc_output_path = os.path.join(script_dir, "output.dbc")
with open(dbc_output_path, "w") as f:
    dbc_content = db.as_dbc_string()

    # ✅ Ensure that choices are displayed on separate lines
    # ✅ Makes value table multiline
    dbc_content = dbc_content.replace(";", ";\n    ")

    f.write(dbc_content)

# ✅ Print success message with time and date
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")
print(f"✅ DBC file successfully created: {dbc_output_path}")
print(f"📅 Time of execution: {now}")
