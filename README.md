# tink-link

Device to send serial commands to the RetroTINK-4K HD15 data input, using a RPi Pico W Web Server.

Note that while the latest version is tested working (barely), This is a work in progress and more functionality / documentation is on the way.

Dependencies:

MicroPython - https://micropython.org/

MicroDOT - https://github.com/miguelgrinberg/microdot/tags

Skeleton - http://getskeleton.com/

The Tink Link uses a Raspberry Pi Pico W to send serial communication commands to the RetroTINK-4K. This can currently used to replicate remote control commands, with the possibly of other features down the line. 
How it works:
Using a Wi-Fi-enabled smart device or computer, you connect to a locally hosted hot spot created by the Pico W. Once connected, navigating to the Tink Link web page will give you the option to enter serial terminal commands. The Pico translates submitted text commands to a UART GPIO data transmission. When interfaced to the HD15 data input of the RetroTINK-4K Tink LINK can simulate remote control command inputs.

Pinout for Pico to HD-15:

pin0 on Pico -> VGA pin 15 - Tink4K RX

pin1 on Pico -> VGA pin 12 - Tink4K TX

pin3 on Pico (Pico GND) -> VGA Outer GND + VGA Pin 5 (HSync GND)


To use:
Install MicroPython onto the RPi Pico W. Copy over the Tink Link main.py, as well as add Microdot.py and skeleton.css dependencies to the root of the Pico W. Wire connections to the HD-15 port as described in the above configuration and power on Pico W. When Pico W is powered up, log into Tink Link hotspot. Connect to 192.168.1.4 in a browser. Send commands to the Tink!

Please bug me (Old Kid) on the Tink Discord for help / testing / info / etc.
