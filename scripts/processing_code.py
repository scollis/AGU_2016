"""
scipts.processing_code
=========================
Common core processing code across the AGU poster

.. autosummary::
    :toctree: generated/
    hello_world
"""

import pyart
import netCDF4
import os
import fnmatch
import datetime
from scipy import ndimage, signal, integrate
import time
import skfuzzy as fuzz
import numpy as np
import copy

WAVE_VERSION = 'First'

def hello_world():
    #placeholder file
    print('why hello ', WAVE_VERSION, ' wave')

def snr_and_sounding(radar, soundings_dir):
    radar_start_date = netCDF4.num2date(radar.time['data'][0],
                                        radar.time['units'])
    sonde_pattern = datetime.datetime.strftime(radar_start_date,
                        'sgpinterpolatedsondeC1.c1.%Y%m%d.*')
    all_sonde_files = os.listdir(soundings_dir)
    sonde_name = fnmatch.filter(all_sonde_files, sonde_pattern)[0]
    print(sonde_pattern,sonde_name)
    interp_sonde = netCDF4.Dataset(os.path.join( soundings_dir, sonde_name))
    temperatures = interp_sonde.variables['temp'][:]
    times = interp_sonde.variables['time'][:]
    heights = interp_sonde.variables['height'][:]
    my_profile = pyart.retrieve.fetch_radar_time_profile(interp_sonde, radar)
    info_dict = {'long_name': 'Sounding temperature at gate',
                 'standard_name' : 'temperature',
                 'valid_min' : -100,
                 'valid_max' : 100,
                 'units' : 'degrees Celsius'}
    z_dict, temp_dict = pyart.retrieve.map_profile_to_gates(my_profile['temp'],
                                             my_profile['height']*1000.0,
                                             radar)
    snr = pyart.retrieve.calculate_snr_from_reflectivity(radar)
    return z_dict, temp_dict, snr

def get_texture(radar):
    nyq = radar.instrument_parameters['nyquist_velocity']['data'][0]
    start_time = time.time()
    data = ndimage.filters.generic_filter(radar.fields['velocity']['data'],
                                                pyart.util.interval_std,
                                                size = (4,4),
                                               extra_arguments = (-nyq, nyq))
    total_time = time.time() - start_time
    print(total_time)
    filtered_data = ndimage.filters.median_filter(data, size = (4,4))
    texture_field = pyart.config.get_metadata('velocity')
    texture_field['data'] = filtered_data
    return texture_field

#moment : [[start_up, finish_up, start_down, finish_down], weight]
def cum_score_fuzzy_logic(radar, mbfs = None,
                          debug = False, ret_scores = False,
                          hard_const = None):
    if mbfs == None:
        second_trip = {'velocity_texture' : [[0,0,80,90], 1.0],
                       'cross_correlation_ratio' : [[.5,.7,1,1], 0.0],
                       'normalized_coherent_power' : [[0,0,.5,.6], 3.0],
                       'height': [[0,0,5000,8000], 1.0],
                       'sounding_temperature' : [[-100,-100,100,100], 0.0],
                       'SNR' : [[15,20, 1000,1000],1.0]}

        rain = {'differential_phase_texture' : [[0,0,80,90], 1.0],
                       'cross_correlation_ratio' : [[0.94,0.96,1,1], 1.0],
                       'normalized_coherent_power' : [[0.4,0.5,1,1], 1.0],
                       'height': [[0,0,5000,6000], 0.0],
                       'sounding_temperature' : [[0,3,100,100], 2.0],
                       'SNR' : [[8,10, 1000,1000], 1.0]}

        snow = {'differential_phase_texture' : [[0,0,80,90], 1.0],
                       'cross_correlation_ratio' : [[0.85,0.9,1,1], 1.0],
                       'normalized_coherent_power' : [[0.4,0.5,1,1], 1.0],
                       'height': [[0,0,25000,25000], 0.0],
                       'sounding_temperature' : [[-100,-100,0,1.], 2.0],
                       'SNR' : [[8,10, 1000,1000], 1.0]}

        no_scatter = {'differential_phase_texture' : [[90,90,400,400], 0.0],
                       'cross_correlation_ratio' : [[0,0,0.1,0.2], 0.0],
                       'normalized_coherent_power' : [[0,0,0.1,0.2], 0.0],
                       'height': [[0,0,25000,25000], 0.0],
                       'sounding_temperature' : [[-100,-100,100,100], 0.0],
                       'SNR' : [[-100,-100, 8,10], 6.0]}

        melting = {'differential_phase_texture' : [[20,30,80,90], 0.0],
                       'cross_correlation_ratio' : [[0.6,0.7,.94,.96], 4.],
                       'normalized_coherent_power' : [[0.4,0.5,1,1], 0],
                       'height': [[0,0,25000,25000], 0.0],
                       'sounding_temperature' : [[-1.,0,3.5,5], 2.],
                       'SNR' : [[8,10, 1000,1000], 0.0]}

        mbfs = {'multi_trip': second_trip, 'rain' : rain,
                'snow' :snow, 'no_scatter' : no_scatter, 'melting' : melting}
    flds = radar.fields
    scores = {}
    for key in mbfs.keys():
        if debug: print('Doing ' + key)
        this_score = np.zeros(\
                flds[list(flds.keys())[0]]['data'].shape).flatten() * 0.0
        for MBF in mbfs[key].keys():
            this_score = fuzz.trapmf(flds[MBF]['data'].flatten(),
                         mbfs[key][MBF][0] )*mbfs[key][MBF][1] + this_score

        this_score = this_score.reshape(\
                flds[list(flds.keys())[0]]['data'].shape)
        scores.update({key: ndimage.filters.median_filter(\
                this_score, size = [3,4])})
    if hard_const != None:
        # hard_const = [[class, field, (v1, v2)], ...]
        for this_const in hard_const:
            if debug: print('Doing hard constraining ', this_const[0])
            key = this_const[0]
            const = this_const[1]
            fld_data = radar.fields[const]['data']
            lower = this_const[2][0]
            upper = this_const[2][1]
            const_area = np.where(np.logical_and(fld_data >= lower,
                fld_data <= upper))
            if debug: print(const_area)
            scores[key][const_area] = 0.0
    stacked_scores = np.dstack([scores[key] for key in scores.keys() ])
    #sum_of_scores = stacked_scores.sum(axis = 2)
    #print(sum_of_scores.shape)
    #norm_stacked_scores = stacked_scores
    max_score = stacked_scores.argmax(axis = 2)

    gid = {}
    gid['data'] = max_score
    gid['units'] = ''
    gid['standard_name'] = 'gate_id'

    strgs = ''
    i=0
    for key in scores.keys():
        strgs = strgs + str(i) + ': ' + key + ' '
        i = i + 1

    gid['long_name'] = 'Classification of dominant scatterer'
    gid['notes'] = strgs
    gid['valid_max'] = max_score.max()
    gid['valid_min'] = 0.0
    if ret_scores == False:
        rv = (gid, scores.keys())
    else:
        rv = (gid, scores.keys(), scores)
    return rv

