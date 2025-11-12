# ConZero-Jet 🏊

**Smart Swim Jet Controller** - Bluetooth BLE remote control with STM32 motor management for Raspberry Pi

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red.svg)

---

## ✨ Features

- 🖥️ **Touchscreen UI** - Tkinter-based 480x320 display interface
- 📱 **BLE Remote Control** - Shelly BLU Button wireless control
- ⚙️ **UART Motor Control** - STM32 motor controller via serial communication
- 🎮 **GPIO Support** - Physical button controls
- 🏋️ **Training Programs** - Pre-configured workout modes
- 📊 **Real-time Monitoring** - Speed, timer, and status display

---

## 🛠️ Hardware Requirements

| Component | Specification |
|-----------|--------------|
| **Computer** | Raspberry Pi 4 Model B (recommended) |
| **Display** | 3.5" Touchscreen (480x320) |
| **Motor Controller** | STM32-based UART motor board |
| **Remote** | Shelly BLU Button (optional) |
| **GPIO Buttons** | Physical buttons (optional) |

---

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/sagarregmi190/conZero-Jet.git
cd conZero-Jet
```

### 2. System Dependencies (Raspberry Pi)

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install required packages
sudo apt-get install -y bluetooth bluez python3-tk python3-pip python3-venv unclutter

# Add user to required groups
sudo usermod -a -G dialout $USER
sudo usermod -a -G bluetooth $USER

# Reboot to apply changes
sudo reboot
```

### 3. Python Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements-current.txt
```

### 4. Production Setup (Auto-start on boot)

```bash
# Run setup script
chmod +x setup_production.sh
./setup_production.sh

# Reboot to enable auto-start
sudo reboot
```

---

## 🚀 Usage

### Manual Run

```bash
# From project directory
python3 src/main.py

# Or with custom UART port
CONZERO_UART_PORT=/dev/ttyS0 python3 src/main.py
```

### Auto-start (Production Mode)

After running `setup_production.sh`, the application will:
- ✅ Start automatically on boot
- ✅ Run in fullscreen kiosk mode
- ✅ Hide mouse cursor
- ✅ Disable screen blanking

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# UART Configuration
CONZERO_UART_PORT=/dev/ttyS0
UART_BAUD=115200

# BLE Configuration
ALLOWLIST_MACS=AA:BB:CC:DD:EE:FF
BLE_DEBUG=false
```

### Motor Configuration

Edit `motor_config.json`:

```json
{
  "max_speed": 100,
  "min_speed": 20,
  "default_speed": 50,
  "acceleration_rate": 5
}
```

---

## 📁 Project Structure

```
conZero-Jet/
├── src/
│   ├── main.py              # Application entry point
│   ├── core/                # Core application logic
│   ├── hardware/            # Hardware interface modules
│   └── ui_handlers/         # UI event handlers
├── logs/                    # Application logs
├── icons/                   # UI icon assets
├── motor_config.json        # Motor settings
├── paired_remotes.json      # BLE device pairings
├── requirements-current.txt # Python dependencies
├── setup_production.sh      # Production setup script
├── start_conzero.sh        # Startup script
├── splash.sh               # Splash screen script
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

# Scan for BLE devices
sudo hcitool lescan
```

### Serial Port Permission Denied

```bash
# Check if user is in dialout group
groups $USER

# If not, add user and reboot
sudo usermod -a -G dialout $USER
sudo reboot
```

### Display Not Showing

```bash
# Test tkinter installation
python3 -c "import tkinter; print('Tkinter OK')"

# If missing, install
sudo apt-get install python3-tk
```

### View Application Logs

```bash
# Real-time log monitoring
tail -f logs/app.log

# Or check BLE logs
tail -f ble_app.log
```

---

## 🔧 Useful Commands

```bash
# Test startup script manually
./start_conzero.sh

# Disable auto-start
rm ~/.config/autostart/conzero-jet.desktop

# Re-enable auto-start
./setup_production.sh

# Check UART port
ls -l /dev/ttyS0
```

---

## 📜 License

MIT License - See [license](license) file for details

---

## 👤 Author

**Sagar Regmi**  
GitHub: [@sagarregmi190](https://github.com/sagarregmi190)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Open a Pull Request

---

## 📞 Support

- 🐛 [Report Issues](https://github.com/sagarregmi190/conZero-Jet/issues)
- 📧 Contact via GitHub

---

**Built with ❤️ for swim training automation**