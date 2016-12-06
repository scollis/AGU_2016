import pyart
import netCDF4
import numpy as np
import platform
from matplotlib import pyplot as plt
from glob import glob
import os
from datetime import datetime
from scipy import interpolate
import fnmatch
import matplotlib.dates as mdates
from pytmatrix.tmatrix import TMatrix, Scatterer
from pytmatrix.tmatrix_psd import TMatrixPSD, GammaPSD
from pytmatrix import orientation, radar, tmatrix_aux, refractive

from pytmatrix.psd import PSDIntegrator, GammaPSD
from IPython.parallel import Client
import pickle


#index all distrometer files

def get_file_tree(start_dir, pattern):
    """
    Make a list of all files matching pattern
    above start_dir

    Parameters
    ----------
    start_dir : string
        base_directory

    pattern : string
        pattern to match. Use * for wildcard

    Returns
    -------
    files : list
        list of strings
    """

    files = []

    for dir, _, _ in os.walk(start_dir):
        files.extend(glob(os.path.join(dir, pattern)))
    return files

def scatter_off_2dvd_packed(dicc):
    def drop_ar(D_eq):
        if D_eq < 0.7:
            return 1.0;
        elif D_eq < 1.5:
            return 1.173 - 0.5165*D_eq + 0.4698*D_eq**2 - 0.1317*D_eq**3 - \
                8.5e-3*D_eq**4
        else:
            return 1.065 - 6.25e-2*D_eq - 3.99e-3*D_eq**2 + 7.66e-4*D_eq**3 - \
                4.095e-5*D_eq**4

    d_diameters = dicc['1']
    d_densities = dicc['2']
    mypds = interpolate.interp1d(d_diameters,d_densities, bounds_error=False, fill_value=0.0)
    scatterer = Scatterer(wavelength=tmatrix_aux.wl_C, m=refractive.m_w_10C[tmatrix_aux.wl_C])
    scatterer.psd_integrator = PSDIntegrator()
    scatterer.psd_integrator.axis_ratio_func = lambda D: 1.0/drop_ar(D)
    scatterer.psd_integrator.D_max = 10.0
    scatterer.psd_integrator.geometries = (tmatrix_aux.geom_horiz_back, tmatrix_aux.geom_horiz_forw)
    scatterer.or_pdf = orientation.gaussian_pdf(20.0)
    scatterer.orient = orientation.orient_averaged_fixed
    scatterer.psd_integrator.init_scatter_table(scatterer)
    scatterer.psd = mypds # GammaPSD(D0=2.0, Nw=1e3, mu=4)
    radar.refl(scatterer)
    zdr=radar.Zdr(scatterer)
    z=radar.refl(scatterer)
    scatterer.set_geometry(tmatrix_aux.geom_horiz_forw)
    kdp=radar.Kdp(scatterer)
    A=radar.Ai(scatterer)
    return z,zdr,kdp,A


my_system = platform.system()
if my_system == 'Darwin':
    top = '/data/sample_sapr_data/sgpstage/sur/'
    s_dir = '/data/sample_sapr_data/sgpstage/interp_sonde/'
    d_dir = '/data/agu2016/dis/'
    odir_r = '/data/agu2016/radars/'
    odir_s = '/data/agu2016/stats/'
    odir_i = '/data/agu2016/images/'
elif my_system == 'Linux':
    top = '/lcrc/group/earthscience/radar/sgpstage/sur/'
    s_dir = '/lcrc/group/earthscience/radar/sgpstage/interp_sonde/'
    odir_r = '/lcrc/group/earthscience/radar/agu2016/radars/'
    odir_s = '/lcrc/group/earthscience/radar/agu2016/stats/'
    odir_i = '/lcrc/group/earthscience/radar/agu2016/images/'
    d_dir = '/lcrc/group/earthscience/radar/sgpstage/dis/'

all_dis_files = get_file_tree(d_dir, 'sgpvdisC1*.000000.cdf')
all_dis_files.sort()

for filename in all_dis_files[50::]:
    print(filename)
    sfx = filename.split('/')[-1].split('.')[2]
    ofile = d_dir + sfx + 'proccessed.pc'
    print(ofile)
    #filename = '/lcrc/group/earthscience/radar/sgpstage/dis/sgpvdisC1.b1.20110425.000000.cdf'
    distrodata = netCDF4.Dataset(filename, 'r')
    d_time = netCDF4.num2date(distrodata.variables['time'][:],
                        distrodata.variables['time'].units)
    m_numtime = mdates.date2num(d_time)
    diameters = distrodata.variables['drop_diameter'][:]
    densities = distrodata.variables['num_density'][:]
    drops = distrodata.variables['num_drops'][:]
    rwc = distrodata.variables['liquid_water_content'][:]
    distrodata.close()
    good_returns = np.where(rwc > 1.0)[0]
    n_dsds = len(good_returns)
    #print('Getting ready to scatter off ',n_dsds,' DSDs')
    n_dists = len(rwc)
    z2dvd = np.zeros(n_dists)
    kdp2dvd = np.zeros(n_dists)
    zdr2dvd = np.zeros(n_dists)
    A2dvd = np.zeros(n_dists)
    My_Cluster = Client()
    My_View = My_Cluster[:]
    print My_View
    print len(My_View)
    good = True
    #Turn off blocking so all engines can work async
    My_View.block = False

    My_View.execute('from scipy import interpolate')
    My_View.execute('from pytmatrix.tmatrix import TMatrix, Scatterer')
    My_View.execute('from pytmatrix.tmatrix_psd import TMatrixPSD, GammaPSD, PSDIntegrator')
    My_View.execute('from pytmatrix import orientation, radar, tmatrix_aux, refractive')

    print('Making the map!')
    mapme = []
    for i in range(len(rwc)):
        mapme.append({'1':diameters, '2':densities[i,:]})

    result = My_View.map_async(scatter_off_2dvd_packed, mapme)
    #result = My_View.map_async(test_script, packing[0:100])
    #Reduce the result to get a list of output
    qvps = result.get()
    print(qvps)

    pickle.dump( qvps,
                open( ofile, "wb" ) )

