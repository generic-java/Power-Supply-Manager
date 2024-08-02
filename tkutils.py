import sys
import time
import tkinter
import tkinter as tk
from threading import Thread

from PIL import Image, ImageTk

window = tk.Tk()

GRAY = "#1f1f01"
BLUE = "#7cdcfe"

APPLICATION_FONT_PATH = r"fonts\Source_Code_Pro\static\SourceCodePro-Regular.ttf"
DEFAULT_FONT = ("Source Code Pro", 13, "normal")

DEFAULT_BUTTON = {
    "borderwidth": 0,
    "background": BLUE,
    "activebackground": BLUE,
    "padx": 10,
    "font": DEFAULT_FONT,
    "fg": GRAY
}

DEFAULT_MENU_BUTTON = {
    "font": (DEFAULT_FONT[0], DEFAULT_FONT[1] - 1, DEFAULT_FONT[2]),
    "background": BLUE,
    "fg": GRAY,
    "activebackground": GRAY,
    "activeforeground": BLUE
}

DEFAULT_BUTTON_SIZE = {
    "height": 15
}

UNHIGHLIGHTED_BUTTON = {
    "background": GRAY,
    "fg": BLUE
}

DEFAULT_ENTRY = {
    "borderwidth": 0,
    "highlightbackground": BLUE,
    "highlightcolor": BLUE,
    "highlightthickness": 2,
    "background": GRAY,
    "insertbackground": BLUE,
    "justify": tk.LEFT,
    "font": DEFAULT_FONT,
    "fg": BLUE
}

DEFAULT_LABEL = {
    "font": DEFAULT_FONT,
    "background": GRAY,
    "foreground": BLUE
}

DEFAULT_MENU = {
    "highlightbackground": GRAY,
    "highlightthickness": 1,
    "background": BLUE,
}

PROGRESS_BAR_WRAPPER = {
    "background": GRAY,
    "padx": 5,
    "pady": 5,
    "highlightbackground": BLUE,
    "highlightthickness": 2
}

FINISHED_GREEN = "#00ff00"

TOGGLE = (50, 25)

PLAY_PAUSE = (50, 50)

_images = []


def schedule(function, waitTimeMs=0):
    window.after(waitTimeMs, function)


def simple_tk_callback(func):
    def callback(*args):
        func()

    return callback


def _get_default_dict(class_type) -> dict:
    try:
        attr = getattr(sys.modules[__name__], "DEFAULT_" + class_type.upper())
        if isinstance(attr, dict):
            return attr
    except AttributeError:
        pass
    return {}


def make_text_widget_ex(class_type: str, master: tk.Misc, text: str, **kwargs) -> (tk.Widget, tk.StringVar):
    string_var = tk.StringVar()
    string_var.set(text)
    kwargs["textvariable"] = string_var
    try:
        return getattr(tk, class_type)(master, **kwargs, **_get_default_dict(
            class_type)), string_var  # Gets the module attribute with the given class name and creates an instance of it
    except AttributeError:
        raise AttributeError("The tkinter module has no \"" + class_type + "\" class")


def make_text_widget(class_type: str, master, text: str, **kwargs):
    return make_text_widget_ex(class_type, master, text, **kwargs)[0]


def label_entry_group(master, entry_text: str, entry_width: int, label_text: str) -> (tk.Frame, tk.StringVar):
    frame = tk.Frame(master)
    label = make_text_widget("Label", frame, label_text, padx=20)
    entry, string_var = make_text_widget_ex("Entry", frame, entry_text, width=entry_width)
    label.grid(row=0, column=0)
    entry.grid(row=0, column=1)
    return frame, string_var


def label_switch_group(master, label_text: str) -> (tk.Frame, tk.BooleanVar):
    frame = tk.Frame(master)
    label = make_text_widget("Label", frame, label_text, padx=20)
    checkbox = Switch(frame)
    checkbox.button.grid(row=0, column=1)
    label.grid(row=0, column=0)
    return frame, checkbox.bool_var


def label_menu_group(master, label_text, *options):
    frame = tk.Frame(master)
    label = make_text_widget("Label", frame, label_text, padx=20)
    menu = Menu(frame, options[1], *options)
    menu.menu_button.grid(row=0, column=1)
    label.grid(row=0, column=0)
    return frame, menu


def spacer(master, width=0, height=0):
    return tk.Frame(master, width=width, background=GRAY)


