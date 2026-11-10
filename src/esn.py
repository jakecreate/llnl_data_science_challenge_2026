from tifffile import TiffFile, tifffile
import numpy as np
from PIL import Image
from reservoirpy.nodes import Reservoir
import matplotlib.pyplot as plt

tif = './data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif'

from reservoirpy.nodes import Reservoir
reservoir = Reservoir(100, lr=0.5, sr=0.9)

volume = tifffile.imread(tif)
# print(type(volume[0]))

states = np.empty((volume.shape[0], reservoir.output_dim))

print(volume[100].flatten())

# for i in range(volume.shape[0]):
#     states[i] = reservoir(volume[i].flatten())

# plt.figure(figsize=(10, 3))
# plt.title("Activation of 20 reservoir neurons.")
# plt.ylabel("$reservoir(volume[i])$")
# plt.xlabel("$t$")
# plt.plot(states[2, :])
# plt.show()

#Unsupervised training
#Time frame:
#1: Do next token prediction on a timeframe of just a pixel (This can be randomly chosen).

#-----

#Train on one slice
#Turn one slice into a data set (Tackle that)
#Ideal:
#Train ESN on each slice

#Can it classify
#What can ESN leverage that is useful to humans
##Using trained models to generalize to other slices
###Using a system to train and generalize to something else (Dont have train a model for every component (Reduction of computation complexity))