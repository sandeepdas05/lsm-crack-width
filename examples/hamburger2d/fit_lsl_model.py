import numpy as np

from level_set_learn import LevelSetLearn as LSL
from level_set_learn.feature_maps.dim2 import simple_feature_map as sfm
from level_set_learn.initialization_functions import random as rand_init

# Seed a random number generator.
rs = np.random.RandomState(1234)

# Set simple feature map function.
fmap = sfm.simple_feature_map(sigmas=[0,3])

# Set the level set init routine.
ifnc = rand_init.random(rs=rs)

# Initialize the model.
lsl = LSL(data_file="./dataset.h5", feature_map=fmap,
          init_func=ifnc, band=3.0, rs=rs)

# See documentation for complete list of fit options.
lsl.set_fit_options(maxiters=100, remove_tmp=True,
                    logfile="./log.txt", logstamp=False, logstdout=True)

# Finally, start the fitting process.
lsl.fit()

