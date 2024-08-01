import csv
import os
import threading
from datetime import datetime
from tkinter import messagebox
from tkinter.filedialog import askdirectory

import pyvisa

import tkutils
from tkutils import *

_active_exp = None
_active_power_supply = None


def get_active_experiment():
    return _active_exp


def pause_active_experiment():
    if _active_exp is not None:
        _active_exp.pause()


def kill_active_experiment():
    if _active_exp is not None:
        _active_exp.kill()
        _active_exp.unpause()


class Timer:
    def __init__(self):
        self.start_timestamp = time.time()
        self._paused = False
        self._elapsed_time_on_pause = 0
        self._pause_start = 0
        self._time_paused = 0

    def reset(self):
        self.start_timestamp = time.time()
        self._elapsed_time_on_pause = 0
        self._pause_start = 0
        self._time_paused = 0
        self._paused = False

    def elapsed_time_seconds(self):
        if self._paused:
            return self._elapsed_time_on_pause
        else:
            return time.time() - self.start_timestamp

    def elapsed_time_millis(self):
        return self.elapsed_time_seconds() / 1000

    def pause(self):
        if not self._paused:
            self._pause_start = time.time()
        self._elapsed_time_on_pause = self.elapsed_time_seconds()
        self._paused = True

    def unpause(self):
        if self._paused:
            self._time_paused += time.time() - self._pause_start
        self._paused = False
        self.start_timestamp = time.time() - self._elapsed_time_on_pause

    def get_time_paused(self):
        return self._time_paused


class PIDController:
    def __init__(self, kp, ki, kd, integral_reset=True):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0
        self.last_time = None
        self.last_measurement = None
        self.last_setpoint = None
        self.integral_reset = integral_reset

    def calculate(self, measurement, setpoint):
        current_time = time.time()
        if self.last_time is None:
            dt = 0
        else:
            dt = current_time - self.last_time
        if self.last_measurement is None:
            dx = 0
        else:
            dx = (measurement - self.last_measurement)
            # Typically, a PID controller will use the time derivative of error instead of the time derivative of position.  However, using the time derivative of position does effectively the
            # same thing, except that it prevents the output spike that occurs when the setpoint is changed
        error = setpoint - measurement
        self.last_time = current_time
        self.last_measurement = measurement
        if (
                self.last_setpoint is not None
                and setpoint!=self.last_setpoint
                and self.integral_reset
        ):
            self.integral = 0
        self.integral += self.ki * error * dt
        if dt==0:
            d_term = 0
        else:
            d_term = self.kp * dx / dt
        return self.kp * error + self.integral + d_term


class Profile:
    EVENLY_SPACED = 0
    ORDERED_PAIRS = 1

    def __init__(self, profile_file_path: tkinter.StringVar, profile_type: int, total_test_time: tkinter.StringVar = 0):
        self.index = -1
        self.profile_file_path = profile_file_path
        self.profile_type = profile_type
        self.total_test_time = total_test_time
        self._points = []
        self._time_values = []
        self._setpoint_values = []
        self._read_csv(self.profile_file_path.get())

    def _read_csv(self, path: str):
        data = []
        try:
            with open(path, newline="") as csvfile:
                reader = csv.reader(csvfile, delimiter=",", quotechar="|")
                for row in reader:
                    for i in range(len(row)):
                        row[i] = float(row[i])
                    data.append(row)
                if self.profile_type==Profile.EVENLY_SPACED:
                    time_per_point = float(self.total_test_time.get()) / len(data)
                    for i in range(len(data)):
                        self._points.append([data[i][0], time_per_point * i])
                        self._time_values.append(time_per_point * i)
                        self._setpoint_values.append(data[i][0])
                    if len(data[0])!=1:
                        raise AttributeError
                elif self.profile_type==Profile.ORDERED_PAIRS:
                    self._points = data
                    for pair in data:
                        self._time_values.append(pair[0])
                        self._setpoint_values.append(pair[1])
                    if len(data[0])!=2:
                        raise AttributeError
        except (AttributeError, ValueError):
            print("Invalid file")
            pass  # TODO: add actual code here

    def get_progress(self):
        return max(self.index + 1, 0) / len(self._points)

    def calculate_progress(self, index):
        return max(index + 1, 0) / len(self._points)

    def __iter__(self):
        self.index = -1
        return self

    def __next__(self):
        self.index += 1
        if self.index < len(self._points):
            return self._points[self.index][0], self._points[self.index][1]
        else:
            raise StopIteration

    def get_setpoints(self):
        return self._points

    def get_time_values(self):
        return self._time_values

    def get_setpoint_values(self):
        return self._setpoint_values


def sleep_until(func, sleep_time=0.001):
    while not func():
        time.sleep(sleep_time)