def fix_rain_above_bb(gid_fld, rain_class, melt_class, snow_class):
    new_gid = copy.deepcopy(gid_fld)
    for ray_num in range(new_gid['data'].shape[0]):
        if melt_class in new_gid['data'][ray_num, :]:
            max_loc = np.where(new_gid['data'][ray_num, :] == melt_class)[0].max()
            rain_above_locs = np.where(new_gid['data'][ray_num, max_loc:] == rain_class)[0] + max_loc
            new_gid['data'][ray_num, rain_above_locs] = snow_class
    return new_gid

def do_my_fuzz(radar):
    second_trip = {'velocity_texture' : [[5.,6.,130.,130.], 5.0],
                   'cross_correlation_ratio' : [[.5,.7,1,1], 0.0],
                   'normalized_coherent_power' : [[0,0,.5,.6], 0.0],
                   'height': [[0,0,5000,8000], 0.0],
                   'sounding_temperature' : [[-100,-100,100,100], 0.0],
                   'SNR' : [[15,20, 1000,1000],1.0]}

    rain = {'velocity_texture' : [[0,0,4,6], 1.0],
                   'cross_correlation_ratio' : [[0.97,0.98,1,1], 1.0],
                   'normalized_coherent_power' : [[0.4,0.5,1,1], 1.0],
                   'height': [[0,0,5000,6000], 0.0],
                   'sounding_temperature' : [[2.,5.,100,100], 2.0],
                   'SNR' : [[8,10, 1000,1000], 1.0]}

    snow = {'velocity_texture' : [[0,0,4,6], 1.0],
                   'cross_correlation_ratio' : [[0.65,0.9,1,1], 1.0],
                   'normalized_coherent_power' : [[0.4,0.5,1,1], 1.0],
                   'height': [[0,0,25000,25000], 0.0],
                   'sounding_temperature' : [[-100,-100,.5,4.], 2.0],
                   'SNR' : [[8,10, 1000,1000], 1.0]}

    no_scatter = {'velocity_texture' : [[4.,5.,30.,30.], 2.0],
                   'cross_correlation_ratio' : [[0,0,0.1,0.2], 0.0],
                   'normalized_coherent_power' : [[0,0,0.1,0.2], 0.0],
                   'height': [[0,0,25000,25000], 0.0],
                   'sounding_temperature' : [[-100,-100,100,100], 0.0],
                   'SNR' : [[-100,-100, 8,10], 4.0]}

    melting = {'velocity_texture' : [[0,0,4,6], 1.5],
                   'cross_correlation_ratio' : [[0.6,0.65,.9,.96], 3.5],
                   'normalized_coherent_power' : [[0.4,0.5,1,1], 0],
                   'height': [[0,0,25000,25000], 0.0],
                   'sounding_temperature' : [[0,0.5,6,7], 1.],
                   'SNR' : [[8,10, 1000,1000], 0.0]}

    mbfs = {'multi_trip': second_trip, 'rain' : rain,
            'snow' :snow, 'no_scatter' : no_scatter, 'melting' : melting}

    hard_const = [['melting' , 'sounding_temperature', (10, 100)],
                  ['multi_trip', 'height', (10000, 1000000)],
                  ['melting' , 'sounding_temperature', (-10000, -2)]]

    gid_fld, cats = cum_score_fuzzy_logic(radar, mbfs = mbfs, debug = True, hard_const = hard_const)
    return fix_rain_above_bb(gid_fld, 3, 1, 5), cats

