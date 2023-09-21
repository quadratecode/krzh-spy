# About

This Python script helps to keep up with ongoing developments in the Kantonsrat ZH with regards to legal revisions.

It monitors and filters all affairs and the weekly dispatch according to a variety of keywords and criteria through the krzh API at opendata.swiss. Furthermore, it scrapes the PDFs of the weekly dispatch for changes in laws with decent precision and is able to differentiate between  the main law ("Haupterlass") and any secondary laws ("Nebenerlasse"). The output is rendered as static HTML. Accuracy is satisfactory but not perfect.

This code base is in early development. It is *not production ready*.

A weekly output is displayed here: https://www.zhlaw.ch/

All data taken from: https://opendata.swiss/en/dataset/web-service-des-geschaftsverwaltungssystems-des-kantonsrates-des-kantons-zurich

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
