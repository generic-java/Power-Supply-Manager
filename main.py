"""
Created: 6/20/24
Author: Samuel Geelhood
Program: Wright Scholars
Mentor: Dr. Steven Adams
Location: Wright-Patterson Air Force Base
"""

import json
import os
from tkinter import messagebox
from tkinter.filedialog import askdirectory
from tkinter.filedialog import askopenfilename

from dotenv import load_dotenv

from graph import Graph
from power_supply_experiment import (
    PowerSupply,
    Experiment,
    kill_active_experiment,
    pause_active_experiment,
    get_active_experiment
)
from tkutils import *

load_dotenv("settings\\config.env")

window_size = (os.getenv("WINDOW_WIDTH"), os.getenv("WINDOW_HEIGHT"))
settings_dir = ".\\settings"
settings_file_name = "user_data.json"
default_settings_file_name = "default_settings.json"

with open(f"{settings_dir}\\{default_settings_file_name}", "r") as default_settings_file:
    DEFAULT_SETTINGS = json.load(default_settings_file)

DEFAULT_VERTICAL_SPACING = os.getenv("DEFAULT_VERTICAL_SPACING")


def main():
    def new_power_supply(addr: str):
        power_supply = PowerSupply(addr, auto_connect=False)

        def on_connect():
            window.after(0, lambda: connection_status.set(
                f"Connected to {power_supply.get_idn()}".strip().replace("\n", "")))
            current_limit = os.getenv("MAX_CURRENT")
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
            else:
                start_experiment_button.setState(on=True)
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
            "profile_file_path": file_path,
            "data_storage_folder_path": folder_path,
            "run_time": time_input,
            "end_at_zero": reset_voltage,
            "voltage_readout": target_voltage_readout,
            "time_readout": elapsed_time_readout,
            "progress_readout": progress_readout,
            "progress_bar": progress_bar,
            "actual_voltage_readout": actual_voltage_readout,
            "actual_current_readout": actual_current_readout,
            "power_readout": power_readout,
            "on_finish": on_experiment_end,
            "graph": graph,
            "target_power": target_power_input,
            "run_mode": control_type_toggle.get_highlighted_button(),
            "kp": kp_entry,
            "ki": ki_entry,
            "kd": kd_entry,
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
        def verify_is_number(num: str, dict, key):
            try:
                float(num)
                dict[key] = num
            except ValueError:
                pass

        if not os.path.isdir(settings_dir):
            os.mkdir(settings_dir)
        with open(f"{settings_dir}/{settings_file_name}", "w") as file:
            to_save = DEFAULT_SETTINGS.copy()
            if machine_address.get()!="":
                to_save["machine_address"] = machine_address.get()
            if os.path.isfile(file_path.get()):
                to_save["profile_file_path"] = file_path.get()
            if os.path.exists(folder_path.get()):
                to_save["data_storage_folder_path"] = folder_path.get()
            to_save["profile_type"] = profile_menu.get_selected_option()
            to_save["control_type"] = control_type_toggle.get_highlighted_button()
            verify_is_number(time_input.get(), to_save, "test_time")
            verify_is_number(kp_entry.get(), to_save, "kp")
            verify_is_number(ki_entry.get(), to_save, "ki")
            verify_is_number(kd_entry.get(), to_save, "kd")
            to_save["reset_voltage"] = reset_voltage.get()
            json.dump(to_save, file)

    def load_settings():
        try:
            with open(f"{settings_dir}\\{settings_file_name}", "r") as settings_file:
                return json.load(settings_file)
        except (json.JSONDecodeError, FileNotFoundError):
            return DEFAULT_SETTINGS

    settings = load_settings()

    window.geometry(f"{window_size[0]}x{window_size[1]}")
    window.minsize(window_size[0], window_size[1])
    window.config(background=GRAY)
    window.iconbitmap("./images/icon.ico")
    window.title("Power Supply Manager")

    experiment_config_frame = tk.Frame(
        window, width=1400, height=800, padx=20, pady=20, background=GRAY
    )

    # Region connection status
    connection_status = tk.StringVar()
    connection_status.set("Disconnected")
    # End region

    # Region machine address chooser (row 0)
    machine_addr_chooser_container, machine_address = label_entry_group(
        experiment_config_frame, settings["machine_address"], 90, "Machine address"
    )
    make_text_widget(
        "Button",
        machine_addr_chooser_container,
        "Connect",
        command=lambda: new_power_supply(machine_address.get()),
    ).grid(row=0, column=2, padx=20)
    machine_addr_chooser_container.config(pady=DEFAULT_VERTICAL_SPACING, background=GRAY)
    machine_addr_chooser_container.grid(row=0, column=0, sticky=tk.W)

    # End region

    # Region data location chooser (row 1)
    def set_storage_folder_path():
        directory = askdirectory()
        if directory!="":
            folder_path.set(directory)

    folder_chooser_container, folder_path = label_entry_group(
        experiment_config_frame, settings["data_storage_folder_path"], 78, "Data storage location"
    )
    make_text_widget(
        "Button",
        folder_chooser_container,
        "Choose folder",
        command=lambda: set_storage_folder_path(),
    ).grid(row=0, column=2, padx=20)
    folder_chooser_container.config(pady=DEFAULT_VERTICAL_SPACING, background=GRAY)
    folder_chooser_container.grid(row=1, column=0, sticky=tk.W)

    # End region

    # Region file chooser (row 2)
    def set_profile_file_path():
        directory = askopenfilename(filetypes=[("CSV Files", ".csv")])
        if directory!="":
            file_path.set(directory)

    file_chooser_container, file_path = label_entry_group(
        experiment_config_frame, settings["profile_file_path"], 84, "Profile file path"
    )
    make_text_widget(
        "Button", file_chooser_container, "Choose file", command=set_profile_file_path
    ).grid(row=0, column=2, padx=20)
    file_chooser_container.config(pady=DEFAULT_VERTICAL_SPACING, background=GRAY)
    file_chooser_container.grid(row=2, column=0, sticky=tk.W)

    # End region

    # Region profile managing widgets (row 3)
    @simple_tk_callback
    def toggle_time_input_visibility():
        if profile_menu.get_selected_option()=="Evenly spaced":
            time_input_container.grid(row=0, column=2)
        else:
            time_input_container.grid_forget()

    profile_manager_frame, profile_menu = label_menu_group(
        experiment_config_frame, "Profile type", *["Evenly spaced", "Ordered pairs"]
    )

    time_input_container, time_input = label_entry_group(
        profile_manager_frame, settings["test_time"], 4, "Test time (s)"
    )
    time_input_container.config(background=GRAY)

    profile_menu.on_option_select(toggle_time_input_visibility)
    profile_menu.select_option(settings["profile_type"])

    check_container, reset_voltage = label_switch_group(profile_manager_frame, "Set voltage to zero at experiment end")
    reset_voltage.set(bool(settings["reset_voltage"]))
    check_container.config(background=GRAY)
    check_container.grid(row=0, column=3)

    profile_manager_frame.config(background=GRAY, pady=DEFAULT_VERTICAL_SPACING)
    profile_manager_frame.grid(row=3, column=0, sticky=tk.W)
    # End region

    # Region connection status (row 4)
    tk.Label(experiment_config_frame, textvariable=connection_status, padx=20, pady=DEFAULT_VERTICAL_SPACING,
        **DEFAULT_LABEL).grid(row=4, column=0, sticky=tk.W)
    # End region

    # Region control type chooser (row 5)
    control_type_frame = tk.Frame(experiment_config_frame, padx=20, pady=20, background=GRAY)

    manual_control_frame = tk.Frame(control_type_frame)

    target_power_container, target_power_input = label_entry_group(manual_control_frame, 0, 4, "Target power (W)")
    target_power_container.config(background=GRAY)
    target_power_container.grid(row=0, column=0)

    def toggle_target_power_visibility(highlighted: int):
        active_experiment = get_active_experiment()
        if highlighted==0:
            manual_control_frame.grid_forget()
            if active_experiment is not None:
                active_experiment.set_run_mode(Experiment.AUTOMATIC)
        else:
            manual_control_frame.grid(row=0, column=1)
            if active_experiment is not None:
                active_experiment.set_run_mode(Experiment.MANUAL)

    control_type_toggle = HighlightedButtonPair(
        control_type_frame,
        "Automatic control",
        "Manual control",
        onSwitch=toggle_target_power_visibility,
    )
    control_type_toggle.select(settings["control_type"])
    control_type_toggle.frame.grid(row=0, column=0)

    pid_gains = tk.Frame(manual_control_frame)

    kp_frame, kp_entry = label_entry_group(pid_gains, settings["kp"], 4, "kP")
    kp_frame.grid(row=0, column=0)
    ki_frame, ki_entry = label_entry_group(pid_gains, settings["ki"], 4, "kI")
    ki_frame.grid(row=0, column=1)
    kd_frame, kd_entry = label_entry_group(pid_gains, settings["kd"], 4, "kD")
    kd_frame.grid(row=0, column=2)

    pid_gains.grid(row=0, column=1)

    control_type_frame.grid(row=5, column=0, sticky=tk.W)
    # End region

    # Region play, pause, and stop buttons (row 6)
    experiment_manager_frame = tk.Frame(experiment_config_frame, background=GRAY)
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
    spacer(stop_button_frame, width=20).grid(row=0, column=0)
    stop_experiment_button.grid(row=0, column=1)

    start_experiment_button.button.grid(row=0, column=0)
    control_button_frame.grid(row=0, column=0)

    progress_frame = tk.Frame(experiment_manager_frame, background=GRAY)
    progress_label = make_text_widget("Label", progress_frame, "Progress")
    progress_bar = ProgressBar(progress_frame, (300, 25), animated=True)
    progress_readout = Readout(tk.StringVar(), tk.Label(progress_frame, padx=20), "")
    progress_label.grid(row=0, column=0)
    spacer(progress_frame, width=20).grid(row=0, column=1)
    progress_bar.bar.grid(row=0, column=2)
    progress_readout.get_label().grid(row=0, column=3)
    experiment_manager_frame.grid(row=6, column=0, sticky=tk.W)
    # End region

    experiment_config_frame.place(relx=0.5, y=0, anchor=tk.N)

    # Region experiment information display
    experiment_display = tk.Frame(window, background=GRAY, pady=20)

    readout_container = tk.Frame(experiment_display, width=250, height=175, background=GRAY)

    target_voltage_readout = Readout(
        tk.StringVar(),
        tk.Label(readout_container, padx=20),
        "Target voltage: ",
    )
    target_voltage_readout.get_label().grid(row=0, column=0, sticky=tk.W)

    elapsed_time_readout = Readout(
        tk.StringVar(), tk.Label(readout_container, padx=20), "Elapsed time: "
    )
    elapsed_time_readout.get_label().grid(row=1, column=0, sticky=tk.W)

    actual_voltage_readout = Readout(
        tk.StringVar(), tk.Label(readout_container, padx=20), "Actual voltage: "
    )
    actual_voltage_readout.get_label().grid(row=2, column=0, sticky=tk.W)

    actual_current_readout = Readout(
        tk.StringVar(), tk.Label(readout_container, padx=20), "Current: "
    )
    actual_current_readout.get_label().grid(row=3, column=0, sticky=tk.W)

    power_readout = Readout(
        tk.StringVar(), tk.Label(readout_container, padx=20), "Power (W): "
    )
    power_readout.get_label().grid(row=4, column=0, sticky=tk.W)

    graph = Graph(experiment_display, 4, ["Target voltage", "Actual voltage", "Current", "Power (W)"])
    graph.get_widget().grid(row=0, column=0)
    readout_container.grid(row=0, column=1)
    readout_container.grid_propagate(False)

    experiment_display.place(relx=0.5, rely=1, anchor=tk.S)
    # End region

    window.after(500, lambda: new_power_supply(machine_address.get()))

    def exit_program():
        kill_active_experiment()
        save_settings()
        window.destroy()
        window.quit()

    window.protocol("WM_DELETE_WINDOW", exit_program)
    window.mainloop()


if __name__=="__main__":
    main()
