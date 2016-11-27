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

if __name__ == "__main__":
    hello_world()
    top = '/lcrc/group/earthscience/radar/sgpstage/sur/'
    all_files = get_file_tree(top, '*.mdv')
    print('found ', len(all_files), ' files')
    print(all_files[0], all_files[len(all_files)/2],
            all_files[-1])

