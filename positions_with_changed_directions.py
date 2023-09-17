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
from tabulate import tabulate
import yaml


STUDIES_DIR = None
STUDY_DATA_FILE = None


HIGHLIGHT = '\033[2;30;47m'
ENDCOLOR = '\033[0;0m'


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


def find_previous_study_dates(this_study_date):
    study_dates = [d for d in os.listdir(STUDIES_DIR) if os.path.isdir(os.path.join(STUDIES_DIR, d))]
    study_dates.sort()
    try:
        i = study_dates.index(this_study_date)
    except IndexError:
        return []
    else:
        return study_dates[:i]


def read_positions_file(positions_file):
    positions = {}
    with open(positions_file) as f:
        for line in f.readlines():
            symbol, direction = line.split()
            positions[symbol] = {'Direction': direction}
    return positions


def study_date_to_str(study_date):
    dt = datetime.datetime.strptime(study_date, '%Y-%m-%d')
    return dt.strftime('%b-%d')


def main(args):
    set_global_values()
    positions = read_positions_file(args.positions_file)
    study_date = find_latest_study_date()
    study_data = load_study_data(study_date)
    past_dates = find_previous_study_dates(study_date)
    past_dates.sort(reverse=True)
    past_dates = past_dates[:7]  #  past 7 weeks + this week ~= 2 months
    past_study_data = {d:load_study_data(d) for d in past_dates}
    table = []
    for symbol in positions:
        if symbol in study_data:
            position_direction = positions[symbol]['Direction']
            study_direction = study_data[symbol]['Direction']
            if position_direction != study_direction:
                row = [symbol, position_direction, study_direction]
                highlight_done = False
                for past_date in past_dates:
                    if symbol in past_study_data[past_date]:
                        direction = past_study_data[past_date][symbol]['Direction']
                        # Highlight first occurance of same direction as current
                        if not highlight_done and direction == position_direction:
                            direction = f'{HIGHLIGHT}{direction}{ENDCOLOR}'
                            highlight_done = True
                        row.append(direction)
                    else:
                        row.append(None)
                table.append(row)
    headers = ['Symbol', 'Pos-Dir', study_date_to_str(study_date)] + [study_date_to_str(d) for d in past_dates]
    print(tabulate(table, headers=headers))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('positions_file')
    args = parser.parse_args()
    main(args)
