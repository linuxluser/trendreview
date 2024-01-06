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

* ~~Add a cheap Flask test server that modified the YAML file when a POST is sent back.~~
* ~~Add radio buttons on generated HTML for sentiment and have then send a POST to the local server.~~
* ~~Change "Trend" to "Direction", meaning "Directional Assumption".~~
* ~~Add no-chart table to each basket in the markdown file for copy-pasta goodness.~~
* Change data structure so that all symbols get located under "Symbols" key.
* Add "Price Action" data point.
* ~~Scape the full company name from Finviz and store in YAML file.~~
* Automatically determine direction (get via a reliable service).
