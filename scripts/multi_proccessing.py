#!/usr/bin/env python
"""
scripts.multi_processsing
=========================
top level script for processing a cpol file from command line
on Argonne LCRC Blues

.. autosummary::
    :toctree: generated/
    hello_world
"""
from matplotlib import use
use('agg')
#import processing_code as radar_codes
import sys
from glob import glob
from datetime import datetime
import os, platform
import pyart
import netCDF4
from matplotlib import pyplot as plt
import matplotlib
import numpy as np
from scipy import ndimage, signal, integrate
import time
from time import sleep
import copy
import netCDF4
#import skfuzzy as fuzz
import datetime
import fnmatch
from IPython.parallel import Client



def hello_world():
    #placeholder file
    print('why hello Argonne')
    radar_codes.hello_world()

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

def process_a_volume(packed):
    import imp
    radar_codes = imp.load_source('radar_codes',
            '/home/scollis/projects/AGU_2016/scripts/processing_code.py')

    #import importlib.util
    #spec = importlib.util.spec_from_file_location("radar_codes",
    #        "/home/scollis/projects/AGU_2016/scripts/processing_code.py")
    #radar_codes = importlib.util.module_from_spec(spec)
    #spec.loader.exec_module(foo)
    #foo.MyClass()
    from datetime import datetime
    import os, platform
    import pyart
    import netCDF4
    from matplotlib import pyplot as plt
    import matplotlib
    import numpy as np
    from scipy import ndimage, signal, integrate
    import time
    import copy
    import netCDF4
    import datetime
    import fnmatch
    """
    Process one volume of radar data

    Parameters
    ----------
    radar_fname : string
        fully qualified file name for radar

    odir_radar : string
        directory for radars to be saved to

    odir_statistics : string
        directory for summary files to be written to

    odir_images : string
        directory for images to be written to

    Returns
    -------
    state : TBD
        TBD
    """
    soundings_dir = packed['s_dir']
    odir_radars = packed['odir_r']
    odir_statistics = packed['odir_s']
    odir_images = packed['odir_i']
    radar_fname = packed['infile']


    #read radar file
    radar = pyart.io.read(radar_fname)
    print(radar.fields.keys())
    i_end = 975
    radar.range['data']=radar.range['data'][0:i_end]
    for key in radar.fields.keys():
        radar.fields[key]['data']= radar.fields[key]['data'][:, 0:i_end]
    radar.ngates = i_end

    #determine some string metatdata
    radar_start_date = netCDF4.num2date(radar.time['data'][0],
                                        radar.time['units'])
    print(radar_start_date)
    ymd_string = datetime.datetime.strftime(radar_start_date, '%Y%m%d')
    hms_string = datetime.datetime.strftime(radar_start_date, '%H%M%S')
    print(ymd_string, hms_string)

    dis_output_location = os.path.join(odir_statistics,
            ymd_string)
    if not os.path.exists(dis_output_location):
        os.makedirs(dis_output_location)

    status_fn = os.path.join(dis_output_location, 'status_' +
            ymd_string+hms_string+'.txt')

    status_fh = open(status_fn, 'w')
    status_fh.write('Read file in \n')
    status_fh.flush()

    z_dict, temp_dict, snr = radar_codes.snr_and_sounding(radar, soundings_dir)
    texture =  radar_codes.get_texture(radar)

    #Calculate texture
    radar.add_field('sounding_temperature', temp_dict, replace_existing = True)
    radar.add_field('height', z_dict, replace_existing = True)
    radar.add_field('SNR', snr, replace_existing = True)
    radar.add_field('velocity_texture', texture, replace_existing = True)
    status_fh.write('Texture done \n')
    status_fh.flush()

    #Fuzzy logic construction of gate id
    my_fuzz, cats = radar_codes.do_my_fuzz(radar)
    radar.add_field('gate_id', my_fuzz,
                      replace_existing = True)
    status_fh.write('FL done \n')
    status_fh.flush()


    #Var KDP
    #- create gatefilter
    rain_and_snow = pyart.correct.GateFilter(radar)
    rain_and_snow.exclude_all()
    rain_and_snow.include_equal('gate_id', 1)
    rain_and_snow.include_equal('gate_id', 3)
    rain_and_snow.include_equal('gate_id', 4)

    melt_locations = np.where(radar.fields['gate_id']['data'] == 1)
    kinda_cold = np.where(radar.fields['sounding_temperature']['data'] < 0)
    fzl_sounding = radar.gate_altitude['data'][kinda_cold].min()
    if len(melt_locations[0] > 1):
        fzl_pid = radar.gate_altitude['data'][melt_locations].mean()
        fzl = (fzl_pid + fzl_sounding)/2.0
    else:
        fzl = fzl_sounding

    if fzl > 5000:
        fzl = 3500.0

    #- run code
    m_kdp, phidp_f, phidp_r = pyart.retrieve.kdp_proc.kdp_maesaka(radar,
                                                                  gatefilter=rain_and_snow)
   #- Append fields
    radar.add_field('maesaka_differential_phase', m_kdp, replace_existing = True)
    radar.add_field('maesaka_forward_specific_diff_phase', phidp_f, replace_existing = True)
    radar.add_field('maesaka__reverse_specific_diff_phase', phidp_r, replace_existing = True)
    status_fh.write('mesaka done \n')
    status_fh.flush()

    #CSU KDP
    csu_kdp_field, csu_filt_dp, csu_kdp_sd = radar_codes.return_csu_kdp(radar)
    radar.add_field('bringi_differential_phase',
            csu_filt_dp, replace_existing = True)
    radar.add_field('bringi_specific_diff_phase',
            csu_kdp_field, replace_existing = True)
    radar.add_field('bringi_specific_diff_phase_sd',
            csu_kdp_sd, replace_existing = True)
    status_fh.write('CSU done \n')
    status_fh.flush()

    #LP KDP
    phidp, kdp = pyart.correct.phase_proc_lp(radar, 0.0,
            debug=True, fzl=fzl)
    radar.add_field('corrected_differential_phase',
            phidp,replace_existing = True)
    radar.add_field('corrected_specific_diff_phase',
            kdp,replace_existing = True)
    status_fh.write('LP done \n')
    status_fh.flush()

    #extract KDP and moments at Disdrometer sites
    height = radar.gate_altitude
    lats = radar.gate_latitude
    lons = radar.gate_longitude
    lowest_lats = lats['data']\
            [radar.sweep_start_ray_index['data']\
            [0]:radar.sweep_end_ray_index['data'][0],:]
    lowest_lons = lons['data']\
            [radar.sweep_start_ray_index['data']\
            [0]:radar.sweep_end_ray_index['data'][0],:]
    c1_dis_lat = 36.605
    c1_dis_lon = -97.485
    cost = np.sqrt((lowest_lons - c1_dis_lon)**2 \
            + (lowest_lats - c1_dis_lat)**2) #A cost function for searching
    index = np.where(cost == cost.min())
    lon_locn = lowest_lons[index]
    lat_locn = lowest_lats[index]
    print(lat_locn, lon_locn)


    #save summaries of moments at sites
    dis_string = ''
    time_of_dis = netCDF4.num2date(radar.time['data'],
            radar.time['units'])[index[0]][0]
    tstring = datetime.datetime.strftime(time_of_dis,
            '%Y%m%d%H%M%S')
    dis_string = dis_string + tstring + ' '
    for key in radar.fields.keys():
        dis_string = dis_string + key + ' '
        dis_string = dis_string +\
                str(radar.fields[key]['data'][index][0]) + ' '

    #Save other summary data
    write_dis_filename = os.path.join(dis_output_location,
                        'csapr_distro_'+ymd_string+hms_string+'.txt')
    dis_fh = open(write_dis_filename, 'w')
    dis_fh.write(dis_string)
    dis_fh.close()
    status_fh.write('Distro saved \n')
    status_fh.flush()

    #- QVP
    hts = np.linspace(radar.altitude['data'],15000.0 + radar.altitude['data'],61)
    flds =['reflectivity',
         'bringi_specific_diff_phase',
         'corrected_specific_diff_phase',
         'maesaka_differential_phase',
         'cross_correlation_ratio',
         'velocity_texture']
    my_qvp = radar_codes.retrieve_qvp(radar, hts, flds = flds)
    hts_string = 'height(m) '
    for htss in hts:
        hts_string = hts_string + str(int(htss)) + ' '

    write_qvp_filename = os.path.join(dis_output_location,
                                     'csapr_qvp_'+ymd_string+hms_string+'.txt')

    dis_fh = open(write_qvp_filename, 'w')
    dis_fh.write(hts_string + '\n')
    for key in flds:
        print(key)
        this_str = key + ' '
        for i in range(len(hts)):
            this_str = this_str + str(my_qvp[key][i]) + ' '
        this_str = this_str + '\n'
        dis_fh.write(this_str)
    dis_fh.close()
    status_fh.write('qvp saved \n')
    status_fh.flush()

    #images
    im_output_location = os.path.join(odir_images, ymd_string)
    if not os.path.exists(im_output_location):
        os.makedirs(im_output_location)

    #-KDP compare
    display = pyart.graph.RadarMapDisplay(radar)
    fig = plt.figure(figsize = [20,6])
    plt.subplot(1,3,1)
    display.plot_ppi_map('bringi_specific_diff_phase', sweep = 0, resolution = 'l',
                        mask_outside = False,
                        cmap = pyart.graph.cm.NWSRef,
                        vmin = 0, vmax = 6, title='Bringi/CSU')
    plt.subplot(1,3,2)
    display.plot_ppi_map('corrected_specific_diff_phase', sweep = 0, resolution = 'l',
                        mask_outside = False,
                        cmap = pyart.graph.cm.NWSRef,
                        vmin = 0, vmax = 6, title='Giangrande/LP')

    plt.subplot(1,3,3)
    display.plot_ppi_map('maesaka_differential_phase', sweep = 0, resolution = 'l',
                        mask_outside = False,
                        cmap = pyart.graph.cm.NWSRef,
                        vmin = 0, vmax = 6, title='North/Maesaka')

    plt.savefig(os.path.join(im_output_location,
                'csapr_kdp_comp_'+ymd_string+hms_string+'.png'))

    #determine radar file name
    r_output_location = os.path.join(odir_radars, ymd_string)
    if not os.path.exists(r_output_location):
        os.makedirs(r_output_location)
    rfilename = os.path.join(r_output_location,
            'csaprsur_' + ymd_string + '.' + hms_string + '.nc')

    #save radar file
    pyart.io.write_cfradial(rfilename, radar)
    plt.close(fig)
    status_fh.write('image saved \n')
    status_fh.flush()
    status_fh.close()
    return ymd_string + hms_string

