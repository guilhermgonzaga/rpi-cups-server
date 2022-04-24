<!-- SPDX-License-Identifier: Unlicense -->

# rpi-cups-server

Raspberry Pi enabled CUPS print server that turns the printer on when a new job arrives and off after a period of inactivity.

The script will poll the CUPS active job queue and control the printer accordingly: if there are jobs, turn the printer on; After a period of inactivity, turn the printer off. As is, the printer is controlled with a high pulse on the GPIO pin specified in the settings file. This pulse may be used e.g. to fake a on/off button press with an optocoupler (modding required).

The code is focused on a specific printer model (HP P1006) running on
a Raspberry Pi, so tailor it to your needs.

## Get started

First of all, figure out an easy way to interface with your printer.

Steps to start using this project:

- Create a settings file from `settings_template.json`

	The settings file is by default `settings.json` on the same directory as the controller script. Alternatively, a custom file path can be specified as an argument when running the script.

- Adapt `setup.sh` and `controller.py` to your particular printer model

- Install dependencies and setup CUPS with `setup.sh`

- Start the printer controller with `start.sh`

	By using `start.sh`, the controller script is started with option `-O` and detached from the shell with `disown`. However, the script works fine if run normally and some status information is output.

### Extras

1. There is code in the controller script to notify the admin of errors through a webhook previously configured. It is not necessary, but a nice addition that may be worth setting up.

1. It is very easy to set up a crontab to start the controller at boot time. For that, run

	```sh
	crontab -e
	```

	and add the following job to the opened file.

	```sh
	# Run printer controller at startup
	@reboot cd /absolute/path/to/rpi-cups-server/ && ./start.sh
	```
