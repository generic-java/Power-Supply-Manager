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

from powersupplyexp import PowerSupply, Experiment, killActiveExperiment, pauseActiveExperiment, getActiveExperiment
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

    def experimentOver():
        window.after(500, stopExperimentButton.grid_forget)
        startExperimentButton.setState(on=True)

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
            "progressBar": progressBar,
            "actualVoltageReadout": actualVoltageReadout,
            "actualCurrentReadout": actualCurrentReadout,
            "powerReadout": powerReadout,
            "onFinish": experimentOver
        }
        Experiment(**expSettings).start()
        stopExperimentButton.grid(row=0, column=2)
        progressFrame.grid(row=0, column=1)

    def abortExp():
        startExperimentButton.setState(on=True)
        killActiveExperiment()
        stopExperimentButton.grid_forget()
        progressFrame.grid_forget()


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
    window.minsize(1300, 800)
    window.config(background=GRAY)
    window.iconbitmap("icon.ico")
    window.title("Power Supply Manager")

    centerFrame = tk.Frame(window, width=1300, height=800, background=GRAY)

    textConfigFrame = tk.Frame(window, width=1400, height=800, padx=20, background=GRAY)

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
    # End region

    # Region reset voltage switch
    checkContainer, resetVoltage = labelSwitchCombo(optionFrame, "Set voltage to zero at experiment end")
    resetVoltage.set(bool(settings["resetVoltage"]))
    checkContainer.config(background=GRAY)
    checkContainer.grid(row=0, column=3)
    # End region

    # Region target power input
    targetPowerContainer, targetPowerInput = entryLabelCombo(textConfigFrame, 0, 4, "Target power (W)")
    targetPowerContainer.config(background=GRAY)

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

    # Region play pause stop buttons
    experimentManagerFrame = tk.Frame(textConfigFrame, background=GRAY)

    def playPauseExp(playing: bool):
        if playing:
            pauseActiveExperiment()
        else:
            activeExperiment = getActiveExperiment()
            if activeExperiment is not None:
                if activeExperiment.isActive():
                    activeExperiment.unpause()
                else:
                    startNewExp()
            else:
                startNewExp()

    controlButtonFrame = tk.Frame(experimentManagerFrame, width=100, height=50, background=GRAY, padx=20)

    startExperimentButton = Switch(controlButtonFrame, switchType=PLAY_PAUSE, onswitch=playPauseExp)
    stopExperimentButton = makeImgButton(controlButtonFrame, "./stop.PNG", (50, 50), command=abortExp)

    startExperimentButton.button.grid(row=0, column=0)
    spacer(controlButtonFrame, 20).grid(row=0, column=1)
    controlButtonFrame.grid(row=0, column=0)

    progressFrame = tk.Frame(experimentManagerFrame, background=GRAY)
    progressLabel = makeTextWidget("Label", progressFrame, "Progress")
    progressBar = ProgressBar(progressFrame, (300, 25), animated=True)
    progressReadout = Readout(tk.StringVar(), tk.Label(progressFrame, padx=20), "")
    progressLabel.grid(row=0, column=0)
    spacer(progressFrame, 20).grid(row=0, column=1)
    progressBar.bar.grid(row=0, column=2)
    progressReadout.getLabel().grid(row=0, column=3)
    experimentManagerFrame.place(x=0, y=650, anchor=tk.W)
    # End region

    # Region progress readout
    progressReadoutContainer = tk.Frame(centerFrame, width=700, height=100, background=GRAY)

    targetVoltageReadout = Readout(tk.StringVar(), tk.Label(progressReadoutContainer, padx=20), "Target voltage: ")
    targetVoltageReadout.getLabel().grid(row=0, column=0)

    elapsedTimeReadout = Readout(tk.StringVar(), tk.Label(progressReadoutContainer, padx=20), "Elapsed time: ")
    elapsedTimeReadout.getLabel().grid(row=0, column=1)

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
    abortExpBtn = makeTextWidget("Button", centerFrame, "Abort test", command=abortExp)
    # End region

    textConfigFrame.place(x=0, y=0, anchor=tk.NW)
    centerFrame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    window.after(25, lambda: newPowerSupply(machineAddr.get()))

    window.mainloop()
    saveSettings()


if __name__=="__main__":
    main()
