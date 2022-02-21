import numpy as np
import matplotlib.pyplot as pyplot
import csv

try:
    with open("processed_mean.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(['l', 'ph', 'coh', 'sep', 'ali', 'col'])

        for l in np.linspace(0, 100, 21):
            for ph in np.linspace(0, 0.95, 20):
                print('l%f-ph%f'%(l, ph))    
                with open('l%f-ph%f.csv'%(l, ph)) as f:
                    reader = csv.reader(f)
                    coh = 0
                    sep = 0
                    ali = 0
                    coli = 0
                    nrows = -1
                    for row in reader:
                        rframe, rtime, rposx0, rposx1, rposy0, rposy1, rvelx0, rvelx1, rvely0, rvely1, rdevx0, rdvelx1, rdvely0, rdvely1, rcoh, rali, rsep, rcol = row

                        nrows += 1
                        if nrows == 0:
                            continue

                        # Set amount of collisions directly
                        coli = int(rcol)

                        # Take mean of coh, sep and ali
                        coh += float(rcoh)
                        sep += float(rsep)
                        ali += float(rali)

                    coh /= nrows
                    ali /= nrows
                    sep /= nrows

                    writer.writerow([l, ph, coh/nrows, sep/nrows, ali/nrows, coli])
except:
    print("Some error")

try:
    with open("processed_rss.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(['l', 'ph', 'coh', 'sep', 'ali', 'col'])

        for l in np.linspace(0, 100, 21):
            for ph in np.linspace(0, 0.95, 20):
                print('l%f-ph%f'%(l, ph))    
                with open('l%f-ph%f.csv'%(l, ph)) as f:
                    reader = csv.reader(f)
                    coh = 0
                    sep = 0
                    ali = 0
                    coli = 0
                    nrows = -1
                    for row in reader:
                        rframe, rtime, rposx0, rposx1, rposy0, rposy1, rvelx0, rvelx1, rvely0, rvely1, rdevx0, rdvelx1, rdvely0, rdvely1, rcoh, rali, rsep, rcol = row

                        nrows += 1
                        if nrows == 0:
                            continue

                        # Set amount of collisions directly
                        coli = int(rcol)

                        coh += np.square(float(rcoh))
                        sep += np.square(float(rsep))
                        ali += np.square(float(rali))

                    writer.writerow([l, ph, coh/nrows, sep/nrows, ali/nrows, coli])
except:
    print("Some error")