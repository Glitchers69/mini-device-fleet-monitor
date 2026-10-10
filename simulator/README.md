# Device Simulator

Standalone HTTP simulator that generates periodic heartbeats for a fleet of 5 devices and allows interactively halting individual devices to observe them transitioning from ONLINE to OFFLINE after the 30-second timeout.

## Prerequisites

- Python 3.11+
- `requests` package (`pip install -r requirements.txt`)
- The fleet monitor server must be running (`python manage.py runserver`)

## Usage

```bash
# Run simulator against default http://localhost:8000
python simulator/run.py

# Or specify custom API URL or interval
python simulator/run.py --url http://localhost:8000 --interval 5.0

# Or run non-interactively in the background
python simulator/run.py --headless
```

## Interactive Commands

While the simulator is running, you can enter commands in the terminal:

- `stop <device_id>` or `<device_id>`: Halts heartbeats for that device (e.g. `stop device-01` or `device-01`).
- `start <device_id>`: Resumes heartbeats for a previously stopped device.
- `list`: Displays the current status of all simulator worker threads.
- `exit` or `quit`: Gracefully shuts down all device threads and exits.

## Testing Timeout Behavior

1. Start the simulator: `python simulator/run.py`
2. Open the operator dashboard at `http://localhost:8000/dashboard/` or call `GET /devices`. All 5 devices will show **ONLINE**.
3. In the simulator terminal, type `stop device-01`.
4. Within 30 seconds of stopping, `device-01` will transition to **OFFLINE** on the dashboard and in API responses, while the remaining 4 devices stay **ONLINE**.
