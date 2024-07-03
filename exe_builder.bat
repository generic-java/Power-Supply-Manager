@set /p output=Enter the output directory:

@pyinstaller "Power Supply Manager.spec"

@robocopy ./ "./dist/Power Supply Manager" icon.ico

@mkdir %output%

@echo "Copying the exe files to " %output%

@echo off

@robocopy "./dist/Power Supply Manager" %output% /E

@pause