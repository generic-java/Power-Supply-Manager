import sys
import tkinter as tk

from PIL import Image, ImageTk

window = tk.Tk()

GRAY = "#1f1f01"
BLUE = "#7cdcfe"
DEFAULT_FONT = ("Microsoft New Tai Lue", 14, "bold")

DEFAULT_BUTTON = {
    "borderwidth": 0,
    "background": BLUE,
    "activebackground": BLUE,
    "padx": 10,
    "font": DEFAULT_FONT,
    "fg": GRAY
}

DEFAULT_MENU_BUTTON = {
    "font": ("Microsoft New Tai Lue", 13, "bold"),
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

FINISHED_GREEN = "#00ff00"


def simpleTKCallback(func):
    def callback(*args):
        func()

    return callback


def _getDefaultDict(classType) -> dict:
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
        return getattr(tk, classType)(master, kwargs, **_getDefaultDict(classType)), stringVar  # Gets the module attribute with the given class name and creates an instance of it
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


def labelCheckButtonCombo(master, labelText: str) -> (tk.Frame, tk.BooleanVar):
    frame = tk.Frame(master)
    label = makeTextWidget("Label", frame, labelText, padx=20)
    boolVar = tk.BooleanVar()
    boolVar.set(True)
    checkbox = SimpleCheckbox(frame)
    checkbox.button.grid(row=0, column=1)
    label.grid(row=0, column=0)
    return frame, boolVar


def menuLabelCombo(master, labelText, *options):
    frame = tk.Frame(master)
    label = makeTextWidget("Label", frame, labelText, padx=20)
    menu = Menu(frame, options[1], *options)
    menu.menuButton.grid(row=0, column=1)
    label.grid(row=0, column=0)
    return frame, menu.selectedOption


class SimpleCheckbox:
    def __init__(self, master, checked=True):
        self.checked = Image.open("./checked.PNG").resize((50, 25))
        self.unchecked = Image.open("./unchecked.PNG").resize((50, 25))
        self.checked = ImageTk.PhotoImage(self.checked)
        self.unchecked = ImageTk.PhotoImage(self.unchecked)
        self.button = tk.Button(master, image=self.checked, bd=-1, background=GRAY, activebackground=GRAY)
        self.button.config(command=self.toggle)
        self.button.image = self.checked
        self._checked = checked

    def toggle(self):
        self._checked = not self._checked
        if self._checked:
            self.button.config(image=self.checked)
        else:
            self.button.config(image=self.unchecked)


class Menu:
    def __init__(self, master, displayedOption, *options):
        self._menuOpen = False
        self._mouseOverBtn = False
        self._mouseOverMenuFrame = False
        self._dropdown = ImageTk.PhotoImage(Image.open("./drop_down.PNG").resize((8, 8)))
        self.menuButton, self.selectedOption = makeTextWidgetEx("Button", master, displayedOption)
        self.menuButton.config(image=self._dropdown, compound=tk.RIGHT)
        window.bind("<Button-1>", self._toggleVisibility)

        @simpleTKCallback
        def mouseEnterBtn():
            self._mouseOverBtn = True

        @simpleTKCallback
        def mouseLeaveBtn():
            self._mouseOverBtn = False

        @simpleTKCallback
        def mouseEnterMenuFrame():
            self._mouseOverMenuFrame = True

        @simpleTKCallback
        def mouseLeaveMenuFrame():
            self._mouseOverMenuFrame = False

        self.menuButton.bind("<Enter>", mouseEnterBtn)
        self.menuButton.bind("<Leave>", mouseLeaveBtn)
        self.displayedOption = displayedOption
        self.options = options
        self._menuFrame = tk.Frame(window, DEFAULT_MENU)
        self._menuFrame.bind("<Enter>", mouseEnterMenuFrame)
        self._menuFrame.bind("<Leave>", mouseLeaveMenuFrame)
        for i in range(len(options)):
            @simpleTKCallback
            def displayChosenOption(index=i):  # See https://docs.python-guide.org/writing/gotchas/
                self.selectedOption.set(options[index])
                self._hide()

            button, stringVar = makeTextWidgetEx("Button", self._menuFrame, options[i])
            button.config(command=displayChosenOption, highlightbackground=GRAY, highlightthickness=1)
            button.config(DEFAULT_MENU_BUTTON)
            button.grid(row=i, column=0, sticky=tk.EW)

            @simpleTKCallback
            def onBtnMouseHover(widget=button):
                widget.config(**UNHIGHLIGHTED_BUTTON)

            @simpleTKCallback
            def onBtnMouseLeave(widget=button):
                widget.config(**DEFAULT_MENU_BUTTON)

            button.bind("<Enter>", onBtnMouseHover)
            button.bind("<Leave>", onBtnMouseLeave)

    def _hide(self):
        self._menuFrame.place_forget()
        self._menuOpen = False

    def _toggleVisibility(self, *args):
        if self._menuOpen:
            if not self._mouseOverMenuFrame:
                self._hide()
        elif self._mouseOverBtn:
            self._menuFrame.place(x=self.menuButton.winfo_rootx() - window.winfo_rootx(), y=self.menuButton.winfo_rooty() - window.winfo_rooty() + self.menuButton.winfo_height(), anchor=tk.NW)
            self._menuFrame.config(padx=0)
            for i in range(10):
                self._menuFrame.lift()
            self._menuOpen = True


class HighlightedButtonPair:
    def __init__(self, master, firstButtonText, secondButtonText, highlighted: int = 0, firstButtonCommand=lambda: None, secondButtonCommand=lambda: None, onSwitch=lambda i: None):
        self.frame = tk.Frame(master, padx=5, pady=5, background=GRAY, highlightbackground=BLUE, highlightthickness=2)
        rightSpacer = tk.Frame(self.frame, width=5, background=GRAY)

        def makeBtnCmd(cmd, target):
            def newCmd():
                self._highlight(target)
                cmd()

            return newCmd

        self._onSwitch = onSwitch
        self.firstButton = makeTextWidget("Button", self.frame, firstButtonText, command=makeBtnCmd(firstButtonCommand, target=0))
        self.secondButton = makeTextWidget("Button", self.frame, secondButtonText, command=makeBtnCmd(secondButtonCommand, target=1))
        self._highlighted = None
        self._highlight(highlighted)
        self.firstButton.grid(row=0, column=0)
        rightSpacer.grid(row=0, column=1)
        self.secondButton.grid(row=0, column=2)

    def getHighlighted(self):
        return self._highlighted

    def _highlight(self, target):
        current = self._highlighted
        if 2 > target==int(target):
            self._highlighted = target
        else:
            raise AttributeError("The value of the '_highlighted' argument must be an integer of 0 or 1")
        if target==0:
            self.secondButton.config(**UNHIGHLIGHTED_BUTTON)
            self.firstButton.config(**DEFAULT_BUTTON)
        else:
            self.firstButton.config(**UNHIGHLIGHTED_BUTTON)
            self.secondButton.config(**DEFAULT_BUTTON)
        if current!=self._highlighted:
            self._onSwitch(self._highlighted)


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
