"""
Created on 6/20/24
Author: Samuel Geelhood
Program: Wright Scholars
Mentor: Dr. Steve Adams
Location: Wright-Patterson Air Force Base
"""
import json
import os
from tkinter import messagebox
from tkinter.filedialog import askdirectory
from tkinter.filedialog import askopenfilename

from powersupplyexp import PowerSupply, Experiment, killActiveExperiment
from tkutils import *

DEFAULT_SETTINGS = {
    "machineAddress": "TCPIP0::169.254.197.112::inst0::INSTR",
    "fileURI": "",
    "dataStoragePath": "",
    "testTime": 10,
    "resetVoltage": True
}

currentLimit = 30

settingsDir = "./settings"
settingsFileName = "settings.json"


def main():
    def newPowerSupply(addr: str):
        powerSupply = PowerSupply(addr, autoConnect=False)

        def onPowerSupplyConnect():
            window.after(0, lambda: connectionStatus.set(f"Connected to {powerSupply.getIDN()}"))
            powerSupply.applyCurrentLimit(currentLimit)
            powerSupply.setCurrent(currentLimit)

        def onPowerSupplyDisconnect():
            window.after(0, lambda: connectionStatus.set("Disconnected"))

        onPowerSupplyDisconnect()

        powerSupply.onConnect(onPowerSupplyConnect)
        powerSupply.onDisconnect(onPowerSupplyDisconnect)
        powerSupply.tryConnect()

    def startNewExp():
        if not os.path.isfile(filePath.get()):
            if messagebox.askretrycancel("Invalid path", icon=messagebox.ERROR, message="The experiment could not be started because the provided path to the setpoint file is invalid."):
                filePath.set(askopenfilename(filetypes=[("CSV Files", ".csv")]))
                startNewExp()
            return
        try:
            float(timeInput.get())
        except ValueError:
            messagebox.showerror("Invalid run time", message="The provided value for the experiment run time is not a number.")
            return
        expSettings = {
            "filePathStringVar": filePath,
            "folderPathStringVar": folderPath,
            "runTimeStringVar": timeInput,
            "endAtZeroBoolVar": resetVoltage,
            "voltageReadout": targetVoltageReadout,
            "timeReadout": elapsedTimeReadout,
            "progressReadout": progressReadout,
            "actualVoltageReadout": actualVoltageReadout,
            "actualCurrentReadout": actualCurrentReadout,
            "powerReadout": powerReadout,
            "onFinish": abortExp
        }
        Experiment(**expSettings).start()
        abortExpBtn.place(relx=0.5, y=450, anchor=tk.CENTER)
        startExp.place_forget()

    def abortExp():
        killActiveExperiment()
        startExp.place(relx=0.5, y=450, anchor=tk.CENTER)
        abortExpBtn.place_forget()

    def saveSettings():
        if not os.path.isdir(settingsDir):
            os.mkdir(settingsDir)
        with open(f"{settingsDir}/{settingsFileName}", "w") as file:
            toSave = DEFAULT_SETTINGS.copy()
            if machineAddr.get()!="":
                toSave["machineAddress"] = machineAddr.get()
            if os.path.isfile(filePath.get()):
                toSave["fileURI"] = filePath.get()
            if os.path.exists(folderPath.get()):
                toSave["dataStoragePath"] = folderPath.get()
            try:
                float(timeInput.get())
                toSave["testTime"] = timeInput.get()
            finally:
                toSave["resetVoltage"] = resetVoltage.get()
            json.dump(toSave, file)

    def loadSettings():
        try:
            with open(f"{settingsDir}/{settingsFileName}", "r") as file:
                return json.load(file)
        except (json.JSONDecodeError, FileNotFoundError):
            return DEFAULT_SETTINGS

    settings = loadSettings()

    window.geometry("1300x800")
    window.config(background=GRAY)
    window.iconbitmap("icon.ico")
    window.title("Power Supply Manager")

    centerFrame = tk.Frame(window, width=1300, height=800, background=GRAY)

    textConfigFrame = tk.Frame(window, width=1400, height=400, padx=20, background=GRAY)

    # Region connection status
    connectionStatus = tk.StringVar()
    connectionStatus.set("Disconnected")
    # End region

    # Region machine address chooser
    machineAddrChooserContainer, machineAddr = entryLabelCombo(textConfigFrame, settings["machineAddress"], 78, "Machine address")
    makeTextWidget("Button", machineAddrChooserContainer, "Connect",
        command=lambda: newPowerSupply(machineAddr.get())).grid(row=0, column=2, padx=20)
    machineAddrChooserContainer.config(pady=20, background=GRAY)
    machineAddrChooserContainer.place(relx=0, y=50, anchor=tk.W)

    # End region

    # Region data location chooser
    def setFolderPath():
        directory = askdirectory()
        if directory!="":
            folderPath.set(directory)

    folderChooserContainer, folderPath = entryLabelCombo(textConfigFrame, settings["dataStoragePath"], 70, "Data storage location")
    makeTextWidget("Button", folderChooserContainer, "Choose folder", command=lambda: setFolderPath()).grid(row=0, column=2, padx=20)
    folderChooserContainer.config(pady=20, background=GRAY)
    folderChooserContainer.place(relx=0, y=125, anchor=tk.W)

    # End region

    # Region file chooser
    def setFilePath():
        directory = askopenfilename(filetypes=[("CSV Files", ".csv")])
        if directory!="":
            filePath.set(directory)

    fileChooserContainer, filePath = entryLabelCombo(textConfigFrame, settings["fileURI"], 77, "Profile file path")
    makeTextWidget("Button", fileChooserContainer, "Choose file", command=setFilePath).grid(row=0, column=2, padx=20)
    fileChooserContainer.config(pady=20, background=GRAY)
    fileChooserContainer.place(relx=0, y=200, anchor=tk.W)

    # End region

    # Region profile type chooser
    @simpleTKCallback
    def toggleTimeInputVisibility():
        if profileType.get()=="Evenly spaced":
            timeInputContainer.grid(row=0, column=2)
        else:
            timeInputContainer.grid_forget()

    optionFrame, profileType = menuLabelCombo(textConfigFrame, "Profile type", *["Evenly spaced", "Ordered pairs"])
    profileType.trace_add("write", toggleTimeInputVisibility)
    optionFrame.config(background=GRAY)
    optionFrame.place(relx=0, y=250)
    # End region

    # Region test time input
    timeInputContainer, timeInput = entryLabelCombo(optionFrame, settings["testTime"], 4, "Test time (s)")
    timeInputContainer.config(background=GRAY)
    timeInputContainer.grid(row=0, column=2)
    # End region

    # Region target power input
    targetPowerContainer, targetPowerInput = entryLabelCombo(textConfigFrame, 0, 4, "Target power (W)")
    targetPowerContainer.config(background=GRAY)
    targetPowerContainer.place(x=400, y=350, anchor=tk.W)

    def toggleTargetPowerVisibility(highlighted: int):
        if highlighted==0:
            targetPowerContainer.place_forget()
        else:
            targetPowerContainer.place(x=400, y=350, anchor=tk.W)

    # End region

    # Region control type chooser
    controlTypeToggle = HighlightedButtonPair(textConfigFrame, "Automatic control", "Manual control", onSwitch=toggleTargetPowerVisibility)
    controlTypeToggle.frame.place(x=20, y=350, anchor=tk.W)
    # End region

    # Region reset voltage checkbox
    checkContainer, resetVoltage = labelCheckButtonCombo(centerFrame, "Set voltage to zero at experiment end")
    resetVoltage.set(bool(settings["resetVoltage"]))
    checkContainer.config(background=GRAY)
    checkContainer.place(relx=0.5, y=365, anchor=tk.CENTER)
    # End region

    # Region progress readout
    progressReadoutContainer = tk.Frame(centerFrame, width=700, height=100, background=GRAY)

    targetVoltageReadout = Readout(tk.StringVar(), tk.Label(progressReadoutContainer, padx=20), "Target voltage: ")
    targetVoltageReadout.getLabel().grid(row=0, column=0)

    elapsedTimeReadout = Readout(tk.StringVar(), tk.Label(progressReadoutContainer, padx=20), "Elapsed time: ")
    elapsedTimeReadout.getLabel().grid(row=0, column=1)

    progressReadout = Readout(tk.StringVar(), tk.Label(progressReadoutContainer, padx=20), "Progress: ")
    progressReadout.getLabel().grid(row=0, column=2)

    progressReadoutContainer.place(relx=0.5, y=550, anchor=tk.CENTER)
    # End region

    # Region experiment readout
    expReadoutContainer = tk.Frame(centerFrame, width=700, height=100)

    actualVoltageReadout = Readout(tk.StringVar(), tk.Label(expReadoutContainer, padx=20), "Actual voltage: ")
    actualVoltageReadout.getLabel().grid(row=0, column=0)

    actualCurrentReadout = Readout(tk.StringVar(), tk.Label(expReadoutContainer, padx=20), "Current: ")
    actualCurrentReadout.getLabel().grid(row=0, column=1)

    powerReadout = Readout(tk.StringVar(), tk.Label(expReadoutContainer, padx=20), "Power (W): ")
    powerReadout.getLabel().grid(row=0, column=2)

    expReadoutContainer.place(relx=0.5, y=650, anchor=tk.CENTER)
    # End region

    # Region connection status
    tk.Label(centerFrame, textvariable=connectionStatus, **DEFAULT_LABEL).place(relx=0.5, y=750, anchor=tk.CENTER)
    # End region

    # Region start and abort experiment buttons
    startExp = makeTextWidget("Button", centerFrame, "Begin test", command=startNewExp)
    startExp.place(relx=0.5, y=450, anchor=tk.CENTER)
    abortExpBtn = makeTextWidget("Button", centerFrame, "Abort test", command=abortExp)
    # End region

    textConfigFrame.place(relx=0, rely=0, anchor=tk.NW)
    centerFrame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    window.after(25, lambda: newPowerSupply(machineAddr.get()))

    window.mainloop()
    saveSettings()


if __name__=="__main__":
    main()
