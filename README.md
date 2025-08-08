# Elegoo Centauri Carbon monitoring script

This is a simple Python script to monitor the status of one or more 3D printers on your local WiFi network. Printers need to support SDCP, which includes the Elegoo Centauri Carbon.

<img width="549" height="406" alt="ccmonitor" src="https://github.com/user-attachments/assets/109a250d-b233-41b1-aff6-3e96045f425b" />

The script discovers any printers on the network, and then prints changes in status to the console. eg, PRINTING, COMPLETE, IDLE, etc.

Alert sounds are made if a print job is: paused (eg, so you can add metal parts), stopped due to an error, or completed. It also makes a sound once the print bed has cooled down to 40C.
You could edit the script to change the alert rules, play different sounds, trigger desktop notifications, etc.

It should work on both Windows and Linux.

If you are new to running Python scripts, there are lots of great tutorials out there to get you started, such as https://realpython.com/run-python-scripts/

Requirements are python3 and the _websockets_ package, which may need to be installed. eg, for Linux users

`sudo pip install websockets`

or:

`sudo apt install python3-websockets`
