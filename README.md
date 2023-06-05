# Trend Review

This repository is a WIP. It's just a collection of code and scripts that are
used to get charts from FinViz and then build a long doc of those charts so that
I can manually review them. It is not very interesting.


## Setup

```shell
$ python3.9 -m venv env
$ source env/bin/activate
$ pip install -r requirements.txt
```

## TODOs

* Change "Trend" to "Price Action" and "Sentiment" instead.
* Scape the full company name from Finviz and store in YAML file.
* Add radio buttons on generated HTML for sentiment and have then send a POST to the local server.
* Add a cheap Flask test server that modified the YAML file when a POST is sent back.
