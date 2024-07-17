import csv
import os
import threading
import tkinter
from datetime import datetime
from tkinter import messagebox
from tkinter.filedialog import askdirectory

import pyvisa

from tkutils import *

_activeExp = None
_activePowerSupply = None


def getActiveExperiment():
    return _activeExp


def pauseActiveExperiment():
    if _activeExp is not None:
        _activeExp.pause()


def killActiveExperiment():
    if _activeExp is not None:
        _activeExp.kill()


class Timer:
    def __init__(self):
        self.startTimestamp = time.time()

    def reset(self):
        self.startTimestamp = time.time()

    def elapsedTimeSeconds(self):
        return time.time() - self.startTimestamp

    def elapsedTimeMillis(self):
        return self.elapsedTimeSeconds() / 1000


class PIDController:
    def __init__(self, kP, kI, kD, integralReset=True):
        self.kP = kP
        self.kI = kI
        self.kD = kD
        self.integral = 0
        self.lastTime = None
        self.lastMeasurement = None
        self.lastSetpoint = None
        self.integralReset = integralReset

    def calculate(self, measurement, setpoint):
        currentTime = time.time()
        if self.lastTime is None:
            dt = 0
        else:
            dt = currentTime - self.lastTime
        if self.lastMeasurement is None:
            dx = 0
        else:
            dx = measurement - self.lastMeasurement  # Typically, a PID controller will use the time derivative of error instead of the time derivative of position.  However, using the time derivative of position does effectively the same thing, except that it prevents the output spike that occurs when the setpoint is changed
        error = setpoint - measurement
        self.lastTime = currentTime
        self.lastMeasurement = measurement
        if self.lastSetpoint is not None and setpoint!=self.lastSetpoint and self.integralReset:
            self.integral = 0
        self.integral += self.kI * error * dt
        if dt==0:
            dTerm = 0
        else:
            dTerm = self.kP * dx / dt
        return self.kP * error + self.integral + dTerm


class Profile:
    EVENLY_SPACED = 0
    ORDERED_PAIRS = 1

    def __init__(self, profileFilePath: tkinter.StringVar, profileType: int, totalTestTime: tkinter.StringVar = 0):
        self.index = -1
        self.profileFilePath = profileFilePath
        self.profileType = profileType
        self.totalTestTime = totalTestTime
        self.points = []

    def _readCSV(self, path: str):
        data = []
        try:
            with open(path, newline="") as csvfile:
                reader = csv.reader(csvfile, delimiter=",", quotechar="|")
                for row in reader:
                    for i in range(len(row)):
                        row[i] = float(row[i])
                    data.append(row)
                    if len(row)==2 and self.profileType==Profile.EVENLY_SPACED:
                        raise AttributeError
                    elif len(row)==1 and self.profileType==Profile.ORDERED_PAIRS:
                        raise AttributeError
                self.points = data
                self.timePerPoint = float(self.totalTestTime.get()) / len(data)
        except (AttributeError, ValueError):
            pass  # TODO: add actual code here

    def getProgress(self):
        return max(self.index + 1, 0) / len(self.points)

    def __iter__(self):
        self.index = -1
        self._readCSV(self.profileFilePath.get())
        return self

    def __next__(self):
        self.index += 1
        if self.index < len(self.points):
            if self.profileType==Profile.ORDERED_PAIRS:
                return self.points[self.index]
            else:
                return self.points[self.index][0], self.timePerPoint
        else:
            raise StopIteration