class Experiment(Thread):
    AUTOMATIC = 0
    MANUAL = 1

    _run_mode = AUTOMATIC

    def __init__(self, **kwargs):
        super().__init__(daemon=True)
        global _active_power_supply
        global _active_exp
        _active_exp = self
        self._power_supply = _active_power_supply
        self._active = False
        self._paused = False
        for key in kwargs:
            self.__dict__[key] = kwargs[key]
        self.data = []
        self._profile = Profile(kwargs["profile_file_path"], Profile.EVENLY_SPACED, kwargs["run_time"])
        self._time = Timer()
        self._absolute_time = Timer()
        self._progress = 0
        self.set_run_mode(kwargs["run_mode"])
        self._controller = PIDController(0, 0, 0, integral_reset=True)


    def __getitem__(self, item):
        return self.__dict__[item]

    def pause(self):
        self._paused = True
        self._time.pause()

    def unpause(self):
        self._paused = False
        self._time.unpause()

    def _update_time_display(self):
        while self._active:
            self["time_readout"].update("{:.2f}".format(self._absolute_time.elapsed_time_seconds()))
            time.sleep(0.03)

    def _update_displays(self):
        while self._active:
            t = self._absolute_time.elapsed_time_seconds()
            target_volts = self._power_supply.get_target_volts()
            actual_volts = self._power_supply.get_voltage()
            current = self._power_supply.get_current()
            power = self._power_supply.get_power()

            self["voltage_readout"].update("{:.3f}".format(target_volts))
            self["actual_voltage_readout"].update("{:.3f}".format(actual_volts))
            self["actual_current_readout"].update("{:.3f}".format(current))
            self["power_readout"].update("{:.3f}".format(power))
            self.data.append(
                [
                    t,
                    target_volts,
                    actual_volts,
                    current,
                    power,
                ]
            )

            self["graph"].add_to(1, t, actual_volts)
            self["graph"].add_to(2, t, current)
            self["graph"].add_to(3, t, power)
            self["progress_bar"].update(self._progress)
            self["progress_readout"].update("{:.2f}".format(self._progress * 100) + "%")
            time.sleep(0.1)

    def _run_experiment(self):
        self["graph"].wipe_all()
        self["progress_bar"].reset()
        self["progress_readout"].update("0.00%")
        self._time.reset()
        if self._run_mode==Experiment.MANUAL:
            self._time.pause()
        self._absolute_time.reset()
        i = 0
        setpoints = self._profile.get_setpoints()
        while self._active:
            if self._run_mode==Experiment.AUTOMATIC:
                target_voltage, scheduled_time = setpoints[i]
                sleep_until(
                    lambda: self._time.elapsed_time_seconds() > scheduled_time or self._run_mode==Experiment.MANUAL)
                if self._run_mode==Experiment.AUTOMATIC:
                    self._power_supply.set_volts(max(target_voltage, 0))
                    self._progress = self._profile.calculate_progress(i)
                    i += 1
                    self["graph"].add_to(0, scheduled_time + self._time.get_time_paused(), target_voltage)
                    if i==len(setpoints):
                        break
            else:
                try:
                    target_power = float(self["target_power"].get())
                except ValueError:
                    target_power = 0
                calculated_volts_increase = self._controller.calculate(self._power_supply.get_power(), target_power)
                self._power_supply.set_volts(self._power_supply.get_target_volts() + calculated_volts_increase)
                time.sleep(0.01)

    def _save_experiment_data(self):
        now = datetime.now()
        folder_path = self["data_storage_folder_path"].get()
        if not os.path.exists(folder_path):
            folder_path = askdirectory(title="Data storage directory")
            self["data_storage_folder_path"].set(folder_path)
        try:
            with open(f"{folder_path}/experiment-{now.year}-{now.month}-{now.day}_{now.hour}-{now.minute}.csv", "w", newline="") as file:
                writer = csv.writer(file, delimiter=",")
                writer.writerow(
                    [
                        "Elapsed Time",
                        "Target Voltage",
                        "Actual Voltage",
                        "Current",
                        "Power",
                    ]
                )
                for row in self.data:
                    writer.writerow(row)
        except (FileNotFoundError, PermissionError):

            def retry():
                if messagebox.askretrycancel(
                        "Invalid path",
                        icon=messagebox.ERROR,
                        message="The experiment data could not be saved because an invalid path was specified.",
                ):
                    self._save_experiment_data()

            tkutils.schedule(retry, 0)

    def _estimate_voltage(self):
        try:
            target_power = float(self["target_power"].get())
        except ValueError:
            target_power = 0
        current = self._power_supply.get_current()
        if current==0:
            target_volts = 0
        else:
            target_volts = target_power / current
        return target_volts

    def set_run_mode(self, run_mode: int):
        if run_mode > 1:
            raise AttributeError(f"Expected to receive a code for automatic (0) or manual (1) but got '{run_mode}'")
        else:
            self._run_mode = run_mode
            if self._run_mode==Experiment.MANUAL:
                self._time.pause()
                self._power_supply.set_volts(self._estimate_voltage())
            else:
                if not self._paused:
                    self._time.unpause()

    def run(self):
        self._active = True
        self["progress_readout"].recolor(BLUE)
        end_at_zero = self["end_at_zero"].get()
        threading.Thread(target=self._update_displays, daemon=True).start()
        threading.Thread(target=self._update_time_display, daemon=True).start()
        if self._run_mode==Experiment.MANUAL:
            self._power_supply.set_volts(self._estimate_voltage())
            time.sleep(0.5)
        self._run_experiment()
        if end_at_zero:
            self._power_supply.set_volts(0)
            self._update_displays()
        if self._active:
            time.sleep(0.05)
            self["progress_readout"].recolor(FINISHED_GREEN)
            self["on_finish"]()
            self._save_experiment_data()
            self._active = False

    def kill(self):
        self._active = False

    def is_active(self):
        return self._active


