pi@raspberrypi:~/conzero-jet-project $ cat /home/pi/conzero-jet-project/start_conzero.sh
#!/bin/bash
# ConZero-Jet Auto-Start Script

# Wait for desktop to be ready
sleep 0.5

# Set display environment
export DISPLAY=:0
export XAUTHORITY=/home/pi/.Xauthority
export CONZERO_UART_PORT=/dev/ttyS0

# Navigate to project
cd /home/pi/conzero-jet-project

#create a splash screen for conZero-Jet with Logo within : 


# Create logs directory
mkdir -p logs

/home/pi/conzero-jet-project/splash.sh &

# Start the application
/usr/bin/python3 /home/pi/conzero-jet-project/src/main.py >> /home/pi/conzero-jet-project/logs/app.log 2>&1