#!/usr/bin/env python3

"""Runs a local webserver that's used to show the charts and add human input to the study data."""


import os

import filelock
import flask
import yaml


STUDIES_DIR = 'studies'
APP = flask.Flask(__name__, static_url_path='', template_folder='templates')


@APP.route('/')
def index():
    return flask.redirect('/studies', code=302)


@APP.route('/studies')
def studies_list():
    dates_dirs = [d for d in os.listdir(STUDIES_DIR) if d[0].isnumeric()]
    return flask.render_template_string('''<html>
    <head><title>Studies</title></head>
    <body>
        <ul>{% for dir in dirs %}
        <li><a href="/studies/{{ dir }}">{{ dir }}</a></li>
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


@APP.route('/studies/<study_date>/<symbol>/trend', methods=['POST'])
def update_trend(study_date, symbol):
    """Updates the Trend value in the study.yaml file."""
    trend = flask.request.form.get('trend')
    if trend is None:
        return
    if trend not in ('uptrend', 'downtrend', 'sideways'):
        return
    study_yaml_file = os.path.join(STUDIES_DIR, study_date, 'study.yaml')
    lock = filelock.FileLock(study_yaml_file + '.lock')
    with lock:
        with open(study_yaml_file, 'r') as f:
            symbols = yaml.load(f, Loader=yaml.CSafeLoader)
        if symbol in symbols:
            symbols[symbol]['Trend'] = trend
        with open(study_yaml_file, 'w') as f:
            yaml.dump(symbols, f, Dumper=yaml.CSafeDumper, default_flow_style=False, explicit_start=True)
    print(f'File {study_yaml_file} updated with Trend={trend} for {symbol}')
    return flask.request.form


@APP.route('/studies/<study_date>')
def study(study_date):
    incomplete_only = bool(flask.request.args.get('incomplete_only', False))
    study_directory = os.path.join(STUDIES_DIR, study_date)
    if not os.path.exists(study_directory):
        return flask.abort(404)
    yaml_file = os.path.join(study_directory, 'study.yaml')
    with open(yaml_file, 'r') as f:
        symbols = yaml.load(f, Loader=yaml.CSafeLoader)
    # Transform data from by-symbol to by-basket
    baskets = {d['Basket']:{} for d in symbols.values()}
    for symbol, data in symbols.items():
        baskets[data['Basket']][symbol] = data
    # Render template
    return flask.render_template('study_review.html.jinja2',
                                 baskets=baskets, 
                                 for_date=study_date,
                                 incomplete_only=incomplete_only)


if __name__ == '__main__':
    APP.run(port=8080, debug=True)
