#!/usr/bin/env python3

"""Generate HTML and Markdown pages from the trend data collected."""


import argparse
import os
import pathlib

import jinja2
import yaml


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


def main(args):
    yaml_file = os.path.join(args.study_directory, 'study.yaml')
    with open(yaml_file, 'r') as f:
        symbols = yaml.load(f, Loader=yaml.CSafeLoader)

    # Transform data from by-symbol to by-basket
    baskets = {d['Basket']:{} for d in symbols.values()}
    for symbol, data in symbols.items():
        baskets[data['Basket']][symbol] = data
    for_date = get_date_string_from_study_directory(args.study_directory)
    md_template = open('templates/study.md.jinja2').read()
    template = jinja2.Environment(loader=jinja2.BaseLoader).from_string(md_template)
    md_file = os.path.join(args.study_directory, 'study.md')
    with open(md_file, 'w') as f:
        f.write(template.render(baskets=baskets, for_date=for_date))
    print(f'File written: {md_file}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('study_directory')
    args = parser.parse_args()
    main(args)
