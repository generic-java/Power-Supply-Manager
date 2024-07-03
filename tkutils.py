import sys
import tkinter as tk
from tkinter import ttk


GRAY = "#4a4d51"
BLUE = "#7cdcfe"
DEFAULT_FONT = ("Microsoft New Tai Lue", 13, "bold")

DEFAULT_BUTTON = {
    "borderwidth": 0,
    "background": BLUE,
    "padx": 15,
    "font": DEFAULT_FONT,
    "fg": GRAY
}

DEFAULT_ENTRY = {
    "borderwidth": 0,
    "highlightbackground": GRAY,
    "highlightthickness": 2,
    "justify": tk.LEFT,
    "font": DEFAULT_FONT,
    "fg": GRAY
}

DEFAULT_LABEL = {
    "font": DEFAULT_FONT,
    "background": GRAY,
    "fg": BLUE
}

DEFAULT_CHECKBUTTON = {
}

FINISHED_GREEN = "#00ff00"


def getDefaultDict(classType) -> dict:
    try:
        attr = getattr(sys.modules[__name__], "DEFAULT_" + classType.upper())
        if isinstance(attr, dict):
            return attr
    except AttributeError:
        pass
    return {}


def makeTextWidgetEx(classType: str, master: tk.Misc, text: str, **kwargs) -> (tk.Widget, tk.StringVar):
    stringVar = tk.StringVar()
    stringVar.set(text)
    kwargs["textvariable"] = stringVar
    try:
        return getattr(tk, classType)(master, kwargs, **getDefaultDict(
            classType)), stringVar  # Gets the module attribute with the given class name and creates an instance of it
    except AttributeError:
        raise AttributeError("The tkinter module has no \"" + classType + "\" class")


def makeTextWidget(classType: str, master, text: str, **kwargs):
    return makeTextWidgetEx(classType, master, text, **kwargs)[0]


def entryLabelCombo(master, entryText: str, entryWidth: int, labelText: str) -> (tk.Frame, tk.StringVar):
    frame = tk.Frame(master)
    label = makeTextWidget("Label", frame, labelText, padx=20)
    entry, stringVar = makeTextWidgetEx("Entry", frame, entryText, width=entryWidth)
    label.grid(row=0, column=0)
    entry.grid(row=0, column=1)
    return frame, stringVar


def entryCheckButtonCombo(master, labelText: str) -> (tk.Frame, tk.BooleanVar):
    frame = tk.Frame(master)
    label = makeTextWidget("Label", frame, labelText, padx=20)
    boolVar = tk.BooleanVar()
    boolVar.set(True)
    style = ttk.Style()
    style.configure('TCheckbutton', background=GRAY, borderwidth=0)
    checkButton = ttk.Checkbutton(frame, variable=boolVar, **DEFAULT_CHECKBUTTON)
    label.grid(row=0, column=0)
    checkButton.grid(row=0, column=1)
    return frame, boolVar


class Readout:
    def __init__(self, stringVar: tk.StringVar, label: tk.Label, prefix: str):
        self.__stringVar = stringVar
        self.__label = label
        self.__label.config(textvariable=stringVar, **DEFAULT_LABEL)
        self.__prefix = prefix

    def getLabel(self):
        return self.__label

    def update(self, value):
        self.__label.after(0, self.__stringVar.set(self.__prefix + str(value)))  # Booting this function call back to the main thread to avoid tkinter crashes

    def recolor(self, color: str):
        self.__label.config(fg=color)
