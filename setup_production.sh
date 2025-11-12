#!/bin/bash
# ConZero-Jet Production Setup Script
# Automated setup for Raspberry Pi 4 Model B auto-start configuration

echo "========================================="
echo "ConZero-Jet Production Setup"
echo "Raspberry Pi 4 Model B"
echo "========================================="
echo ""

# 1. Create logs directory
echo "[1/10] Creating logs directory..."
mkdir -p /home/pi/conzero-jet-project/logs
chmod 755 /home/pi/conzero-jet-project/logs

# 2. Make startup script executable
echo "[2/10] Setting permissions on startup script..."
chmod +x /home/pi/conzero-jet-project/start_conzero.sh

# 3. Install unclutter (hides mouse cursor)
echo "[3/10] Installing unclutter (cursor hider)..."
sudo apt-get update -qq
sudo apt-get install -y unclutter

# 4. Create autostart directory
echo "[4/10] Creating autostart configuration..."
mkdir -p /home/pi/.config/autostart

# 5. Create desktop entry for auto-start
echo "[5/10] Creating desktop entry..."
cat > /home/pi/.config/autostart/conzero-jet.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=ConZero-Jet
Comment=Swimming Pool Control System
Exec=/home/pi/conzero-jet-project/start_conzero.sh
Terminal=false
Categories=Application;
StartupNotify=false
X-GNOME-Autostart-enabled=true
EOF

# 6. Configure LXDE autostart (disable screen blanking)
echo "[6/10] Disabling screen blanking and configuring display..."
mkdir -p /home/pi/.config/lxsession/LXDE-pi
cat > /home/pi/.config/lxsession/LXDE-pi/autostart << 'EOF'
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xscreensaver -no-splash
@xset s off
@xset -dpms
@xset s noblank
@unclutter -idle 0.1 -root
EOF

# 7. Enable auto-login (requires raspi-config)
echo "[7/10] Enabling auto-login..."
sudo raspi-config nonint do_boot_behaviour B4

# 8. Enable UART hardware (disable login shell)
echo "[8/10] Enabling UART..."
sudo raspi-config nonint do_serial 2

# 9. Set UART permissions
echo "[9/10] Setting UART permissions..."
sudo usermod -a -G dialout pi
sudo chmod 666 /dev/ttyS0

# 10. Add UART permissions to rc.local (persist after reboot)
echo "[10/10] Making UART permissions persistent..."
if ! grep -q "chmod 666 /dev/ttyS0" /etc/rc.local 2>/dev/null; then
    sudo sed -i 's/^exit 0/chmod 666 \/dev\/ttyS0\nexit 0/' /etc/rc.local
fi

echo ""
echo "========================================="
echo "✅ Setup Complete!"
echo "========================================="