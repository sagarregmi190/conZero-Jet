#!/bin/bash
# Show splash screen
export DISPLAY=:0
feh --fullscreen --auto-zoom --hide-pointer /home/pi/conzero-jet-project/splash.png &
sleep 5
pkill feh
