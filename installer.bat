@echo off
set /P user_input=Enter the installation directory:
set installation_dir="%user_input:"=%
set fonts_dir=\fonts
set images_dir=\images
set settings_dir=\settings

@echo on
@echo Building the exe file...

@pyinstaller "Power Supply Manager.spec" --noconfirm

@echo Successfully built the exe file.

@echo Packaging the exe...

@echo off
mkdir %installation_dir%"

mkdir %installation_dir%%fonts_dir%"
mkdir %installation_dir%%images_dir%"
mkdir %installation_dir%%settings_dir%"

@echo on
@echo "Copying the exe files to " %installation_dir%


@robocopy ".\dist\Power Supply Manager" %installation_dir%" /E
@robocopy .%fonts_dir% %installation_dir%%fonts_dir%" /E
@robocopy .%images_dir% %installation_dir%%images_dir%" /E
@robocopy .%settings_dir% %installation_dir%%settings_dir%" /E

@echo Process finished successfully.

@echo off
@pause