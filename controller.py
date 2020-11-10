#!/usr/bin/env python3
"""
Listen to the CUPS active job queue and control the printer accordingly.
If there are jobs, turn the printer on;
After a period of inactivity, turn the printer off.
The printer is turned on or off with a high pulse on the pin
specified in `settings.json`.

If you get daemon.runner to work, remember to use `python -O` to
avoid unnecessary atempts to print debug messages.

This code is focused on a specific printer model (HP P1006) running on
a Raspberry Pi, so tailor it to your needs.
"""

import json
import time
import signal
import subprocess
import requests
# from daemon import runner
from gpiozero import DigitalOutputDevice


class App:
	"""
	Main app, needed for daemon package.
	"""

	def __init__(self):
		self.settings = json.load(open('settings.json'))
		printer_settings = self.settings['printer']
		printer_interface = DigitalOutputDevice(printer_settings['gpio_pin'])
		self.printer = Printer(printer_interface, printer_settings['control_pulse_duration_s'])
		self.timer = Timer(self.settings['timer_timeout_s'])

		# daemon.runner related settings
		# io_settings = self.settings['io']
		# self.stdin_path = io_settings['in_file']
		# self.stderr_path = io_settings['err_file']
		# self.stdout_path = io_settings['out_file']
		# self.pidfile_path = '/tmp/printer_controller.pid'
		# self.pidfile_timeout = 5


	def log_error(self, error):
		""" May be used to log any error on a file specified in settings.json. """
		with open(self.settings['io']['log_file'], 'a') as log:
			lt = time.localtime()
			print(time.strftime('%d/%m/%y %H:%M:%S', lt), error, file=log)


	def notify_error(self, error):
		""" Notify owner of failure via HTTP GET. """
		webhook = self.settings['webhook']
		webhook['params']['mensagem'] += str(error)

		print('Notifying via webhook... ', end='')
		res = requests.get(webhook['url'], params=webhook['params'])
		print('response:', res.text)


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


	def run(self):
		""" Check for jobs and control timeout. """
		job_queue_cmd = self.settings['printer']['job_queue_cmd']
		poll_interval_s = self.settings['poll_interval_s']

		while True:
			try:
				# Command returns one job per line, so count them
				num_jobs = subprocess.check_output(job_queue_cmd, text=True).count('\n')
			except Exception as e:
				self.log_error(e)
				self.notify_error(e)
				raise

			self._update(num_jobs)

			time.sleep(poll_interval_s)


class Printer:
	"""
	Track and control the state of the printer.
	"""

	# Enum; possible states of the printer.
	OFF = 1
	ON = 2

	def __init__(self, interface: DigitalOutputDevice, control_pulse_duration_s):
		self._pulse_duration = control_pulse_duration_s
		self._pin = interface
		self._pin.off()
		self.state = Printer.OFF


	def off(self):
		self._update(Printer.OFF)


	def on(self):
		self._update(Printer.ON)


	def _update(self, state):
		""" Control printer to reflect it's state (on or off). """
		if self.state != state:
			# Make a single active high pulse
			self._pin.blink(on_time=self._pulse_duration, off_time=0, n=1, background=False)
			self.state = state


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


	def _make_handler(self):
		""" Link handler to the object state in order to track timers. """
		def alarm_handler(signum, frame):
			self.state = Timer.FIRED
		return alarm_handler


if __name__ == '__main__':
	app = App()
	app.run()
	# daemon_runner = runner.DaemonRunner(app)
	# daemon_runner.do_action()
