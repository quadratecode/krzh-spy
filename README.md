# About

This Python script monitors with ongoing developments in the Kantonsrat ZH with regards to legal revisions.

It filters all KRZH-affairs and the weekly dispatch according to a variety of keywords and criteria through the KRZH-API at [opendata.swiss](https://opendata.swiss/de). Furthermore, it scrapes the PDFs of the weekly dispatch for changes in laws and is able to differentiate between the main law ("Haupterlass") and any secondary laws ("Nebenerlasse"). The output is rendered as static HTML. Accuracy is satisfactory but not perfect.

This code base is in early development. It is *not production ready*.

A weekly output is displayed here: https://www.zhlaw.ch/

All data taken from [Opendata](https://opendata.swiss/en/dataset/web-service-des-geschaftsverwaltungssystems-des-kantonsrates-des-kantons-zurich)

A license will be added at a later date.

# Usage

1. Clone this repository
2. Install dependencies with `pip3 install -r requirements.txt`
3. Run `python3 main.py`
# ToDo

- [ ] Scrape revisions from laws marked as "Totalrevision"
- [ ] Scrape revisions from landscape PDFs
- [ ] General bug fixing and improvements
- [ ] Add license
