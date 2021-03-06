#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 24 15:44:57 2020

@author: bhossein
"""

import time
#from collections import defaultdict
#from functools import partial
#from multiprocessing import cpu_count
#from pathlib import Path
#from textwrap import dedent
import matplotlib.pyplot as plt
import numpy as np
import random
#import pandas as pd

#from sklearn.externals import joblib
from sklearn.model_selection import RepeatedStratifiedKFold, train_test_split
#from sklearn.preprocessing import LabelEncoder, StandardScaler

from ptflops import get_model_complexity_info
from thop import profile

#import torch

from torch import nn
from torch import optim
from torch.nn import functional as F
#from torch.optim.lr_scheduler import _LRScheduler
#from torch.utils.data import TensorDataset, DataLoader
#import datetime
#import pickle
#from git import Repo

import torch.quantization as qn
from torch.quantization import QuantStub, DeQuantStub

from torchsummary import summary

import pickle

import os
#abspath = os.path.abspath('test_classifier_GPU_load.py')
#dname = os.path.dirname(abspath)
#os.chdir(dname)

try:
    os.chdir('/home/bhossein/BMBF project/code_repo')
    data_dir = "/vol/hinkelstn/codes/"
    raw_data = "/vol/hinkelstn/data/"
except:
    os.chdir('C:\Hinkelstien\code_repo')
    data_dir = 'data/'
    raw_data = "C:/Hinkelstien/data/"

from my_data_classes import create_datasets_file, create_loaders, smooth,\
    create_datasets_win, create_datasets_cv
import my_net_classes
from my_net_classes import SepConv1d, _SepConv1d, Flatten, parameters
import torch
import pickle

from evaluation import evaluate
import option_utils

result_dir = 'results/' 
#data_dir = 'data/' 
#data_dir = '/vol/hinkelstn/codes/'
#if not os.path.exists(data_dir):
#    data_dir = 'data/'

import copy