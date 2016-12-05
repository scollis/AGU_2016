#!/usr/bin/env python
"""
scripts.processsing
=========================
top level script for processing a cpol file from command line
on Argonne LCRC Blues

.. autosummary::
    :toctree: generated/
    hello_world
"""
from matplotlib import use
use('agg')
import processing_code as radar_codes
import os
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
import copy
import netCDF4
import skfuzzy as fuzz
import datetime
import platform
import fnmatch
import os



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

def process_a_volume(radar_fname, soundings_dir,
                     odir_radars,
                     odir_statistics, odir_images):
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

    #Sounding
    #SNR

    z_dict, temp_dict, snr = radar_codes.snr_and_sounding(radar, soundings_dir)
    texture =  radar_codes.get_texture(radar)

    #Calculate texture
    radar.add_field('sounding_temperature', temp_dict, replace_existing = True)
    radar.add_field('height', z_dict, replace_existing = True)
    radar.add_field('SNR', snr, replace_existing = True)
    radar.add_field('velocity_texture', texture, replace_existing = True)
    #Fuzzy logic construction of gate id
    my_fuzz, cats = radar_codes.do_my_fuzz(radar)
    radar.add_field('gate_id', my_fuzz,
                      replace_existing = True)

    #Var KDP
    #CSU KDP
    csu_kdp_field, csu_filt_dp, csu_kdp_sd = radar_codes.return_csu_kdp(radar)
    radar.add_field('bringi_differential_phase',
            csu_filt_dp, replace_existing = True)
    radar.add_field('bringi_specific_diff_phase',
            csu_kdp_field, replace_existing = True)
    radar.add_field('bringi_specific_diff_phase_sd',
            csu_kdp_sd, replace_existing = True)


    #LP KDP
    phidp, kdp = pyart.correct.phase_proc_lp(radar, 0.0,
            debug=True, fzl=3500.0)
    radar.add_field('corrected_differential_phase',
            phidp,replace_existing = True)
    radar.add_field('corrected_specific_diff_phase',
            kdp,replace_existing = True)

    #exract KDP and moments at Disdrometer sites
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
            + (lowest_lats - c1_dis_lat)**2)
    index = np.where(cost == cost.min())
    lon_locn = lowest_lons[index]
    lat_locn = lowest_lats[index]
    print(lat_locn, lon_locn)


    #save summaries of moments at sites
    dis_output_location = os.path.join(odir_statistics,
            ymd_string)
    if not os.path.exists(dis_output_location):
        os.makedirs(dis_output_location)
    dis_string = ''
    time_of_dis = netCDF4.num2date(radar.time['data'],
            radar.time['units'])[index[0]][0]
    tstring = datetime.datetime.strftime(time_of_dis,
            '%Y%m%d%H%H%S')
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

    #images
    im_output_location = os.path.join(odir_images, ymd_string)
    if not os.path.exists(im_output_location):
        os.makedirs(im_output_location)

    #-KDP compare
    display = pyart.graph.RadarMapDisplay(radar)
    fig = plt.figure(figsize = [15,7])
    plt.subplot(1,2,1)
    display.plot_ppi_map('bringi_specific_diff_phase',
                        sweep = 0, resolution = 'l',
                        mask_outside = False,
                        cmap = pyart.graph.cm.NWSRef,
                        vmin = 0, vmax = 6)
    plt.subplot(1,2,2)
    display.plot_ppi_map('corrected_specific_diff_phase',
                        sweep = 0, resolution = 'l',
                        mask_outside = False,
                        cmap = pyart.graph.cm.NWSRef,
                        vmin = 0, vmax = 6)

    plt.savefig(os.path.join(im_output_location,
                'csapr_kdp_comp_'+ymd_string+hms_string+'.png'))

    #determine radar file name
    r_output_location = os.path.join(odir_radars, ymd_string)
    if not os.path.exists(r_output_location):
        os.makedirs(r_output_location)
    rfilename = os.path.join(r_output_location,
            'csaprsur_' + ymd_string + '.' + 'hms_string.nc')

    #save radar file
    pyart.io.write_cfradial(rfilename, radar)


if __name__ == "__main__":
    my_system = platform.system()
    hello_world()
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
    test_file = '20110520/110635.mdv'
    t_radar = os.path.join(top, test_file)
    print(t_radar)
    process_a_volume(t_radar, s_dir,
                     odir_r, odir_s, odir_i)



