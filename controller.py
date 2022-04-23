#!/usr/bin/env python3
# SPDX-License-Identifier: Unlicense
"""
Listen to the CUPS active job queue and control the printer accordingly.
If there are jobs, turn the printer on;
After a period of inactivity, turn the printer off.
The printer is turned on or off with a high pulse on the pin
specified in the settings file.

If you get daemon.runner to work, remember to use `python -O` to
avoid unnecessary attempts to print debug messages.

This code is focused on a specific printer model (HP P1006) running on
a Raspberry Pi, so tailor it to your needs.
"""

import json
import signal
import subprocess as sp
import sys
import time
import requests
from gpiozero import DigitalOutputDevice


class App:
	"""
	Main app class
	"""

	def __init__(self, settings_filename):
		try:
			settings_file = open(settings_filename)
			self.settings = json.load(settings_file)
			settings_file.close()
		except OSError as ose:
			if __debug__:
				print(ose, file=sys.stderr)
			sys.exit(ose.errno)
		except Exception as e:
			if __debug__:
				print(f'Bad settings file: {e}', file=sys.stderr)
			sys.exit(1)
		else:
			printer_settings = self.settings['printer']
			printer_interface = DigitalOutputDevice(printer_settings['gpio_pin'])
			self.printer = Printer(printer_interface, printer_settings['control_pulse_length_s'])
			self.timer = Timer(self.settings['printer_timeout_s'])


	def _update(self, num_jobs):
		""" Update tracked timer and printer states as a state machine. """

		if num_jobs == 0:
			if self.timer.state == Timer.FIRED:
				self.timer.unset()
				self.printer.off()
				if __debug__:
					print('Timeout ended, printer off')
			elif self.timer.state == Timer.UNSET and self.printer.state == Printer.ON:
				self.timer.set()
				if __debug__:
					print('Jobs done, timeout started')
		else:
			if self.timer.state == Timer.UNSET:
				if self.printer.state != Printer.ON:
					self.printer.on()
				if __debug__:
					print(f'Got {num_jobs} job(s), printer on')
			else:
				self.timer.unset()
				if __debug__:
					print(f'Got {num_jobs} job(s), timeout stopped')


	def log_error(self, error):
		""" May be used to log any error on a file specified in settings. """
		lt = time.localtime()
		with open(self.settings['io']['log_file'], 'a') as log:
			print(time.strftime('%y/%m/%d %H:%M:%S', lt), error, file=log)


	def notify_error(self, error):
		""" Notify of failure via HTTP GET. """
		if 'webhook' in self.settings:
			# The code in this block is specific to the author's setup.
			# Change it to your needs.
			webhook = self.settings['webhook']
			webhook['params']['mensagem'] = str(error)
			if __debug__:
				print('Notifying via webhook... ', end='')
			res = requests.get(webhook['url'], params=webhook['params'])
			if __debug__:
				print('response:', res.text)


	def run(self):
		""" Check for jobs and control timeout. """
		cups_queue_cmd = self.settings['cups']['queue_cmd']
		poll_interval_s = self.settings['poll_interval_s']

		while True:
			time.sleep(poll_interval_s)
			try:
				if sp.run(self.settings['cups']['status_cmd'], check=False).returncode == 0:
					# If CUPS service is running, check for active jobs in printer queue
					# Queue lists one job per line, so count them
					num_jobs = sp.check_output(cups_queue_cmd, text=True).count('\n')
			except sp.CalledProcessError as cpe:
				self.log_error(cpe)
				self.notify_error(cpe)
			except Exception as e:
				self.log_error(f'(BROAD EXCEPTION) {e}')
				self.notify_error(f'(BROAD EXCEPTION) {e}')
			else:
				self._update(num_jobs)


class Printer:
	"""
	Track and control the state of the printer.
	"""

	# Enum; possible states of the printer.
	OFF = 1
	ON = 2

	def __init__(self, interface: DigitalOutputDevice, pulse_length_s):
		self._pulse_length = pulse_length_s
		self._pin = interface
		self._pin.off()
		self.state = Printer.OFF


	def _update(self, state):
		""" Control printer to reflect it's state (on or off). """
		if self.state != state:
			# Make a single active high pulse
			self._pin.blink(on_time=self._pulse_length, off_time=0, n=1, background=False)
			self.state = state


	def off(self):
		self._update(Printer.OFF)


	def on(self):
		self._update(Printer.ON)


class Timer:
	"""
	Track and control the state of timers.
	There can only be one timer set at any time.
	"""

	# Enum; possible states of a timer.
	FIRED = 1
	SET = 2
	UNSET = 3

	def __init__(self, timeout_s):
		signal.signal(signal.SIGALRM, self._make_handler())
		self._timeout = timeout_s  # Time in seconds to wait for more jobs
		self.state = Timer.UNSET


	def _make_handler(self):
		""" Link handler to the object state in order to track timers. """
		def alarm_handler(_signum, _frame):
			self.state = Timer.FIRED
		return alarm_handler


	def set(self):
		"""
		Start timeout to wait for more jobs by keeping the printer on.
		In any event, any previously set alarm is canceled.
		"""
		signal.alarm(self._timeout)
		self.state = Timer.SET


	def unset(self):
		""" Cancel any alarm previously set. """
		if self.state == Timer.SET:
			signal.alarm(0)
		self.state = Timer.UNSET


if __name__ == '__main__':
	settings_fname = sys.argv[1] if len(sys.argv) == 2 else 'settings.json'
	app = App(settings_fname)
	app.run()
