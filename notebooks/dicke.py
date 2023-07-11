import numpy as np

from rtlobs import collect as col
from rtlobs import utils as ut
from rtlobs import post_process as post

import time


t_per_iter = 10
t_max = 60
n_iter = int(t_max / t_per_iter)

print(f'Collecting data in {n_iter} segments for {t_max} s.')

t_arr = []
p_arr = []
noise_on_arr = []

ut.biast(1, index=0, gpio=0)
sdr = col.get_sdr()
t_start = time.time()
while n_iter > 0:
    print('Segments remaining:', n_iter, 'Elapsed time:', time.time() - t_start)
    ts, ps, noise_on = col.dicke(262144//8, 35.0, 2.32e6, 1420.4e6, t_per_iter, plot=False, sdr=sdr)
    t_arr += ts
    p_arr += ps
    noise_on_arr += noise_on
    n_iter -= 1
sdr.close()
ut.biast(0, index=0, gpio=0)

np.savez(f'../output/{t_start}_data_chunks.npz',  t=t_arr, p=p_arr, noise_on=noise_on_arr)