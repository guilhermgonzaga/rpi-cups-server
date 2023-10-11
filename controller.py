#!/usr/bin/env python3
# SPDX-License-Identifier: Unlicense
"""
Listen to the CUPS active job queue and control the printer accordingly.
If there are jobs, turn the printer on;
After a period of inactivity, turn the printer off.

This script may be run with `python -O` to avoid unnecessary attempts to
print debug messages. See `start.sh` for an example.

This code is focused on a specific printer model (HP P1006) running on
a Raspberry Pi, so tailor it to your needs.
The printer was modified to turn on or off via a high pulse from the Pi.

Note: the pycups documentation is quite poor, so the API was taken from
      github.com/OpenPrinting/pycups/blob/v2.0.1/cupsmodule.c#L605
      github.com/OpenPrinting/pycups/blob/v2.0.1/cupsconnection.c#L4745
"""

import json
import signal
import sys
import time

import cups
import requests
import usb.core
from gpiozero import DigitalOutputDevice as DigitalPin
from pystemd.systemd1 import Unit as SystemdUnit


def _debug_print(*args, **kwargs):
	if __debug__:
		print(*args, **kwargs)


class App:
	"""
	Main app class
	"""

	def __init__(self, settings_filename):
		try:
			settings_file = open(settings_filename)
			self.settings = json.load(settings_file)
			settings_file.close()

			printer = self.settings['printer']
			printer_intfc = DigitalPin(printer['gpio_pin'])
			self.printer = Printer(printer_intfc, printer['id'], printer['control_pulse_length_s'])
			self.timer = Timer(printer['timeout_s'])

			self.cups_svc = SystemdUnit(b'cups.service')
			self.cups_svc.load()

			self.cupsc = cups.Connection()
			if self.printer.state() == Printer.OFF:
				self.cupsc.disablePrinter(self.settings['cups_queue'])

		except json.decoder.JSONDecodeError as jde:
			_debug_print(f'Bad settings file: {jde}', file=sys.stderr)
			sys.exit(1)
		except usb.core.NoBackendError as nbe:
			_debug_print(f'PyUSB: {nbe}', file=sys.stderr)
			sys.exit(1)
		except OSError as ose:
			_debug_print(ose, file=sys.stderr)
			sys.exit(ose.errno)
		except RuntimeError as re:
			_debug_print(f'CUPS unavailable: {re}', file=sys.stderr)
			self.log(f'CUPS unavailable: {re}')
			sys.exit(1)


	def _queue_disabled(self) -> bool:
		""" Query printer queue state; 5 means destination stopped. """
		return 5 == self.cupsc.getPrinterAttributes(
			self.settings['cups_queue'],
			requested_attributes=['printer-state']
		)['printer-state']


	def _update(self, job_count, printer_state):
		""" Update tracked timer and printer states as a state machine. """

		if job_count > 0:
			self.timer.unset()
			if printer_state == Printer.OFF:
				self.printer.on()
				_debug_print(f'Got {job_count} job(s), no timeout, printer on')
			elif printer_state == Printer.READY:
				if self._queue_disabled():
					self.cupsc.enablePrinter(self.settings['cups_queue'])
				_debug_print(f'Got {job_count} job(s), no timeout, printer ready, queue enabled')
		elif self.timer.state == Timer.UNSET and printer_state != Printer.OFF:
			self.timer.set()
			_debug_print('Jobs done, timeout started')
		elif self.timer.state == Timer.FIRED:
			self.timer.unset()
			self.cupsc.disablePrinter(self.settings['cups_queue'])
			self.printer.off()
			_debug_print('No jobs, timeout reached, printer off, queue disabled')


	def log(self, message):
		""" May be used to log any message on a file specified in settings. """
		lt = time.localtime()
		with open(self.settings['log_file'], 'a') as log:
			print(time.strftime('%Y/%m/%d %H:%M:%S ', lt), message, file=log)


	def notify(self, message):
		"""
		Send a message through GET request to a webhook as a way to notify.
		The URL and parameters are specified in settings.
		This code is very specific to the author's needs. You may delete
		the 'webhook' entry in settings to disable this function easily.
		"""
		if 'webhook' in self.settings:
			webhook = self.settings['webhook']
			webhook['params']['mensagem'] = str(message)
			_debug_print('Notifying via webhook... ', end='')
			res = requests.get(webhook['url'], webhook['params'], timeout=webhook['timeout'])
			_debug_print(f'response: {res.text}')


	def run(self):
		""" Check for jobs and control timeout. """
		poll_interval_s = self.settings['poll_interval_s']

		while True:
			time.sleep(poll_interval_s)

			try:
				if self.cups_svc.Unit.ActiveState == b'active':
					""" Note:
					getJobs returns all jobs from all queues.
					If there are multiple printers on the server, use this instead:
					.getPrinterAttributes(self.settings['cups_queue'], requested_attributes=['queued-job-count'])
					"""
					job_count = len(self.cupsc.getJobs())
					printer_state = self.printer.state()
					self._update(job_count, printer_state)

			# TODO: avoid endless notification
			except cups.IPPError as ce:
				status, description = ce.args
				self.log(f'CUPS IPP Error: {status} {description}')
				self.notify(f'CUPS IPP Error: {status} {description}')
			except AttributeError as ae:
				self.log(f'Attribute Error: {ae}')
				self.notify(f'Attribute Error: {ae}')
			except RuntimeError as re:
				self.log(f'Runtime Error: {re}')
				self.notify(f'Runtime Error: {re}')


class Printer:
	"""
	Track and control the state of the printer.
	The READY state must not be set manually.
	"""

	# Enum; possible states of the printer.
	OFF = 1
	ON = 2
	READY = 3

	def __init__(self, intfc: DigitalPin, id_usb: (int, int), pulse_length_s):
		self._id = id_usb
		self._pulse_length = pulse_length_s
		self._pin = intfc

		self._state = Printer.OFF
		self._state = self.state()


	def state(self):
		""" Query printer state through pyusb. """

		if usb.core.find(idVendor=self._id[0], idProduct=self._id[1]):
			self._state = Printer.READY

		return self._state


	def off(self):
		if self._state != Printer.OFF:
			# Single pulse to turn printer off
			self._pin.blink(on_time=self._pulse_length, off_time=0, n=1, background=False)
			self._state = Printer.OFF


	def on(self):
		if self._state == Printer.OFF:
			# Single pulse to turn printer on
			self._pin.blink(on_time=self._pulse_length, off_time=0, n=1, background=False)
			self._state = Printer.ON


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
