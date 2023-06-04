#!/usr/bin/env python3

"""Runs a local webserver that's used to show the charts and add human input to the study data."""


import os

import flask
import yaml


STUDIES_DIR = 'studies'
APP = flask.Flask(__name__,
                  static_url_path='',
                  template_folder='templates')


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
    img_path = os.path.join(STUDIES_DIR, study_date, f'{image_name}.png')
    if not os.path.exists(img_path):
        return flask.abort(404)
    return flask.send_file(img_path, mimetype='image/png')


@APP.route('/studies/<study_date>')
def study(study_date):
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
                                 for_date=study_date)


if __name__ == '__main__':
    APP.run(port=8080, debug=True)
