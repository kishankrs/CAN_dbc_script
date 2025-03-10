"""
============================================
CAN - Matrix CSV to DBC Converter Script
Author: Kishan Kumar
Version: 1.0
Date: 2025-03-10
Description: 
    This script converts a CAN signal matrix from a CSV file into a DBC file.
    It automatically detects the first CSV file in the script directory and 
    generates a corresponding DBC file with node, transmitter, and receiver 
    information.

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
import datetime
import cantools
import pandas as pd
from cantools.database import Database
from cantools.database.can import Message, Signal
from cantools.database.can.node import Node

print("✅ cantools is available!")

# Auto-detect the first CSV file in the script directory
script_dir = os.path.dirname(os.path.abspath(
    __file__))  # Get script's directory
csv_files = [f for f in os.listdir(script_dir) if f.endswith(".csv")]

if not csv_files:
    raise FileNotFoundError("❌ No CSV file found in the script directory!")

file_path = os.path.join(script_dir, csv_files[0])  # Pick the first CSV file
print(f"📂 Using CSV file: {file_path}")

# Load CSV file
df = pd.read_csv(file_path)

db = Database()

# Collect all unique nodes (Transmitters + Receivers)
all_nodes = set(df["Node"].dropna().unique())  # Extract transmitters

if "Receiver" in df:
    receivers_list = df["Receiver"].dropna().unique()
    for recv in receivers_list:
        recv_nodes = [r.strip() for r in str(recv).split(",")]
        all_nodes.update(recv_nodes)

# Add nodes to cantools database
for node in all_nodes:
    db._nodes.append(Node(node))  # ✅ Manually append nodes

# Group signals by message
messages = {}
for _, row in df.iterrows():
    message_name = row["Message"]
    sender = row["Node"] if pd.notna(row["Node"]) else ""

    if message_name not in messages:
        messages[message_name] = {
            "id": int(row["Message ID"], 16) if isinstance(row["Message ID"], str) else int(row["Message ID"]),
            "signals": [],
            "length": 8,  # Default DLC, adjust if needed
            "cycle_time": int(row["Cycle Time"]) if pd.notna(row["Cycle Time"]) else None,
            "senders": [sender] if sender else [],  # Assign sender node
        }

    # Handle receivers (if the column exists)
    receivers = []
    if "Receiver" in row and pd.notna(row["Receiver"]):
        receivers = [r.strip() for r in row["Receiver"].split(",")
                     ]  # Extract receiver nodes

    # Create signal with receivers
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
        receivers=receivers  # Now each signal has its receivers!
    )

    messages[message_name]["signals"].append(signal)

# Create Message objects and add to database
for message_name, data in messages.items():
    message = Message(
        frame_id=data["id"],
        name=message_name,
        length=data["length"],
        signals=data["signals"],
        cycle_time=data["cycle_time"],
        senders=data["senders"],  # Assign transmitter(s)
        comment=f"Transmitters: {', '.join(data['senders'])}"
    )
    db.messages.append(message)  # Append message directly

# Auto-generate output DBC filename
dbc_output_path = os.path.join(script_dir, "output.dbc")

with open(dbc_output_path, "w") as f:
    f.write(db.as_dbc_string())

# Get current date, time, and day
current_time = datetime.datetime.now()
formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
day_of_week = current_time.strftime("%A")

print(f"✅ DBC file successfully created: {dbc_output_path}")
print(f"📅 Date: {formatted_time} ({day_of_week})")
