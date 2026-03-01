import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.cluster import DBSCAN
from sklearn.linear_model import LinearRegression, RANSACRegressor
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline

from .config import GLOBAL_TRENDS_DEFAULTS
from ..utils.utils import human_format


class PhaseCleaner:
    """
    Clean seismic picks per phase using polynomial regression
    and adaptive bounds.

    """

    def __init__(self, phase_order=None, k_dict=None, min_points=20):
        self.phase_order = phase_order or ["P", "Pn", "Pg", "S", "Sn", "Sg"]
        self.k_dict = k_dict or {
                                phase: 5 if phase in ["P", "Pn", "Pg"] else 5
                                for phase in self.phase_order
                            }
        self.min_points = min_points