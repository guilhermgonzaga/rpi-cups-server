#!/usr/bin/env bash
# Requires sudo
# SPDX-License-Identifier: Unlicense
#
# Whenever the configuration file /etc/cups/cupsd.conf is changed,
# the CUPS server must be restarted, for which this command may be used:
# systemctl restart cups.service
#
# Remember to update the following information (variables).

# Name of the CUPS queue/class
printerQueue=HP_LaserJet_P1006
# User to append to lpadmin group in order to have admin rights on CUPS
user=pi

# Exit immediately if a command exits with a non-zero status
# set -o errexit
# Treat unset variables as errors when substituting
set -o nounset

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
