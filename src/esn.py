from tifffile import imread
import numpy as np
from reservoirpy.nodes import Reservoir, Ridge
import matplotlib.pyplot as plt

tif = './data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif'

#Creating the reservoir
reservoir = Reservoir(100, lr=0.5, sr=0.9)
readout = Ridge(ridge=1e-5)
model = reservoir >> readout

volume = imread(tif)

x = 141 #X Coord for pixel
y = 176 #Y Coord for pixel
z = 761 #Number of slices

train = 200 #Test runs

#Reshaping it by normalizing from u16int to a float64, then reshaping it to be from -1 to 1.
timeserie = volume[:, y, x].astype(np.float64)
timeserie = (timeserie - timeserie.mean()) / (timeserie.std() + 1e-12)
timeserie = timeserie.reshape(-1, 1)

#Next token prediction, resetting before testing, then testing dat
model.fit(timeserie[:train-1], timeserie[1:train], warmup=10)
model.reset()
pred = model.run(timeserie[train:-1])

#Plotting relevant data
plt.figure(figsize=(10, 5))
plt.plot(pred, color="red", label='Pred', alpha=0.8)
plt.plot(timeserie[train:-1], color="blue", label='True', alpha=0.2)
plt.xlabel(f'Pixel coordinate ({x}, {y}) at a timestep')
plt.ylabel(f'Pixel intensity value')
plt.legend()
plt.show()


#To reset reservoir to make each independent:
#reservoir.reset()

#x = 141, y = 176

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