def test_script(packed):
    import sys
    return packed['infile'] + sys.version

if __name__ == "__main__":
    a = int(sys.argv[1])
    b = int(sys.argv[2])
    my_system = platform.system()
    #hello_world()
    if my_system == 'Darwin':
        top = '/data/sample_sapr_data/sgpstage/sur/'
        s_dir = '/data/sample_sapr_data/sgpstage/interp_sonde/'
        odir_r = '/data/sample_sapr_data/agu2016/radars/'
        odir_s = '/data/sample_sapr_data/agu2016/stats/'
        odir_i = '/data/sample_sapr_data/agu2016/images/'
    elif my_system == 'Linux':
        top = '/lcrc/group/earthscience/radar/sgpstage/sur/'
        s_dir = '/lcrc/group/earthscience/radar/sgpstage/interp_sonde/'
        odir_r = '/lcrc/group/earthscience/radar/agu2016/radars/'
        odir_s = '/lcrc/group/earthscience/radar/agu2016/stats/'
        odir_i = '/lcrc/group/earthscience/radar/agu2016/images/'

    all_files = get_file_tree(top, '*.mdv')
    print('found ', len(all_files), ' files')
    print(all_files[0],
            all_files[int(len(all_files)/2)],
            all_files[-1])

    all_files.sort()
    all_radars = get_file_tree(odir_r, '*.nc')
    all_radars.sort()
    print('all_radars made ' , len(all_radars))

    mdv_pat = '%Y%m%d/%H%M%S.mdv'
    mdv_dates = [ datetime.strptime(this_mdv, mdv_pat) for this_mdv in all_files]

    nc_pat = 'csaprsur_%Y%m%d.%H%M%S.nc'
    nc_dates = [ datetime.strptime(this_nc.split('/')[-1], nc_pat) for this_nc in all_radars]

    not_done_yet = []
    for i in range(len(all_files)):
        if not mdv_dates[i] in nc_dates:
            not_done_yet.append(all_files[i])

    print('Files not done ', len(not_done_yet))


    packing = []
    if sys.argv[3] == 'check':
        to_do = files_not_done
    else:
        to_do = all_files

    for fn in to_do:
        this_rec = {'top' : top,
                's_dir' : s_dir,
                'odir_r' : odir_r,
                'odir_s' : odir_s,
                'odir_i' : odir_i,
                'infile' : os.path.join(top, fn)}
        packing.append(this_rec)

    good = False
    while not good:
        try:
            My_Cluster = Client()
            My_View = My_Cluster[:]
            print My_View
            print len(My_View)
            good = True
        except:
            print('no!')
            sleep(15)
            good = False

    #Turn off blocking so all engines can work async
    My_View.block = False

    #on all engines do an import of Py-ART
    My_View.execute('import matplotlib')
    My_View.execute('matplotlib.use("agg")')

    #Map the code and input to all workers
    if b > len(packing):
        b = len(packing)-1
        print('reducing')
    print(packing[a:b])
    result = My_View.map_async(process_a_volume, packing[a:b])
    #result = My_View.map_async(test_script, packing[0:100])

    #Reduce the result to get a list of output
    qvps = result.get()
    print(qvps)

