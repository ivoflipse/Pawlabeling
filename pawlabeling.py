#-----------------------------------------------------------------------------
# Copyright (c) 2013, Paw Labeling Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from pawlabeling.widgets.mainwindow import main

if __name__ == "__main__":
    profile = False
    if profile:
        import cProfile
        cProfile.run("main()", sort="cumulative")
    else:
        main()

