#!/usr/bin/env python3
"""
Device Simulator for Mini Device Fleet Monitor.

Simulates a fleet of devices emitting periodic heartbeats to the monitoring API.
Demonstrates fleet activity and the 30-second timeout by allowing operators
to interactively stop any device and watch it turn OFFLINE.

Strictly zero Django dependencies — communicates purely via HTTP requests (AD-5).
"""

import argparse
import os
import sys
import threading
import time
from datetime import datetime, timezone
import requests

DEFAULT_DEVICES = [
    {"id": "device-01", "name": "Lab Sensor 01"},
    {"id": "device-02", "name": "Warehouse Gateway 02"},
    {"id": "device-03", "name": "Assembly Line Sensor 03"},
    {"id": "device-04", "name": "Thermal Monitor 04"},
    {"id": "device-05", "name": "Field Telemetry Probe 05"},
]


class DeviceSimulator:
    def __init__(self, base_url: str = "http://localhost:8000", interval: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.interval = interval
        self.devices = {d["id"]: d["name"] for d in DEFAULT_DEVICES}
        self.stop_events: dict[str, threading.Event] = {}
        self.threads: dict[str, threading.Thread] = {}
        self.global_stop = threading.Event()

    def register_device(self, device_id: str, name: str) -> bool:
        """Register device via POST /devices. 409 Conflict is treated as already registered."""
        url = f"{self.base_url}/devices"
        payload = {"id": device_id, "name": name}
        try:
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code == 201:
                print(f"[INIT] Registered new device '{device_id}' ({name})")
                return True
            elif resp.status_code == 409:
                print(f"[INIT] Device '{device_id}' already registered (proceeding)")
                return True
            else:
                print(f"[WARN] Registration for '{device_id}' returned HTTP {resp.status_code}: {resp.text}")
                return False
        except requests.RequestException as exc:
            print(f"[ERROR] Could not connect to API at {self.base_url} to register '{device_id}': {exc}")
            return False

    def device_worker(self, device_id: str, stop_event: threading.Event):
        """Worker loop sending heartbeats every interval until stop_event is set."""
        url = f"{self.base_url}/devices/{device_id}/heartbeat"
        while not stop_event.is_set() and not self.global_stop.is_set():
            now_iso = datetime.now(timezone.utc).isoformat()
            payload = {"timestamp": now_iso, "status": "OK"}
            try:
                resp = requests.post(url, json=payload, timeout=4)
                print(f"[{device_id}] Heartbeat sent -> HTTP {resp.status_code} at {now_iso}")
            except requests.RequestException as exc:
                print(f"[{device_id}] Heartbeat request error: {exc}")

            # Sleep for interval or break early if stopped
            stop_event.wait(self.interval)

        print(f"[{device_id}] Worker stopped. Heartbeats halted.")

    def start_device(self, device_id: str):
        """Start or restart a device thread."""
        if device_id not in self.devices:
            print(f"Unknown device: {device_id}. Available: {list(self.devices.keys())}")
            return

        if device_id in self.threads and self.threads[device_id].is_alive():
            print(f"Device '{device_id}' is already running.")
            return

        stop_event = threading.Event()
        self.stop_events[device_id] = stop_event
        thread = threading.Thread(
            target=self.device_worker,
            args=(device_id, stop_event),
            name=f"Worker-{device_id}",
            daemon=True,
        )
        self.threads[device_id] = thread
        thread.start()
        print(f"[{device_id}] Started heartbeat worker.")

    def stop_device(self, device_id: str):
        """Signal a specific device thread to stop."""
        if device_id in self.stop_events and not self.stop_events[device_id].is_set():
            self.stop_events[device_id].set()
            print(f"[{device_id}] Stop signal sent! Device will turn OFFLINE after 30 seconds.")
        else:
            print(f"Device '{device_id}' is not actively running.")

    def list_devices(self):
        """Print current simulation status of all devices."""
        print("\n--- Simulator Fleet Status ---")
        for dev_id, dev_name in self.devices.items():
            is_active = (
                dev_id in self.threads
                and self.threads[dev_id].is_alive()
                and not self.stop_events.get(dev_id, threading.Event()).is_set()
            )
            state = "RUNNING (sending heartbeats)" if is_active else "STOPPED (idle)"
            print(f"  {dev_id} ({dev_name}): {state}")
        print("------------------------------\n")

    def run(self, headless: bool = False):
        """Initialize all devices and run the simulator."""
        print(f"Connecting to Device Fleet Monitor API at: {self.base_url}")
        print(f"Registering {len(self.devices)} simulated devices...\n")

        # 1. Register all devices
        for dev_id, dev_name in self.devices.items():
            self.register_device(dev_id, dev_name)

        print("\nStarting heartbeat threads (every 5 seconds)...\n")
        # 2. Start worker threads
        for dev_id in self.devices:
            self.start_device(dev_id)

        # 3. Interactive loop or headless wait
        if headless or not sys.stdin.isatty():
            print("\nSimulator running in background/headless mode. Press Ctrl+C to terminate.")
            try:
                while not self.global_stop.is_set():
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        else:
            print("\n========================================================")
            print("Simulator is running! Fleet is actively sending heartbeats.")
            print("Commands:")
            print("  stop <id>     - Stop a device (e.g. 'stop device-01' or 'device-01')")
            print("  start <id>    - Resume a stopped device (e.g. 'start device-01')")
            print("  list          - List status of all simulated devices")
            print("  exit / quit   - Stop all devices and exit simulator")
            print("========================================================\n")

            try:
                while not self.global_stop.is_set():
                    try:
                        user_input = input("simulator> ").strip()
                    except EOFError:
                        break

                    if not user_input:
                        continue

                    parts = user_input.split()
                    cmd = parts[0].lower()

                    if cmd in ("exit", "quit"):
                        break
                    elif cmd == "list":
                        self.list_devices()
                    elif cmd == "stop" and len(parts) > 1:
                        self.stop_device(parts[1])
                    elif cmd == "start" and len(parts) > 1:
                        self.start_device(parts[1])
                    elif cmd.startswith("device-"):
                        # Shortcut: entering "device-01" stops it
                        self.stop_device(cmd)
                    else:
                        print("Unknown command. Use: stop <id> | start <id> | list | exit")
            except KeyboardInterrupt:
                print("\nReceived interrupt signal.")

        self.shutdown()

    def shutdown(self):
        """Gracefully stop all devices."""
        print("\nShutting down simulator fleet...")
        self.global_stop.set()
        for dev_id, event in self.stop_events.items():
            event.set()
        for thread in self.threads.values():
            thread.join(timeout=2.0)
        print("All simulator threads terminated. Goodbye.")


def main():
    parser = argparse.ArgumentParser(description="Mini Device Fleet Simulator")
    parser.add_argument(
        "--url",
        default=os.environ.get("FLEET_API_URL", "http://localhost:8000"),
        help="Base URL of the Device Fleet Monitor API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Heartbeat interval in seconds (default: 5.0)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run non-interactively without prompting for input",
    )
    args = parser.parse_args()

    simulator = DeviceSimulator(base_url=args.url, interval=args.interval)
    simulator.run(headless=args.headless)


if __name__ == "__main__":
    main()
