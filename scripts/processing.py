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

def process_a_volume(radar_fname, sounding_dir,
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
    sonde_pattern = datetime.datetime.strftime(\
         radar_start_date,'sgpinterpolatedsondeC1.c1.%Y%m%d.*')
    all_sonde_files = os.listdir(sounding_dir)
    print(sounding_dir, len(all_sonde_files))
    sonde_name = fnmatch.filter(all_sonde_files, sonde_pattern)[0]
    print(sonde_pattern,sonde_name)
    interp_sonde = netCDF4.Dataset(os.path.join( sounding_dir, sonde_name))
    temperatures = interp_sonde.variables['temp'][:]
    times = interp_sonde.variables['time'][:]
    heights = interp_sonde.variables['height'][:]
    my_profile = pyart.retrieve.fetch_radar_time_profile(interp_sonde, radar)
    info_dict = {'long_name': 'Sounding temperature at gate',
                 'standard_name' : 'temperature',
                 'valid_min' : -100,
                 'valid_max' : 100,
                 'units' : 'degrees Celsius'}
    z_dict, temp_dict = pyart.retrieve.map_profile_to_gates( my_profile['temp'],
                                             my_profile['height']*1000.0,
                                             radar)
    radar.add_field('sounding_temperature', temp_dict, replace_existing = True)
    radar.add_field('height', z_dict, replace_existing = True)

    #SNR
    snr = pyart.retrieve.calculate_snr_from_reflectivity(radar)
    radar.add_field('SNR', snr, replace_existing = True)

    #Calculate texture

    #read aux files

    #Fuzzy logic construction of gate id

    #LP KDP

    #CSU KDP

    #Variatonal KDP
    phidp, kdp = pyart.correct.phase_proc_lp(radar,
                                             0.0, debug=True,
                                             fzl=3500.0)

    #exract KDP and moments at Disdrometer sites

    #save summaries of moments at sites

    #Save other summary data

    #determine radar file name

    #save radar file


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