def make_img_button(master, image_path, size, command=lambda *args: None):
    img = ImageTk.PhotoImage(Image.open(image_path).resize(size))
    _images.append(
        img)  # If this isn't stored somewhere permanently, it will be garbage collected and tk will not show it
    button = tk.Button(master, bd=-1, background=GRAY, activebackground=GRAY, image=img, command=command)
    return button


class Switch:
    def __init__(self, master, switch_type=TOGGLE, checked=True, onswitch=lambda checked: None):
        self.bool_var = tk.BooleanVar()
        self.bool_var.trace_add("write", simple_tk_callback(lambda: self.set_state(self.bool_var.get())))
        self._onswitch = onswitch
        if switch_type is TOGGLE:
            self._checkedImg = ImageTk.PhotoImage(Image.open("images/checked.png").resize(TOGGLE))
            self._uncheckedImg = ImageTk.PhotoImage(Image.open("images/unchecked.PNG").resize(TOGGLE))
        else:
            self._checkedImg = ImageTk.PhotoImage(Image.open("images/play.png").resize(PLAY_PAUSE))
            self._uncheckedImg = ImageTk.PhotoImage(Image.open("images/pause.png").resize(PLAY_PAUSE))

        self.button = tk.Button(master, bd=-1, background=GRAY, activebackground=GRAY)
        if checked:
            self.button.config(image=self._checkedImg)
        else:
            self.button.config(image=self._uncheckedImg)
        self.button.config(command=self.toggle)
        self.button.image = self._checkedImg
        self._checked = checked
        self.bool_var.set(self._checked)

    def toggle(self):
        self._checked = not self._checked
        self.bool_var.set(self._checked)
        if self._checked:
            self.button.config(image=self._checkedImg)
        else:
            self.button.config(image=self._uncheckedImg)
        self._onswitch(self._checked)

    def set_state(self, on: bool):
        if not self._checked and on or self._checked and not on:
            self.toggle()


class Menu:
    def __init__(self, master, displayed_option, *options):
        self._menu_open = False
        self._mouse_over_btn = False
        self._mouse_over_menu_frame = False
        self._dropdown = ImageTk.PhotoImage(Image.open("images/drop_down.PNG").resize((8, 8)))
        self.menu_button, self._selected_option = make_text_widget_ex("Button", master, displayed_option)
        self.menu_button.config(image=self._dropdown, compound=tk.RIGHT)
        window.bind("<Button-1>", self._toggle_visibility)

        @simple_tk_callback
        def mouse_enter_btn():
            self._mouse_over_btn = True

        @simple_tk_callback
        def mouse_leave_btn():
            self._mouse_over_btn = False

        @simple_tk_callback
        def mouse_enter_menu_frame():
            self._mouse_over_menu_frame = True

        @simple_tk_callback
        def mouse_leave_menu_frame():
            self._mouse_over_menu_frame = False

        self.menu_button.bind("<Enter>", mouse_enter_btn)
        self.menu_button.bind("<Leave>", mouse_leave_btn)
        self.displayed_option = displayed_option
        self.options = options
        self._menu_frame = tk.Frame(window, DEFAULT_MENU)
        self._menu_frame.bind("<Enter>", mouse_enter_menu_frame)
        self._menu_frame.bind("<Leave>", mouse_leave_menu_frame)
        for i in range(len(options)):
            @simple_tk_callback
            def display_chosen_option(index=i):  # See https://docs.python-guide.org/writing/gotchas/
                self._selected_option.set(options[index])
                self._hide()

            button = make_text_widget("Button", self._menu_frame, options[i])
            button.config(command=display_chosen_option, highlightbackground=GRAY, highlightthickness=1)
            button.config(DEFAULT_MENU_BUTTON)
            button.grid(row=i, column=0, sticky=tk.EW)

            @simple_tk_callback
            def on_btn_mouse_hover(widget=button):
                widget.config(**UNHIGHLIGHTED_BUTTON)

            @simple_tk_callback
            def on_btn_mouse_leave(widget=button):
                widget.config(**DEFAULT_MENU_BUTTON)

            button.bind("<Enter>", on_btn_mouse_hover)
            button.bind("<Leave>", on_btn_mouse_leave)

    def on_option_select(self, function):
        self._selected_option.trace_add("write", simple_tk_callback(function))

    def select_option(self, chosen_option: str):
        has_option = False
        for option in self.options:
            if chosen_option==option:
                has_option = True
        if not has_option:
            raise AttributeError(f"Menu object has no '{chosen_option}' option")
        self._selected_option.set(chosen_option)

    def get_selected_option(self):
        return self._selected_option.get()

    def _hide(self):
        self._menu_frame.place_forget()
        self._menu_open = False

    def _toggle_visibility(self, *args):
        if self._menu_open:
            if not self._mouse_over_menu_frame:
                self._hide()
        elif self._mouse_over_btn:
            self._menu_frame.place(x=self.menu_button.winfo_rootx() - window.winfo_rootx(),
                y=self.menu_button.winfo_rooty() - window.winfo_rooty() + self.menu_button.winfo_height(),
                anchor=tk.NW)
            self._menu_frame.config(padx=0)
            for i in range(10):
                self._menu_frame.lift()
            self._menu_open = True


