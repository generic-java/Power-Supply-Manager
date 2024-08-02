# Overview

Power Supply Manager is a Python program designed to remotely control power supplies built by Magna Power. Its features
include data logging, manual control, and voltage profile tracking.

# Usage

## Connecting to your power supply

To connect to your power supply in Power Supply Manager, paste its TCPIP address into the "Machine address" entry box.
Once the power supply is connected, its identification will be displayed on the screen.

## Using profiles

Power Supply Manager can read two types of profiles "evenly spaced" and "ordered pairs."  All profiles must be comma
delimited value (CSV) files. Profiles can be loaded by clicking the "choose file" button. To repeat your profile, enter
the number of times you want it to loop in the "Loop" entry. If you would like the power supply voltage to reset to zero
once your experiment is over, set the "End at 0" switch to on. Once your profile is ready, hit the play button to start
it.

### Evenly spaced

Evenly spaced profiles are simply ordered lists of voltage setpoints. Simply create a column of voltage setpoints in
Microsoft Excel and save the spreadsheet as a CSV file. You can adjust the end time of your profile by entering your
desired time into the "Test time" entry.

### Ordered pairs

Ordered pairs profiles have two columns, with the left column representing time units in seconds and the right column
representing voltage setpoints.

### Custom

Custom profiles are built using three voltage setpoints. Power Supply Manager will take these setpoints and generate
more setpoints between them to create smooth ramps between your desired voltages.  "V0" represents the starting voltage
of the profile, which
occurs at t = 0.  "V1", "t1", "V2", and "t2" represent the next voltage setpoints of the profile and the times (in
seconds) at which you would like these voltages to be set. The "delay" option can be used to set a delay between ending
one profile loop
and starting the next one. Finally, the "step option" is used to calculate the time (in seconds) between generated
points in your custom profile. A lower step will increase the smoothness of your profile, but too low of a step may
cause lag.

## Manually controlling your power supply

To manually control your power supply, select the "Manual control" option. Then, enter your target power in Watts and
adjust the PID gains to the optimal level. To avoid damaging your electronics, start with a low P gain and gradually
bring it up to your desired level. Next, adjust the I and D gains if necessary. You can switch between manual and
automatic modes while running an active experiment.

## Saving your data

Power Supply Manager will collect current, voltage, and power data from your power supply and save it after the
experiment ends. You can choose which folder you would like the data to be saved to be clicking the "Choose folder"
button.

# Building an EXE

After editing the code, you can make a swanky EXE file by running the "installer" batch file in the root directory of
this project.