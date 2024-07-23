"""
Created: 6/20/24
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

from graph import Graph
from power_supply_experiment import (
    PowerSupply,
    Experiment,
    kill_active_experiment,
    pause_active_experiment,
    get_active_experiment,
)
from tkutils import *

window_size = (1700, 900)

DEFAULT_SETTINGS = {
    "machineAddress": "TCPIP0::169.254.197.112::inst0::INSTR",
    "fileURI": "",
    "dataStoragePath": "",
    "profileType": "Evenly spaced",
    "controlType": 0,
    "testTime": 10,
    "resetVoltage": True,
}

DEFAULT_SPACING = 12

settings_dir = "./settings"
settings_file_name = "settings.json"

current_limit = 30


def main():
    def exit_program():
        # del graph
        # del progress_bar
        save_settings()

    def new_power_supply(addr: str):
        power_supply = PowerSupply(addr, auto_connect=False)

        def on_connect():
            window.after(
                0,
                lambda: connection_status.set(f"Connected to {power_supply.get_idn()}"),
            )
            power_supply.apply_current_limit(current_limit)
            power_supply.set_current(current_limit)

        def on_disconnect():
            window.after(0, lambda: connection_status.set("Disconnected"))

        on_disconnect()
        power_supply.on_connect(on_connect)
        power_supply.on_disconnect(on_disconnect)
        power_supply.try_connect()

    def start_new_experiment():
        if not os.path.isfile(file_path.get()):
            if messagebox.askretrycancel(
                    "Invalid path",
                    icon=messagebox.ERROR,
                    message="The experiment could not be started because the provided path to the setpoint file is invalid.",
            ):
                file_path.set(askopenfilename(filetypes=[("CSV Files", ".csv")]))
                start_new_experiment()
            return
        try:
            float(time_input.get())
        except ValueError:
            messagebox.showerror(
                "Invalid run time",
                message="The provided value for the experiment run time is not a number.",
            )
            return
        experiment_settings = {
            "filePathStringVar": file_path,
            "folderPathStringVar": folder_path,
            "runTimeStringVar": time_input,
            "endAtZeroBoolVar": reset_voltage,
            "voltageReadout": target_voltage_readout,
            "timeReadout": elapsed_time_readout,
            "progressReadout": progress_readout,
            "progressBar": progress_bar,
            "actualVoltageReadout": actual_voltage_readout,
            "actualCurrentReadout": actual_current_readout,
            "powerReadout": power_readout,
            "onFinish": on_experiment_end,
            "graph": graph,
        }
        Experiment(**experiment_settings).start()
        window.after(50, lambda: stop_button_frame.grid(row=0, column=1))
        progress_frame.grid(row=0, column=1)

    def manage_active_experiment(playing: bool):
        if playing:
            pause_active_experiment()
        else:
            active_experiment = get_active_experiment()
            if active_experiment is not None:
                if active_experiment.is_active():
                    active_experiment.unpause()
                else:
                    start_new_experiment()
            else:
                start_new_experiment()

    def stop_experiment():
        start_experiment_button.setState(on=True)
        kill_active_experiment()
        stop_button_frame.grid_forget()
        progress_frame.grid_forget()

    def on_experiment_end():
        start_experiment_button.setState(on=True)
        stop_button_frame.grid_forget()

    def save_settings():
        if not os.path.isdir(settings_dir):
            os.mkdir(settings_dir)
        with open(f"{settings_dir}/{settings_file_name}", "w") as file:
            to_save = DEFAULT_SETTINGS.copy()
            if machine_address.get() != "":
                to_save["machineAddress"] = machine_address.get()
            if os.path.isfile(file_path.get()):
                to_save["fileURI"] = file_path.get()
            if os.path.exists(folder_path.get()):
                to_save["dataStoragePath"] = folder_path.get()
            to_save["profileType"] = profile_menu.get_selected_option()
            to_save["controlType"] = control_type_toggle.get_highlighted_button()
            try:
                float(time_input.get())
                to_save["testTime"] = time_input.get()
            finally:
                to_save["resetVoltage"] = reset_voltage.get()
            json.dump(to_save, file)

    def load_settings():
        try:
            with open(f"{settings_dir}/{settings_file_name}", "r") as file:
                return json.load(file)
        except (json.JSONDecodeError, FileNotFoundError):
            return DEFAULT_SETTINGS

    settings = load_settings()

    window.geometry(f"{window_size[0]}x{window_size[1]}")
    window.minsize(window_size[0], window_size[1])
    window.config(background=GRAY)
    window.iconbitmap("./images/icon.ico")
    window.title("Power Supply Manager")

    center_frame = tk.Frame(window, width=1300, height=800, background=GRAY)

    text_config_frame = tk.Frame(
        window, width=1400, height=800, padx=20, background=GRAY
    )

    # Region connection status
    connection_status = tk.StringVar()
    connection_status.set("Disconnected")
    # End region

    # Region machine address chooser (row 0)
    machine_addr_chooser_container, machine_address = label_entry_group(
        text_config_frame, settings["machineAddress"], 78, "Machine address"
    )
    make_text_widget(
        "Button",
        machine_addr_chooser_container,
        "Connect",
        command=lambda: new_power_supply(machine_address.get()),
    ).grid(row=0, column=2, padx=20)
    machine_addr_chooser_container.config(pady=DEFAULT_SPACING, background=GRAY)
    machine_addr_chooser_container.grid(row=0, column=0)

    # End region

    # Region data location chooser (row 1)
    def set_folder_path():
        directory = askdirectory()
        if directory != "":
            folder_path.set(directory)

    folder_chooser_container, folder_path = label_entry_group(
        text_config_frame, settings["dataStoragePath"], 70, "Data storage location"
    )
    make_text_widget(
        "Button",
        folder_chooser_container,
        "Choose folder",
        command=lambda: set_folder_path(),
    ).grid(row=0, column=2, padx=20)
    folder_chooser_container.config(pady=DEFAULT_SPACING, background=GRAY)
    folder_chooser_container.grid(row=1, column=0)

    # End region

    # Region file chooser (row 2)
    def set_file_path():
        directory = askopenfilename(filetypes=[("CSV Files", ".csv")])
        if directory != "":
            file_path.set(directory)

    file_chooser_container, file_path = label_entry_group(
        text_config_frame, settings["fileURI"], 77, "Profile file path"
    )
    make_text_widget(
        "Button", file_chooser_container, "Choose file", command=set_file_path
    ).grid(row=0, column=2, padx=20)
    file_chooser_container.config(pady=DEFAULT_SPACING, background=GRAY)
    file_chooser_container.grid(row=2, column=0)

    # End region

    # Region profile managing widgets (row 3)
    @simple_tk_callback
    def toggle_time_input_visibility():
        if profile_menu.get_selected_option() == "Evenly spaced":
            time_input_container.grid(row=0, column=2)
        else:
            time_input_container.grid_forget()

    profile_manager_frame, profile_menu = label_menu_group(
        text_config_frame, "Profile type", *["Evenly spaced", "Ordered pairs"]
    )

    time_input_container, time_input = label_entry_group(
        profile_manager_frame, settings["testTime"], 4, "Test time (s)"
    )
    time_input_container.config(background=GRAY)

    profile_menu.on_option_select(toggle_time_input_visibility)
    profile_menu.select_option(settings["profileType"])
    profile_manager_frame.config(background=GRAY, pady=DEFAULT_SPACING)
    profile_manager_frame.grid(row=3, column=0, sticky=tk.W)
    # End region

    # Region reset voltage switch
    check_container, reset_voltage = label_switch_group(profile_manager_frame, "Set voltage to zero at experiment end")
    reset_voltage.set(bool(settings["resetVoltage"]))
    check_container.config(background=GRAY)
    check_container.grid(row=0, column=3)
    # End region

    # Region play, pause, and stop buttons
    experiment_manager_frame = tk.Frame(text_config_frame, background=GRAY)

    control_button_frame = tk.Frame(
        experiment_manager_frame, height=50, background=GRAY, padx=20
    )
    stop_button_frame = tk.Frame(control_button_frame, background=GRAY)

    start_experiment_button = Switch(
        control_button_frame, switch_type=PLAY_PAUSE, onswitch=manage_active_experiment
    )
    stop_experiment_button = make_img_button(
        stop_button_frame, "images/stop.PNG", (50, 50), command=stop_experiment
    )
    spacer(stop_button_frame, 20).grid(row=0, column=0)
    stop_experiment_button.grid(row=0, column=1)

    start_experiment_button.button.grid(row=0, column=0)
    control_button_frame.grid(row=0, column=0)

    progress_frame = tk.Frame(experiment_manager_frame, background=GRAY)
    progress_label = make_text_widget("Label", progress_frame, "Progress")
    progress_bar = ProgressBar(progress_frame, (300, 25), animated=True)
    progress_readout = Readout(tk.StringVar(), tk.Label(progress_frame, padx=20), "")
    progress_label.grid(row=0, column=0)
    spacer(progress_frame, 20).grid(row=0, column=1)
    progress_bar.bar.grid(row=0, column=2)
    progress_readout.get_label().grid(row=0, column=3)

    # End region
    # Region target power input
    control_type_frame = tk.Frame(text_config_frame, padx=20, pady=20, background=GRAY)

    target_power_container, target_power_input = label_entry_group(control_type_frame, 0, 4, "Target power (W)")
    target_power_container.config(background=GRAY)

    def toggle_target_power_visibility(highlighted: int):
        if highlighted == 0:
            target_power_container.grid_forget()
            experiment_manager_frame.grid(row=5, column=0, sticky=tk.W)
        else:
            target_power_container.grid(row=0, column=1)
            experiment_manager_frame.grid_forget()
            start_experiment_button.setState(on=True)

    # End region

    # Region control type chooser (row 4)

    control_type_toggle = HighlightedButtonPair(
        control_type_frame,
        "Automatic control",
        "Manual control",
        onSwitch=toggle_target_power_visibility,
    )
    control_type_toggle.select(settings["controlType"])
    control_type_toggle.frame.grid(row=0, column=0)
    control_type_frame.grid(row=4, column=0, sticky=tk.W)
    # End region

    # Region progress readout
    progress_readout_container = tk.Frame(
        center_frame, width=700, height=100, background=GRAY
    )

    target_voltage_readout = Readout(
        tk.StringVar(),
        tk.Label(progress_readout_container, padx=20),
        "Target voltage: ",
    )
    target_voltage_readout.get_label().grid(row=0, column=0)

    elapsed_time_readout = Readout(
        tk.StringVar(), tk.Label(progress_readout_container, padx=20), "Elapsed time: "
    )
    elapsed_time_readout.get_label().grid(row=0, column=1)

    progress_readout_container.place(relx=0.5, y=550, anchor=tk.CENTER)
    # End region

    # Region experiment readout
    exp_readout_container = tk.Frame(center_frame, width=700, height=100)

    actual_voltage_readout = Readout(
        tk.StringVar(), tk.Label(exp_readout_container, padx=20), "Actual voltage: "
    )
    actual_voltage_readout.get_label().grid(row=0, column=0)

    actual_current_readout = Readout(
        tk.StringVar(), tk.Label(exp_readout_container, padx=20), "Current: "
    )
    actual_current_readout.get_label().grid(row=0, column=1)

    power_readout = Readout(
        tk.StringVar(), tk.Label(exp_readout_container, padx=20), "Power (W): "
    )
    power_readout.get_label().grid(row=0, column=2)

    exp_readout_container.place(relx=0.5, y=650, anchor=tk.CENTER)
    # End region

    # Region connection status
    tk.Label(center_frame, textvariable=connection_status, **DEFAULT_LABEL).place(
        relx=0.5, y=750, anchor=tk.CENTER
    )
    # End region

    text_config_frame.place(x=0, y=0, anchor=tk.NW)
    center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    # Region matplotlib graph

    # End region
    graph = Graph(window, 4, ["Target voltage", "Actual voltage", "Current", "Power"])
    graph.get_widget().place(relx=0.5, rely=1, anchor=tk.S)
    window.after(100, lambda: new_power_supply(machine_address.get()))

    window.wm_protocol("WM_DELETE_WINDOW", exit_program)
    window.mainloop()


if __name__ == "__main__":
    main()