class Experiment(Thread):
    def __init__(self, **kwargs):
        super().__init__()
        global _activePowerSupply
        global _activeExp
        _activeExp = self
        self.powerSupply = _activePowerSupply
        self.runTime = 0
        self.filePathStringVar = kwargs["filePathStringVar"]
        self.folderPath = kwargs["folderPathStringVar"]
        self.runTimeStringVar = kwargs["runTimeStringVar"]
        self.endAtZeroBoolVar = kwargs["endAtZeroBoolVar"]
        self.voltageReadout = kwargs["voltageReadout"]
        self.timeReadout = kwargs["timeReadout"]
        self.progressReadout = kwargs["progressReadout"]
        self.progressBar = kwargs["progressBar"]
        self.actualVoltageReadout = kwargs["actualVoltageReadout"]
        self.actualCurrentReadout = kwargs["actualCurrentReadout"]
        self.powerReadout = kwargs["powerReadout"]
        self._onFinish = kwargs["onFinish"]
        self.startTimestamp = 0
        self.elapsedTime = 0
        self._active = False
        self.daemon = True
        self.data = []
        self.setpoints = []
        self._paused = False
        self.manualControlEnabled = False
        self.profile = Profile(self.filePathStringVar, Profile.EVENLY_SPACED, self.runTimeStringVar)
        self.targetVoltage = 0

    def pause(self):
        self._paused = True

    def unpause(self):
        self._paused = False

    def _daemon(self):
        global _activeExp
        while self._active:
            if self is not _activeExp:
                self.kill()
                break
            if not self._paused:
                self.elapsedTime = round(time.time() - self.startTimestamp, 2)
                self.voltageReadout.update(self.targetVoltage)
                self.timeReadout.update("{:.2f}".format(min(self.elapsedTime, self.runTime)))
                self.actualVoltageReadout.update("{:.3f}".format(self.powerSupply.getVoltage()))
                self.actualCurrentReadout.update("{:.3f}".format(self.powerSupply.getCurrent()))
                self.powerReadout.update("{:.3f}".format(self.powerSupply.getPower()))
                self.data.append([self.elapsedTime, self.powerSupply.getTargetVoltage(), self.powerSupply.getVoltage(), self.powerSupply.getCurrent(), self.powerSupply.getPower()])
            time.sleep(0.05)  # To free up CPU time

    def _saveExperimentData(self):
        now = datetime.now()
        folderPath = self.folderPath.get()
        if not os.path.exists(folderPath):
            folderPath = askdirectory(title="Data storage directory")
            self.folderPath.set(folderPath)
        try:
            with open(f"{folderPath}/experiment-{now.year}-{now.month}-{now.day}_{now.hour}-{now.minute}.csv", "w",
                    newline="") as file:
                writer = csv.writer(file, delimiter=",")
                writer.writerow(["Elapsed Time", "Target Voltage", "Actual Voltage", "Current", "Power"])
                for row in self.data:
                    writer.writerow(row)
        except (FileNotFoundError, PermissionError):
            def retry():
                if messagebox.askretrycancel("Invalid path", icon=messagebox.ERROR,
                        message="The experiment data could not be saved because an invalid path was specified."):
                    self._saveExperimentData()

            self.filePathStringVar.after(0, func=retry)

    def runAuto(self):
        self.progressBar.reset()
        self.progressReadout.update("0.00%")
        for targetVoltage, waitTime in self.profile:
            while self._paused or self.manualControlEnabled:
                time.sleep(0.01)
            time.sleep(waitTime)
            if not self._active:
                break
            self.targetVoltage = max(targetVoltage, 0.0)
            self.powerSupply.setVoltage(self.targetVoltage)
            self.progressBar.update(self.profile.getProgress())
            self.progressReadout.update("{:.2f}".format(self.profile.getProgress() * 100) + "%")

    def runManual(self):
        pass

    def run(self):
        finished = False
        self._active = True
        self.progressReadout.recolor(BLUE)
        self.runTime = float(self.runTimeStringVar.get())
        endAtZero = self.endAtZeroBoolVar.get()
        self.startTimestamp = time.time()
        threading.Thread(target=self._daemon, daemon=True).start()
        self.runAuto()
        if endAtZero:
            self.powerSupply.setVoltage(0)
            self.voltageReadout.update(0)
        if self._active:
            self.progressReadout.recolor(FINISHED_GREEN)
            self._active = False
            time.sleep(0.1)
            self._onFinish()
            if finished:
                self.progressReadout.update("100.00%")
            self._saveExperimentData()

    def kill(self):
        self._active = False

    def isActive(self):
        return self._active


def getActivePowerSupply():
    return _activePowerSupply


class PowerSupply:
    def __init__(self, resourceName: str, autoConnect: bool = False, onConnect=lambda: None, onDisconnect=lambda: None):
        self._instr = None
        self._resourceName = resourceName
        self._rm = pyvisa.ResourceManager()
        self._onConnect = onConnect
        self._onDisconnect = onDisconnect
        self._lastConnected = False
        self._active = False
        self._currentLimit = None
        self._IDN = None
        self._targetVoltage = 0
        self._targetCurrent = 0
        self._voltage = 0
        self._current = 0
        if autoConnect:
            self.tryConnect()

    def onConnect(self, onConnect):
        self._onConnect = onConnect

    def onDisconnect(self, onDisconnect):
        self._onDisconnect = onDisconnect

    def tryConnect(self):
        if not self._active:
            global _activePowerSupply
            _activePowerSupply = self
            self._active = True
            threading.Thread(target=self._daemon, daemon=True).start()
        return self

    def kill(self):
        if self.isConnected():
            self._instr.write("INP:STOP\n")  # Disable DC input
        self._active = False

    def _checkForDisconnect(self):
        try:
            self._instr.session
        except pyvisa.errors.InvalidSession:
            self._instr = None
        except AttributeError:  # If the _instr field is already None
            pass

    def _connect(self):
        try:
            self._instr = self._rm.open_resource(self._resourceName)
            self._IDN = self._instr.query("*IDN?")
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
        global _activePowerSupply
        while self._active:
            if not self is _activePowerSupply:
                self.kill()
                break
            self._checkForDisconnect()
            if self.isConnected():
                self._refresh()
            else:
                self._connect()
            if self._lastConnected and not self.isConnected():
                self._onDisconnect()
            self._lastConnected = self.isConnected()
            time.sleep(0.1)  # Sleep to save CPU time

    def getIDN(self):
        return self._IDN

    def applyCurrentLimit(self, limit):
        if self.isConnected():
            self._currentLimit = limit
            self._instr.write(f"SOUR: CURR {limit}\n")

    def setVoltage(self, voltage: float):
        if self.isConnected():
            self._targetVoltage = voltage
            self._instr.write(f"VOLT {voltage}\n")

    def setCurrent(self, current: float):
        if self.isConnected():
            self._targetCurrent = current
            self._instr.write(f"CURR {current}\n")

    def getVoltage(self):
        return self._voltage

    def getCurrent(self):
        return self._current

    def getTargetVoltage(self):
        return self._targetVoltage

    def getTargetCurrent(self):
        return self._targetCurrent

    def getPower(self):
        if self.isConnected():
            return self.getCurrent() * self.getVoltage()
        else:
            return 0

    def writeCommand(self, command: str):
        if self.isConnected():
            self._instr.write(command)

    def query(self, query: str):
        if self.isConnected():
            return self._instr.query(query)

    def isConnected(self):
        return self._instr is not None
