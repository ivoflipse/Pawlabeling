"""
contact Labeling is a tool to process (veterinary) pressure measurements.
===================================================================
"""
import numpy as np

__version__ = '0.3.0'

__all__ = ['functions', 'models', 'tests', 'settings', 'widgets',]


if not np.dtype(np.float).itemsize == 8:
    raise RuntimeError("scikit-clinicalgraphics requires np.float precision to be 64-bit")
