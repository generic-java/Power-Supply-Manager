SET /p output=Enter the output directory: 

SET dir=\__pycache__

SET dirPath="%output:"=%

SET settingsDir=\settings

SET pycache=%dirPath%%dir%"

SET settings=%dirPath%%settingsDir%"

@mkdir %output%
@robocopy ./ %output% icon.ico
@robocopy ./__pycache__ %pycache%
@robocopy ./ %output% main.py 
@robocopy ./ %output% power_supply_experiment.py
@robocopy ./ %output% tkutils.py
@robocopy ./settings %settings%

@pause