#!/usr/bin/env python3

"""Runs a local webserver that's used to show the charts and add human input to the study data."""


import os

import filelock
import flask
import yaml


STUDIES_DIR = None
STUDY_DATA_FILE = None
APP = flask.Flask(__name__, static_url_path='', template_folder='templates')


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
        symbols = yaml.load(f, Loader=yaml.CSafeLoader)
    # Transform data from by-symbol to by-basket
    baskets = {d['Basket']:{} for d in symbols.values()}
    for symbol, data in symbols.items():
        baskets[data['Basket']][symbol] = data
    return baskets


def find_previous_study_date(this_study_date):
    study_dates = [d for d in os.listdir(STUDIES_DIR) if os.path.isdir(os.path.join(STUDIES_DIR, d))]
    study_dates.sort()
    try:
        return study_dates[study_dates.index(this_study_date) - 1]
    except IndexError:
        return None


@APP.route('/')
def index():
    return flask.redirect('/studies', code=302)


@APP.route('/studies')
def studies_list():
    dates_dirs = [d for d in os.listdir(STUDIES_DIR) if d[0].isnumeric()]
    return flask.render_template_string('''<html>
    <head><title>Studies</title></head>
    <body>
        <ul>{% for dir in dirs|sort(reverse=True) %}
        <li><a href="/studies/{{ dir }}?incomplete_only=true">{{ dir }}</a></li>
        {% endfor %}</ul>
    </body>
</html>''', dirs=dates_dirs)


@APP.route('/studies/<study_date>/<image_name>.png')
def chart(study_date, image_name):
    """Serves PNG files directly."""
    img_path = os.path.join(STUDIES_DIR, study_date, f'{image_name}.png')
    if not os.path.exists(img_path):
        return flask.abort(404)
    return flask.send_file(img_path, mimetype='image/png')


@APP.route('/studies/<study_date>/<symbol>/direction', methods=['POST'])
def update_direction(study_date, symbol):
    """Updates the Direction value in the study.yaml file."""
    direction = flask.request.form.get('direction')
    if direction is None:
        return
    if direction not in ('bullish', 'bearish', 'neutral'):
        return
    study_yaml_file = os.path.join(STUDIES_DIR, study_date, STUDY_DATA_FILE)
    lock = filelock.FileLock(study_yaml_file + '.lock')
    with lock.acquire():
        with open(study_yaml_file, 'r') as f:
            symbols = yaml.load(f, Loader=yaml.CSafeLoader)
        if symbol in symbols:
            symbols[symbol]['Direction'] = direction
        with open(study_yaml_file, 'w') as f:
            yaml.dump(symbols, f, Dumper=yaml.CSafeDumper, default_flow_style=False, explicit_start=True)
    print(f'File {study_yaml_file} updated with Direction={direction} for {symbol}')
    return flask.request.form


@APP.route('/studies/<study_date>')
def study(study_date):
    incomplete_only = bool(flask.request.args.get('incomplete_only', False))
    baskets = load_study_data(study_date)
    previous_baskets = load_study_data(find_previous_study_date(study_date))
    # Render template
    return flask.render_template('study_review.html.jinja2',
                                 baskets=baskets, 
                                 previous_baskets=previous_baskets,
                                 for_date=study_date,
                                 incomplete_only=incomplete_only)


if __name__ == '__main__':
    set_global_values()
    APP.run(port=8080, debug=True)
