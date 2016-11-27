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

def process_a_volume(radar_fname, odir_radars,
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

    #determine some string metatdata


    #Calculate texture

    #read aux files

    #Fuzzy logic construction of gate id

    #LP KDP

    #CSU KDP

    #Variatonal KDP

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
    elif my_system == 'Linux':
        top = '/lcrc/group/earthscience/radar/sgpstage/sur/'
    all_files = get_file_tree(top, '*.mdv')
    print('found ', len(all_files), ' files')
    print(all_files[0],
            all_files[int(len(all_files)/2)],
            all_files[-1])

