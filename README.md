# rpi-cups-server

Raspberry Pi enabled CUPS print server that turns the printer on when a new job arrives and off after a period of inactivity.

The script will poll the CUPS active job queue and control the printer accordingly: if there are jobs, turn the printer on; After a period of inactivity, turn the printer off. As is, the printer is controlled with a high pulse on the GPIO pin specified in `settings.json`. This pulse may be used e.g. to fake a on/off button press (modding required).

The code is focused on a specific printer model (HP P1006) running on
a Raspberry Pi, so tailor it to your needs.


## Get started

First of all, figure out an easy way to interface with your printer.

Steps to start using this project:

1. Create `settings.json` from `settings_template.json` with your preferences.
1. Adapt `setup.sh` and `controller.py` to your particular printer model.
1. Run `setup.sh` to install dependencies and setup CUPS.
1. Start the printer controller with `run.sh`

Obs.: `controller.py` is only needed in order to automate the printer, but
if you want more flexibility out of it, try and get daemon.runner to work.

### Extras

1. There is code in the controller script to notify the admin of errors through a webhook previously configured. It is not necessary, but a nice addition that may be worth setting up.

1. It is very easy to set up `crontab` to start the controller at boot time. For that, run

	```sh
	crontab -e
	```

	and then insert the following lines in the opened file.

	```sh
	# Run printer controller at startup
	@reboot cd /absolute/path/to/rpi-cups-server/ && ./start.sh
	```
