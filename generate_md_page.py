#!/usr/bin/env python3

"""Generate HTML and Markdown pages from the trend data collected."""


import argparse
import datetime
import os
import pathlib
import time

import jinja2
import yaml


STUDIES_BASE_DIR = None
STUDY_DATA_FILE = None
STUDY_MARKDOWN_FILE = None


def set_global_values():
    """Read config.yaml and load in global values of this script from that."""
    global STUDIES_BASE_DIR
    global STUDY_DATA_FILE
    global STUDY_MARKDOWN_FILE
    with open('config.yaml') as f:
        config = yaml.load(f, Loader=yaml.CSafeLoader)
    STUDIES_BASE_DIR = config['Studies Base Directory']
    STUDY_DATA_FILE = config['Study Data File']
    STUDY_MARKDOWN_FILE = config['Study Markdown File']


def load_study_data(study_date):
    if study_date is None:
        return {}
    study_directory = os.path.join(STUDIES_BASE_DIR, study_date)
    if not os.path.exists(study_directory):
        flask.abort(404)
    yaml_file = os.path.join(study_directory, STUDY_DATA_FILE)
    with open(yaml_file, 'r') as f:
        symbols = yaml.load(f, Loader=yaml.CSafeLoader)
    # Transform data from by-symbol to by-basket
    baskets = {d['Basket']:{} for d in symbols.values()}
    for symbol, data in symbols.items():
        baskets[data['Basket']][symbol] = data
    return baskets


def get_date_string_from_study_directory(study_directory):
    path = pathlib.Path(study_directory)
    year = month = day = None
    for part in path.parts:
        # Does not have dashes
        if part.isnumeric() and len(part) == 8:
            year = int(part[:4])
            month = int(part[4:6])
            day = int(part[6:8])
            break
        # Does have dashes
        elif part.count('-') == 2:
            year_str, month_str, day_str = part.split('-')
            if year_str.isnumeric() and month_str.isnumeric() and day_str.isnumeric():
                year = int(year_str)
                month = int(month_str)
                day = int(day_str)
                break
    if None in (year, month, day):
        raise ValueError(f'Directory {study_directory} does not contain a date-based directory')
    return '{}-{:02}-{:02}'.format(year, month, day)


def find_past_study_dates(this_study_date, back=3):
    """Find all of the studies in the past in date order from this study date."""
    study_dates = [d for d in os.listdir(STUDIES_BASE_DIR) if os.path.isdir(os.path.join(STUDIES_BASE_DIR, d))]
    study_dates.sort()
    idx = study_dates.index(this_study_date)
    try:
        return study_dates[idx - back:idx]
    except IndexError:
        return None


def add_custom_filters(j2_environment):
    """Add custom filters to a jinja2 environment.
    See https://jinja.palletsprojects.com/en/3.0.x/api/#custom-filters
    """
    def datestr2monthday(dstr):
        d = datetime.date(*time.strptime(dstr, '%Y-%m-%d')[:3])
        return d.strftime('%b %d')
    j2_environment.filters['datestr2monthday'] = datestr2monthday


def main(args):
    set_global_values()
    study_date = get_date_string_from_study_directory(args.study_directory)
    baskets = load_study_data(study_date)
    past_study_dates = find_past_study_dates(study_date)
    past_baskets = {sd:load_study_data(sd) for sd in past_study_dates}
    previous_basket = past_baskets[past_study_dates[-1]]

    # Load and render template
    md_template = open('templates/study.md.jinja2').read()
    j2env = jinja2.Environment(loader=jinja2.BaseLoader)
    add_custom_filters(j2env)
    template = j2env.from_string(md_template)
    md_file = os.path.join(args.study_directory, STUDY_MARKDOWN_FILE)
    with open(md_file, 'w') as f:
        f.write(template.render(
            baskets=baskets,
            past_baskets=past_baskets,
            previous_basket=previous_basket,
            study_date=study_date))
    print(f'File written: {md_file}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('study_directory')
    args = parser.parse_args()
    main(args)
