# ConZero-Jet

 **Smart Swim Jet Controller** with Bluetooth BLE remote control and STM32 motor management for Raspberry Pi.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

---

##  Features

-  **Without Touchscreen UI** - Tkinter-based 480x320 display interface
-  **BLE Remote Control** - Shelly BLU Button wireless control
-  **UART Motor Control** - STM32 motor controller via ASPEP protocol
-  **GPIO Buttons** - Physical button support (power, mode, timer, speed)
-  **Training Programs** - Pre-configured workout modes (P1-P5)
-  **Real-time Monitoring** - Speed, timer, and status display

---

##  Hardware Requirements

| Component | Specification |
|-----------|--------------|
| **Computer** | Raspberry Pi 3/4/5 |
| **Display** | 3.5" Touchscreen (480x320) |
| **Motor Controller** | STM32-based motor board (UART) |
| **Remote** | Shelly BLU Button (optional) |
| **GPIO Buttons** | 4x physical buttons (optional) |

---

##  Installation

### 1. System Dependencies (Raspberry Pi)

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Bluetooth & Serial support
sudo apt-get install -y bluetooth bluez libbluetooth-dev python3-tk python3-serial

# Add user to required groups
sudo usermod -a -G dialout $USER
sudo usermod -a -G bluetooth $USER

# Reboot
sudo reboot
```

### 3. Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

##  Usage

### Run the Application

```bash
# From project directory
python src/main.py

# Or with environment variables
CONZERO_UART_PORT=/dev/ttyS0 python src/main.py
```

### Control Options

#### Touchscreen Controls
- **Power Button** - Turn motor on/off
- **Mode Button** - Cycle through training programs (P0, T, P1-P5)
- **Timer Button** - Set workout duration (15-90 min)
- **Speed Button** - Adjust speed (20-100%)

#### BLE Remote (Shelly BLU Button)
- **Button 1 Single Press** - Pause/Resume
- **Button 1 Long Press** - Power on/off
- **Button 2** - Change mode
- **Button 3** - Set timer
- **Button 4** - Adjust speed

---

##  Configuration

### Environment Variables

Create a `.env` file (optional):

```bash
# UART Configuration
CONZERO_UART_PORT=/dev/ttyS0
UART_BAUD=115200

# BLE Configuration
ALLOWLIST_MACS=AA:BB:CC:DD:EE:FF,11:22:33:44:55:66
BLE_DEBUG=false
```

### GPIO Pin Mapping

Edit `src/config.py` to change GPIO pins:

```python
GPIO_PINS = {
    'power': 16,    # BCM pin 16
    'mode': 17,     # BCM pin 17
    'timer': 27,    # BCM pin 27
    'speed': 22,    # BCM pin 22
}
```

### Training Programs

Customize workout programs in `src/config.py`:

```python
TRAINING_PLANS = {
    "P1": [(120, 20), (180, 30), (60, 20)],  # (seconds, speed%)
    "P2": [(180, 45), (180, 55), (120, 45)],
    # Add more...
}
```

---

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run specific test
pytest tests/test_uart_manager.py -v
```

---

##  Project Structure

```
conzeroproject/
├── src/
│   ├── main.py              # Application entry point
│   ├── config.py            # Configuration settings
│   ├── conzero_jet_ui.py    # Tkinter UI
│   ├── connectivity.py      # BLE connectivity
│   ├── uart_manager.py      # STM32 motor control
│   ├── gpio_handler.py      # GPIO button handling
│   ├── mode_manager.py      # Training mode logic
│   └── error_handler.py     # Error management
├── tests/                   # Test files
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

---

## 🐛 Troubleshooting

### Bluetooth Not Working
```bash
# Check Bluetooth service
sudo systemctl status bluetooth

# Restart Bluetooth
sudo systemctl restart bluetooth

# Scan for devices
bluetoothctl scan on
```

### Serial Port Permission Denied
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER

# Or run with sudo (not recommended)
sudo python src/main.py
```

### Display Not Showing
```bash
# Check if tkinter is installed
python3 -c "import tkinter; print('OK')"

# If missing, install
sudo apt-get install python3-tk
```

---

## 📜 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 👤 Author

**Sagar Regmi** ([@sagarregmi190](https://github.com/sagarregmi190))

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📞 Support

- 🐛 [Report Issues](https://github.com/sagarregmi190/conzeroproject/issues)


---

**Built with ❤️ for swim training automation**