def get_active_power_supply():
    return _active_power_supply


class PowerSupply:
    def __init__(self, resource_name: str, auto_connect: bool = False, on_connect=lambda: None, on_disconnect=lambda: None):
        self._instr = None
        self._resourceName = resource_name
        self._rm = pyvisa.ResourceManager()
        self._onConnect = on_connect
        self._on_disconnect = on_disconnect
        self._last_connected = False
        self._active = False
        self._currentLimit = None
        self._idn = None
        self._targetVoltage = 0
        self._targetCurrent = 0
        self._voltage = 0
        self._current = 0
        self._resistance = 0
        if auto_connect:
            self.try_connect()

    def on_connect(self, on_connect):
        self._onConnect = on_connect

    def on_disconnect(self, on_disconnect):
        self._on_disconnect = on_disconnect

    def try_connect(self):
        if not self._active:
            global _active_power_supply
            _active_power_supply = self
            self._active = True
            threading.Thread(target=self._daemon, daemon=True, name="power supply thread").start()
        return self

    def kill(self):
        if self.is_connected():
            self._instr.write("INP:STOP\n")  # Disable DC input
        self._active = False

    def _check_for_disconnect(self):
        try:
            self._instr.session
        except pyvisa.errors.InvalidSession:
            self._instr = None
        except AttributeError:  # If the _instr field is already None
            pass

    def _connect(self):
        try:
            self._instr = self._rm.open_resource(self._resourceName)
            self._idn = self._instr.query("*IDN?")
            self._instr.write("CURR 0\n")  # Set the current to zero before enabling DC input
            self._instr.write("INP:START\n")  # Enable DC input
            self._onConnect()
        except pyvisa.errors.VisaIOError:
            pass

    def _refresh(self):
        try:
            self._voltage = float(self.query("MEASure:VOLTage?\n"))
            self._current = float(self.query("MEASure:CURRent?\n"))
            self._resistance = self._voltage / self._current
        except ValueError:
            pass

    def _daemon(self):
        global _active_power_supply
        while self._active:
            if self is not _active_power_supply:
                self.kill()
                break
            self._check_for_disconnect()
            if self.is_connected():
                self._refresh()
            else:
                self._connect()
            if self._last_connected and not self.is_connected():
                self._on_disconnect()
            self._last_connected = self.is_connected()
            time.sleep(0.1)  # Sleep to save CPU time

    def get_idn(self):
        return self._idn

    def apply_current_limit(self, limit):
        if self.is_connected():
            self._currentLimit = limit
            self._instr.write(f"SOUR: CURR {limit}\n")

    def set_volts(self, voltage: float | str):
        self._targetVoltage = voltage
        if self.is_connected():
            self._instr.write(f"VOLT {voltage}\n")

    def set_current(self, current: float | str):
        if self.is_connected():
            self._targetCurrent = current
            self._instr.write(f"CURR {current}\n")

    def get_voltage(self):
        return self._voltage

    def get_current(self):
        return self._current

    def get_resistance(self):
        return self._resistance

    def get_target_volts(self):
        return self._targetVoltage

    def get_target_current(self):
        return self._targetCurrent

    def get_power(self):
        if self.is_connected():
            return self.get_current() * self.get_voltage()
        else:
            return 0

    def get_resistance(self):
        return self._resistance

    def write_command(self, command: str):
        if self.is_connected():
            self._instr.write(command)

    def query(self, query: str):
        if self.is_connected():
            return self._instr.query(query)

    def is_connected(self):
        return self._instr is not None
