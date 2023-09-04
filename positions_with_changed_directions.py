#!/usr/bin/env python

"""Find positions, given by a file, that have changed directional assumptions.

This is to aid in how early correction for positions whose directional assumptions
have changed since getting into the position. We often want to tighten up the profit
target and stop loss of a position that has switched directions since being in the
position.
"""


import argparse
import datetime
import os
import yaml


STUDIES_DIR = None
STUDY_DATA_FILE = None


def set_global_values():
    """Read config.yaml and load in global values of this script from that."""
    global STUDIES_DIR
    global STUDY_DATA_FILE
    with open('config.yaml') as f:
        config = yaml.load(f, Loader=yaml.CSafeLoader)
    STUDIES_DIR = config['Studies Base Directory']
    STUDY_DATA_FILE = config['Study Data File']


def load_study_data(study_date):
    if study_date is None:
        return {}
    study_directory = os.path.join(STUDIES_DIR, study_date)
    if not os.path.exists(study_directory):
        flask.abort(404)
    yaml_file = os.path.join(study_directory, STUDY_DATA_FILE)
    with open(yaml_file, 'r') as f:
        return yaml.load(f, Loader=yaml.CSafeLoader)


def find_latest_study_date():
    today = datetime.date.today()
    dow = today.weekday()
    if dow == 4:  # Friday
        study_date = today.strftime('%Y-%m-%d')
    elif dow < 4:
        days_back = - (dow + 3)
        study_date = (today + datetime.timedelta(days=days_back)).strftime('%Y-%m-%d')
    else:
        days_back = 4 - dow
        study_date = (today + datetime.timedelta(days=days_back)).strftime('%Y-%m-%d')
    return study_date


def find_previous_study_date(this_study_date):
    study_dates = [d for d in os.listdir(STUDIES_DIR) if os.path.isdir(os.path.join(STUDIES_DIR, d))]
    study_dates.sort()
    try:
        return study_dates[study_dates.index(this_study_date) - 1]
    except IndexError:
        return None


def read_positions_file(positions_file):
    positions = {}
    with open(positions_file) as f:
        for line in f.readlines():
            symbol, direction = line.split()
            positions[symbol] = {'Direction': direction}
    return positions


def main(args):
    set_global_values()
    study_date = find_latest_study_date()
    study_data = load_study_data(study_date)
    prev_study_date = find_previous_study_date(study_date)
    prev_study_data = load_study_data(prev_study_date)
    positions = read_positions_file(args.positions_file)
    for symbol in positions:
        if symbol in study_data:
            position_direction = positions[symbol]['Direction']
            study_direction = study_data[symbol]['Direction']
            if position_direction != study_direction:
                print(f'{symbol}\t{position_direction} != {study_direction}', end='')
                # If previous study direction is what we're already in, make a note
                if symbol in prev_study_data:
                    prev_study_direction = prev_study_data[symbol]['Direction']
                    if prev_study_direction != study_direction and prev_study_direction == position_direction:
                        print(f'  # NOTE: direction is same as the previous study', end='')
                print()  # newline


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('positions_file')
    args = parser.parse_args()
    main(args)
