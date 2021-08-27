#!/usr/bin/env bash
# Requires sudo
# SPDX-License-Identifier: Unlicense
#
# Remember to edit the printer information (the following variables).
#
# Whenever you make changes to the /etc/cups/cupsd.conf configuration
# file, you'll need to restart the CUPS server by typing the following
# command at a terminal prompt: `sudo systemctl restart cups.service`

# Name of the CUPS queue/class
printerQueue=HP_LaserJet_P1006

# User to append to lpadmin group in order to have admin rights on CUPS
user=pi

### DEPENDENCIES

apt update
apt install -y cups hplip printer-driver-hpcups

pip3 install -r requirements.txt

### PRINTER SETUP

hp-setup --interactive --auto -x

### CUPS CONFIG

usermod -a -G lpadmin "$user"
lpadmin -p "$printerQueue" -o printer-error-policy=retry-current-job
cupsctl --remote-admin --remote-any --share-printers --user-cancel-any
systemctl restart cups.service
