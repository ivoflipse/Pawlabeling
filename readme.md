Paw Labeling
============

![Paw labeling tool](docs/images/Pawlabeling.png)

Overview
--------

Paw Labeling is a tool to process veterinary pressure measurements.
It can currently import RSscan and Zebris entire plate export-files.

It assumes all measurements are organized in folders as following:

    Dog Name 1
            |___ Measurement export file 1
            |___ Measurement export file 2
            |___ Measurement export file 3
    Dog Name 2
            |___ Measurement export file 1
            |___ Measurement export file 2
            |___ Measurement export file 3
    - ...
            |___ ...

This structure is loaded into a tree for navigation. Selecting a measurement will load it into the entire plate widget.
It will then try to load meta data, such as the location of the paws and their labels from memory, if available.
If this information is not available, it will try to track the individual contacts using a custom tracking algorithm
(which might not work for anything other than dogs) and let you manually label the contacts with their respective labels
(Left Front, LF; Left Hind, LH; Right Front, RF; Right Hind, RH).

The tool currently offers no options for viewing the results or fixing any issues with the tracking.

Features
--------

- Load measurements and track where the paws have made contact
- Enable manual labeling of the contacts with their respective paw and saving of the results for later use


Installation
-----

Requires Python 2 (2.6 or newer), I'm not sure whether my dependencies are supported by Python 3 yet.

I strongly recommend that you consider installing Python packages with pip, as in it is the current preferred method.
If you are using pip, you can directly install all the dependencies from the requirements file using
`pip install -r requirements.txt`

Alternatively, you can download a package manager like [Anaconda](http://continuum.io/downloads) or
a scientific distribution like [Python(x,y)](https://code.google.com/p/pythonxy/).
This is especially recommendable if you're not used to using Python and are a Windows user.
Please check whether you're using 32 or 64 bit Python, because you'll have to download the respective library versions.

In any case, you need to install:

- OpenCV
- PySide
- Numpy
- Scipy


Usage
-----

**1. Edit `settings/configuration.py` for your system**

Apply the following changes:

- Change `measurment_folder` to the folder containing all your measurements organized as described above.
- Change the `store_results_folder` to the folder where you'll be storing the paw labels and other results.
- Change brand to your specific brand (either "rsscan" or "zebris"), if your brand is not supported, please contact me.
- Change the frequency to your measurement frequency. Currently only one frequency for all measurements is supported, as this information is not generally available in all export files.
- Change the main_window height and width depending on your screen resolution and change the degree of interpolation if the images don't fit your screen.


**2. Run `pawlabeling.py` to start the tool**

It will automatically load the measurements, select the first one in the tree and look for contacts.
Furthermore, it will mark any incomplete steps as `Invalid` if they touch the edges of the plate or if they were not finished before the end of the measurement.

**3. Label all your contacts**

Use the keypad to label the currently selected paw (highlighted in yellow):

	7	9		LF	RF	
			->
	1	3		LH	RH

You can switch the currently selected contact by pressing `4` or `6`. Remove a label using `5` or undo the previous label using `Ctrl+Z`.

**4. Save your results**

After you've labeled all contacts, press `Ctrl+S` to save your results. Now you can select the next measurement for labeling. It will automatically load the previous results, so they can aid you while labeling.

Contact
----------

Post bugs and issues on github. Send other comments to Ivo Flipse: first last at geemail dotcom or @ivoflipse5