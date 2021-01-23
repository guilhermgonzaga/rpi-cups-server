#!/usr/bin/env bash
# Requires sudo
# SPDX-License-Identifier: Unlicense
#
# Remember to edit the printer information (all on the following variables).
#
# Whenever you make changes to the /etc/cups/cupsd.conf configuration
# file, you'll need to restart the CUPS server by typing the following
# command at a terminal prompt: `sudo systemctl restart cups.service`

printerName=P1006
printerDescription="HP LaserJet P1006"
printerUri="hp:/usb/HP_LaserJet_P1006?serial=AC1CN14"
#printerModel="HP LaserJet p1006, hpcups 3.18.12, requires proprietary plugin"


### DEPENDENCIES


apt update

apt install -y cups hplip printer-driver-hpcups

pip install -r requirements.txt


### PRINTER SETUP


# If there's more than one suitable printer in usb, a specifier is necessary.
# printerAddress=$(lsusb | grep -i "$printerName" | sed -e 's/^Bus \([0-9]+\) Device \([0-9]+\).*$/\1:\2/')
hp-setup --interactive --auto -x #"$printerAddress"


### CUPS SETUP


usermod -a -G lpadmin pi
cupsctl --remote-admin --remote-any --share-printers --user-cancel-any
/etc/init.d/cups restart

# Use lpadmin to create a printer
lpadmin -p "$printerName" -E -D "$printerDescription" -v "$printerUri" #-m "$printerModel"
lpadmin -o printer-error-policy=retry-job

/etc/init.d/cups restart
