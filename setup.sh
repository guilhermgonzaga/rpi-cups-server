#!/usr/bin/env bash
# Requires sudo
# SPDX-License-Identifier: Unlicense
#
# Remember to edit the printer information (all on the following variables).
#
# Whenever you make changes to the /etc/cups/cupsd.conf configuration
# file, you'll need to restart the CUPS server by typing the following
# command at a terminal prompt: `sudo systemctl restart cups.service`

### DEPENDENCIES

apt update
apt install -y cups hplip printer-driver-hpcups

pip3 install -r requirements.txt

### PRINTER SETUP

hp-setup --interactive --auto -x

### CUPS CONFIG

usermod -a -G lpadmin pi
cupsctl --remote-admin --remote-any --share-printers --user-cancel-any
/etc/init.d/cups restart
