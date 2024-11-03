# tink-link
===this currently does not work at all and is a work in progress===

Device to send serial commands to the RetroTINK-4K HD15 data input, using a RPi Pico W Web Server.

Dependancies:

MicroPython - https://micropython.org/

MicroDOT - https://github.com/miguelgrinberg/microdot/tags

Skeleton - http://getskeleton.com/

The Tink Link uses a Raspberry Pi Pico W to send serial communication commands to the RetroTINK-4K. This can currently used to replicate remote control commands, with the possibly of other features down the line. 
How it works:
Using a Wi-Fi-enabled smart device or computer, you connect to a locally hosted hot spot created by the Pico W. Once connected, navigating to the Tink Link web page will give you the option to enter serial terminal commands. The Pico translates submitted text commands to a GPIO data transmission pin. This pin uses "open drain" 3.3V signaling logic which, when interfaced to the HD15 data input of the RetroTINK-4K, can simulate Remote Control inputs. Reply data from the RetroTINK-4K are also received on an additional Pico GPIO pin.
