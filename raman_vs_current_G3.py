#%%
import pyvisa as visa
import numpy as np
import sys
import os
from instrument_connection.scripts import AQ6315
from module_connection import module_connection as mc
from module_connection import NKTP_DLL as nk
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import time
# %%

# %%
rm = visa.ResourceManager()
instruments = np.array(rm.list_resources())
print(instruments)

nk.openPorts(nk.getAllPorts(), 0, 0)
portlist = nk.getAllPorts().split(',')
for port in portlist:
    result, devList = nk.deviceGetAllTypes(port)
    if result == 0:
        comport = port
print(port)
osa_address_long = instruments[['GPIB' in x for x in instruments]]
osa_address_short = osa_address_long[0].split('::')[1]
osa = AQ6315.OSA(address=osa_address_short)
#%%
osa.sweep_mode = 'SGL'
osa.trace = 'A'
osa.set_sample(1000)
osa.set_span(950, 1200)
osa.set_res(1)
osa.set_sens('SHI1')
osa.set_average_times(1)
#%%
booster = mc.boosterModule(comport, 5)
currents = np.array([0.7, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5])
booster.unlock()
booster.register_write('22', 0)  # Set booster current to zero
mainboard = mc.baseModule(comport, 15)
mainboard.register_write('32', 2)  # Set interlock to 2 (interlock off)
#%%
serial = 'K0109585'
base_path = os.path.join(os.getcwd(), 'data')

# uncoil_0deg, uncoil_45deg, coil_0deg, coil_45deg
extension = 'uncoil_0deg'
save_path = os.path.join(base_path, extension, serial)
if not os.path.isdir(save_path):
    os.mkdir(save_path)
#%%
mainboard.register_write('30', 1)  # Turn seed emission on
plt.pause(2)
osa.sweep()
osa.save(os.path.join(save_path, 'seed'))
fig = osa.plot_trace('A')
ax = fig.get_axes()[0]
ax.set_title('Seed')
ax.set_ylim([-90, 0])
fig.show()

mainboard.register_write('30', 2)  # Turn preamp emission on
print('b')
plt.pause(2)
osa.sweep()
osa.save(os.path.join(save_path, 'seed_preamp'))
fig = osa.plot_trace('A')
ax = fig.get_axes()[0]
ax.set_title('Seed + Preamp')
ax.set_ylim([-90, 0])
fig.show()
#%%
plt.close()
def handle_close(evt):
    global continue_measuring
    print ('Closed Figure, cancelling loop')
    continue_measuring = False

if len(currents) <= 10:
    cmap = plt.get_cmap('tab10')(np.arange(10, dtype=int))
else:
    cmap = plt.get_cmap('tab20')(np.arange(20, dtype=int))

fig, ax = plt.subplots()
fig.show()
ax.set_xlabel('Wavelength [nm]')
ax.set_ylabel('Power [dBm]')
fig.canvas.mpl_connect('close_event', handle_close)

continue_measuring = True
finished = False
booster.register_write('30', 2)
for indx, curr in enumerate(currents):
    if continue_measuring:
        ax.set_title('Now: ' + str(curr) + f' A [{indx/len(currents)*100:.1f}%]' )
        j = (indx)/len(currents)
        print("[%-20s] %d%%" % ('='*int(20*j), 100*j) +  '\t[' + str(int(curr*1000)) + ' A]', end='\r')
        fig.canvas.draw()
        booster.register_write('22', curr)  # Set booster current to curr
        plt.pause(1)
        read_curr = booster.register_read('1A')[0][0]  # Get the stage 2 current reading
        print(read_curr)
        osa.sweep()
        wl, int = osa.get_trace('A')
        ax.plot(wl, int, color=cmap[indx], label=str(curr)+'A')
        ax.legend(prop={'size': 14}, loc='upper right')
        fig.canvas.draw()
        osa.save(os.path.join(save_path, str(curr)+'A'))
        if indx == len(currents)-1:
            finished = True
    else:
        break

    if finished:
        ax.set_title(f'{serial}')
        fig.canvas.draw()
        # print('\n')
        # input('Press any key to exit')

ax.set_xlabel('Wavelength [nm]')
ax.set_ylabel('Power [dBm]')
# ax.set_title('Raman')
# ax.legend([str(x) + 'A' for x in currents])

booster.register_write('22', 0.7)  # Turn current down to 0.7 A
time.sleep(1)
booster.register_write('30', 0)  # Turn off booster emission
time.sleep(1)
mainboard.register_write('30', 1)  # Turn off preamp
time.sleep(1)
mainboard.register_write('30', 0)  # Turn off seed
