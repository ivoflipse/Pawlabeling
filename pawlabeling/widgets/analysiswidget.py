#-----------------------------------------------------------------------------
# Copyright (c) 2013, Paw Labeling Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from collections import defaultdict

from PySide.QtGui import *
import numpy as np

from functions import utility
from settings import configuration


class AnalysisWidget(QTabWidget):
    def __init__(self, parent):
        super(AnalysisWidget, self).__init__(parent)

