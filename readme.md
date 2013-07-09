Paw Labeling
============

Overview
--------

Paw Labeling is a tool to process veterinary pressure measurements.
It can currently import RSscan and Zebris entire plate export-files.

It assumes all measurements are organized in folders as following:

`
- Dog Name 1
        |___ Measurement export file 1
        |___ Measurement export file 2
        |___ Measurement export file 3
- Dog Name 2
        |___ Measurement export file 1
        |___ Measurement export file 2
        |___ Measurement export file 3
- ...
        |___ ...
`

This structure is loaded into a tree for navigation. Selecting a measurement will load it into the entire plate widget.
It will then try to load meta data, such as the location of the paws and their labels from memory, if available.
If this information is not available, it will try to track the individual contacts using a custom tracking algorithm
(which might not work for anything other than dogs) and let you manually label the contacts with their respective labels
(Left Front, LF; Left Hind, LH; Right Front, RF; Right Hind, RH).

The tool currently offers no options for viewing the results or fixing any issues with the tracking.