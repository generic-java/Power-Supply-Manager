import csv
import os
import threading
from datetime import datetime
from tkinter import messagebox
from tkinter.filedialog import askdirectory

import pyvisa

from tkutils import *

_active_exp = None
_active_power_supply = None


def getActiveExperiment():
    return _active_exp


def pauseActiveExperiment():
    if _active_exp is not None:
        _active_exp.pause()


def kill_active_experiment():
    if _active_exp is not None:
        _active_exp.kill()
        _active_exp.unpause()


class Timer:
    def __init__(self):
        self.start_timestamp = time.time()

    def reset(self):
        self.start_timestamp = time.time()

    def elapsedTimeSeconds(self):
        return time.time() - self.start_timestamp

    def elapsedTimeMillis(self):
        return self.elapsedTimeSeconds() / 1000


class PIDController:
    def __init__(self, k_p, k_i, k_d, integral_reset=True):
        self.k_p = k_p
        self.k_i = k_i
        self.k_d = k_d
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
                and setpoint != self.last_setpoint
                and self.integral_reset
        ):
            self.integral = 0
        self.integral += self.k_i * error * dt
        if dt == 0:
            d_term = 0
        else:
            d_term = self.k_p * dx / dt
        return self.k_p * error + self.integral + d_term


class Profile:
    EVENLY_SPACED = 0
    ORDERED_PAIRS = 1

    def __init__(
            self,
            profile_file_path: tkinter.StringVar,
            profile_type: int,
            total_test_time: tkinter.StringVar = 0,
    ):
        self.index = -1
        self.profile_file_path = profile_file_path
        self.profile_type = profile_type
        self.total_test_time = total_test_time
        self.points = []

    def _read_csv(self, path: str):
        data = []
        try:
            with open(path, newline="") as csvfile:
                reader = csv.reader(csvfile, delimiter=",", quotechar="|")
                for row in reader:
                    for i in range(len(row)):
                        row[i] = float(row[i])
                    data.append(row)
                    if len(row) == 2 and self.profile_type == Profile.EVENLY_SPACED:
                        raise AttributeError
                    elif len(row) == 1 and self.profile_type == Profile.ORDERED_PAIRS:
                        raise AttributeError
                self.points = data
                self.time_per_point = float(self.total_test_time.get()) / len(data)
        except (AttributeError, ValueError):
            pass  # TODO: add actual code here

    def get_progress(self):
        return max(self.index + 1, 0) / len(self.points)

    def __iter__(self):
        self.index = -1
        self._read_csv(self.profile_file_path.get())
        return self

    def __next__(self):
        self.index += 1
        if self.index < len(self.points):
            if self.profile_type == Profile.ORDERED_PAIRS:
                return self.points[self.index]
            else:
                return self.points[self.index][0], self.time_per_point
        else:
            raise StopIteration