class HighlightedButtonPair:
    def __init__(self, master, first_button_text, second_button_text, highlighted: int = 0,
                 first_button_command=lambda: None, second_button_command=lambda: None, onSwitch=lambda i: None):
        self.frame = tk.Frame(master, padx=5, pady=5, background=GRAY, highlightbackground=BLUE, highlightthickness=2)

        def make_btn_cmd(cmd, target):
            def new_cmd():
                self.select(target)
                cmd()

            return new_cmd

        self._on_switch = onSwitch
        self.first_button = make_text_widget("Button", self.frame, first_button_text,
            command=make_btn_cmd(first_button_command, target=0))
        self.second_button = make_text_widget("Button", self.frame, second_button_text,
            command=make_btn_cmd(second_button_command, target=1))
        self._highlighted = None
        self.select(highlighted)
        self.first_button.grid(row=0, column=0)
        spacer(self.frame, width=5).grid(row=0, column=1)
        self.second_button.grid(row=0, column=2)

    def get_highlighted_button(self) -> int:
        return self._highlighted

    def select(self, target):
        current = self._highlighted
        if 2 > target==int(target):
            self._highlighted = target
        else:
            raise AttributeError("The value of the '_highlighted' argument must be an integer of 0 or 1")
        if target==0:
            self.second_button.config(**UNHIGHLIGHTED_BUTTON)
            self.first_button.config(**DEFAULT_BUTTON)
        else:
            self.first_button.config(**UNHIGHLIGHTED_BUTTON)
            self.second_button.config(**DEFAULT_BUTTON)
        if current!=self._highlighted:
            self._on_switch(self._highlighted)


class ProgressBar(Thread):
    def __init__(self, master, size: tuple[float, float], animated=False):
        super().__init__()
        self.name = "progress bar thread"
        self.daemon = True
        self._size = size
        self.bar = tk.Canvas(master, width=size[0], height=size[1], background=GRAY, highlightthickness=2,
            highlightbackground=BLUE)
        self.bar.create_rectangle((0, 0), self._size, fill=GRAY)
        self._progress_percent = 0
        self._displayed_progress = 0
        self._last_displayed_progress = 0
        self._animated = animated
        self.start()

    def reset(self):
        self._displayed_progress = 0
        self.update(0)

    def update(self, progress_percent):
        progress_percent = round(progress_percent, 2)
        if 0 > progress_percent > 1:
            raise AttributeError("The 'progressPercent' argument must be a number between 0 and 1")
        else:
            self._progress_percent = progress_percent
            if not self._animated:
                self._displayed_progress = self._progress_percent

    def run(self):
        while True:
            try:
                self._displayed_progress += (self._progress_percent - self._displayed_progress) / 10
                if self._last_displayed_progress > self._displayed_progress:
                    self.bar.delete("all")
                self.bar.create_rectangle((0, 0), (self._displayed_progress * self._size[0] + 2, self._size[1] + 2),
                    fill=BLUE)
                self._last_displayed_progress = self._displayed_progress
            except tkinter.TclError:
                pass
            finally:
                time.sleep(0.04)


class Readout:
    def __init__(self, string_var: tk.StringVar, label: tk.Label, prefix: str):
        self._string_var = string_var
        self._label = label
        self._label.config(textvariable=string_var, **DEFAULT_LABEL)
        self._prefix = prefix

    def get_label(self):
        return self._label

    def update(self, value):
        self._label.after(0, self._string_var.set(self._prefix + str(value)))

    def recolor(self, color: str):
        self._label.after(0, lambda: self._label.config(fg=color))
