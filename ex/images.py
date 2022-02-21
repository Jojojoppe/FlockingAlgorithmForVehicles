import numpy as np 
import matplotlib.pyplot as plt
import matplotlib.colors as clr
import csv
import scipy.ndimage as ndimage
import scipy.signal as signal

COH = np.zeros([21, 20], dtype='f')
SEP = np.zeros([21, 20], dtype='f')
ALI = np.zeros([21, 20], dtype='f')
COL = np.zeros([21, 20], dtype='uint32')
FIT = np.zeros([21, 20], dtype='f')

with open("processed_rss.csv") as f:
    reader = csv.reader(f)
    rnum = -1
    for row in reader:
        rnum += 1
        if rnum==0:
            continue

        rl, rph, rcoh, rsep, rali, rcol = row

        i = int(np.ceil((float(rl))/5))
        j = int(np.ceil((float(rph))/0.05))
        
        COL[i, j] = int(rcol)
        if COL[i, j]==0:
            COH[i, j] = float(rcoh)
            ALI[i, j] = float(rali)
            SEP[i, j] = float(rsep)
        else:
            COH[i, j] = -1 # np.NAN
            ALI[i, j] = -1 # np.NAN
            SEP[i, j] = -1 # np.NAN

# Create fitness function
FIT = COH + ALI + SEP
globalmax = np.max(FIT)
FIT[FIT==0] = -1
FIT[FIT<0] = globalmax

plt.clf()
plt.tight_layout()

left  = 0.125  # the left side of the subplots of the figure
right = 0.9    # the right side of the subplots of the figure
bottom = 0.1   # the bottom of the subplots of the figure
top = 0.9      # the top of the subplots of the figure
wspace = 0.2   # the amount of width reserved for blank space between subplots
hspace = 0.45   # the amount of height reserved for white space between subplots
plt.subplots_adjust(left, bottom, right, top, wspace, hspace)

# Fittness
plt.subplot(111)
plt.title("score")
p = plt.imshow(FIT, extent=[0, 1, 105, 0], aspect='auto')
plt.ylabel('l')
plt.xlabel('ph')
plt.colorbar(p ,boundaries=np.linspace(0, globalmax, 256), values=np.linspace(0, globalmax, 255))

plt.savefig("images/score.png")