class Experiment(Thread):
    def __init__(self, **kwargs):
        super().__init__()
        global _active_power_supply
        global _active_exp
        _active_exp = self
        self.power_supply = _active_power_supply
        self.run_time = 0
        self.file_path_string_var = kwargs["filePathStringVar"]
        self.folder_path = kwargs["folderPathStringVar"]
        self.run_time_string_var = kwargs["runTimeStringVar"]
        self.end_at_zero_bool_var = kwargs["endAtZeroBoolVar"]
        self.voltage_readout = kwargs["voltageReadout"]
        self.time_readout = kwargs["timeReadout"]
        self.progress_readout = kwargs["progressReadout"]
        self.progress_bar = kwargs["progressBar"]
        self.actual_voltage_readout = kwargs["actualVoltageReadout"]
        self.actual_current_readout = kwargs["actualCurrentReadout"]
        self.power_readout = kwargs["powerReadout"]
        self._on_finish = kwargs["onFinish"]
        self.graph = kwargs["graph"]
        self.start_timestamp = 0
        self.elapsed_time = 0
        self._active = False
        self.daemon = True
        self.data = []
        self.setpoints = []
        self._paused = False
        self.manualControlEnabled = False
        self.profile = Profile(
            self.file_path_string_var, Profile.EVENLY_SPACED, self.run_time_string_var
        )
        self.targetVoltage = 0
        self._experimentTimer = Timer()
        self._waitTimer = Timer()
        self.waitTime = 0
        self._lastWaitTime = 0
        self.errorTimer = Timer()
        self.lastWaitError = 0
        self.errorDerivative = 0

    def pause(self):
        self._paused = True

    def unpause(self):
        self._paused = False

    def _daemon(self):
        global _active_exp
        while self._active:
            if self is not _active_exp:
                self.kill()
                break
            if not self._paused:
                self.elapsed_time = round(time.time() - self.start_timestamp, 2)
                self.voltage_readout.update(self.targetVoltage)
                self.time_readout.update(
                    "{:.2f}".format(min(self.elapsed_time, self.run_time))
                )
                self.actual_voltage_readout.update(
                    "{:.3f}".format(self.power_supply.get_voltage())
                )
                self.actual_current_readout.update(
                    "{:.3f}".format(self.power_supply.get_current())
                )
                self.power_readout.update("{:.3f}".format(self.power_supply.get_power()))
                self.data.append(
                    [
                        self.elapsed_time,
                        self.power_supply.get_target_voltage(),
                        self.power_supply.get_voltage(),
                        self.power_supply.get_current(),
                        self.power_supply.get_power(),
                    ]
                )
            time.sleep(0.05)  # To free up CPU time

    def _save_experiment_data(self):
        now = datetime.now()
        folder_path = self.folder_path.get()
        if not os.path.exists(folder_path):
            folder_path = askdirectory(title="Data storage directory")
            self.folder_path.set(folder_path)
        try:
            with open(
                    f"{folder_path}/experiment-{now.year}-{now.month}-{now.day}_{now.hour}-{now.minute}.csv",
                    "w",
                    newline="",
            ) as file:
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

            self.file_path_string_var.after(0, func=retry)

    def _update_graph(self, t, target_voltage):
        self.graph.add_to(0, t, target_voltage)
        self.graph.add_to(1, t, self.power_supply.get_voltage())
        self.graph.add_to(2, t, self.power_supply.get_current())
        self.graph.add_to(3, t, self.power_supply.get_power())

    def run_auto(self):
        self.graph.wipe_all()
        self._experimentTimer.reset()
        self.progress_bar.reset()
        self.progress_readout.update("0.00%")
        self._waitTimer.reset()
        self.errorTimer.reset()
        for target_voltage, waitTime in self.profile:

            self._waitTimer.reset()
            while self._paused or self.manualControlEnabled:
                self._update_graph(
                    self._experimentTimer.elapsedTimeSeconds(), target_voltage
                )
                time.sleep(0.01)

            dt = self.errorTimer.elapsedTimeSeconds()

            estimated_error = self.errorDerivative * dt + self.lastWaitError

            timeToWait = max(0, waitTime + estimated_error)

            self._waitTimer.reset()
            time.sleep(timeToWait)
            waitError = waitTime - self._waitTimer.elapsedTimeSeconds()
            if dt == 0:
                self.errorDerivative = 0
            else:
                self.errorDerivative = (waitError - self.lastWaitError) / dt
            self.errorTimer.reset()
            self.lastWaitError = waitError

            if not self._active:
                break
            target_voltage = max(target_voltage, 0)
            self.targetVoltage = target_voltage
            self.power_supply.set_voltage(self.targetVoltage)
            self.progress_bar.update(self.profile.get_progress())
            self.progress_readout.update(
                "{:.2f}".format(self.profile.get_progress() * 100) + "%"
            )
            self._update_graph(
                self._experimentTimer.elapsedTimeSeconds(), target_voltage
            )

    def run_manual(self):
        pass

    def run(self):
        finished = False
        self._active = True
        self.progress_readout.recolor(BLUE)
        self.run_time = float(self.run_time_string_var.get())
        end_at_zero = self.end_at_zero_bool_var.get()
        self.start_timestamp = time.time()
        threading.Thread(target=self._daemon, daemon=True).start()
        self.run_auto()
        if end_at_zero:
            self.power_supply.set_voltage(0)
            self.voltage_readout.update(0)
        if self._active:
            self.progress_readout.recolor(FINISHED_GREEN)
            self._active = False
            time.sleep(0.1)
            self._on_finish()
            if finished:
                self.progress_readout.update("100.00%")
            self._save_experiment_data()

    def kill(self):
        self._active = False

    def is_active(self):
        return self._active


def get_active_power_supply():
    return _active_power_supply


class PowerSupply:
    def __init__(
            self,
            resource_name: str,
            auto_connect: bool = False,
            on_connect=lambda: None,
            on_disconnect=lambda: None,
    ):
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
            threading.Thread(target=self._daemon, daemon=True).start()
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

    def set_voltage(self, voltage: float):
        if self.is_connected():
            self._targetVoltage = voltage
            self._instr.write(f"VOLT {voltage}\n")

    def set_current(self, current: float):
        if self.is_connected():
            self._targetCurrent = current
            self._instr.write(f"CURR {current}\n")

    def get_voltage(self):
        return self._voltage

    def get_current(self):
        return self._current

    def get_target_voltage(self):
        return self._targetVoltage

    def get_target_current(self):
        return self._targetCurrent

    def get_power(self):
        if self.is_connected():
            return self.get_current() * self.get_voltage()
        else:
            return 0

    def write_command(self, command: str):
        if self.is_connected():
            self._instr.write(command)

    def query(self, query: str):
        if self.is_connected():
            return self._instr.query(query)

    def is_connected(self):
        return self._instr is not None
