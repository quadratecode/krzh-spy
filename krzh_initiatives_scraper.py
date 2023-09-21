import requests
from bs4 import BeautifulSoup
from time import sleep
import json
import logging
import arrow

# Setup logging
logger = logging.getLogger(__name__)


# Main function to scrape data from the krzh dispatch
def krzh_initiatives():
    # Base ufl from opendata.swiss
    base_url = (
        "https://parlzhcdws.cmicloud.ch/parlzh5/cdws/Index/GESCHAEFT/searchdetails"
    )

    # Parameters for the API call
    params = {
        # Only return certain types of affairs
        "q": 'geschaeftsart any "parlamentarische initiative einzelinitiative behördeninitiative" sortBy beginn_start/sort.descending',
        "l": "de-CH",
        "s": "1",
        # Number of fetched entries, max is 1k
        "m": "300",
    }

    # Get the data from the API
    def parse_and_download(xml_data):
        soup = BeautifulSoup(xml_data, "lxml-xml")
        affairs = soup.find_all("Geschaeft")
        entries = []

        # Loop through all affairs
        for affair in affairs:
            legislative_steps = affair.find_all("AblaufschrittTyp")
            # Skip if there are no legislative steps
            if len(legislative_steps) == 0:
                continue
            for legislative_step in legislative_steps:
                action = legislative_step.text
                # Only add the entry if the action is a certain type
                if action.lower() in [
                    "zustimmung",
                    "ablehnung",
                    "vorläufig unterstützt",
                    "rückzug",
                    "Antrag Kommission",
                ]:
                    decision_parent = legislative_step.parent
                    vorlage_nr = affair.KRNr.text
                    vorlage_type = affair.Geschaeftsart.text
                    vorlage_title = affair.Titel.text

                    if decision_parent.StatusText is not None:
                        decision_abstract = decision_parent.StatusText.text
                    else:
                        decision_abstract = None
                    decision_date = arrow.get(
                        decision_parent.Sitzungsdatum.contents[-1].text,
                        ["YYYY-MM-DD", "DD.MM.YYYY", "YYYYMMDD"],
                    ).format("YYYYMMDD")

                    documents = affair.find_all("Dokument")
                    try:
                        last_document = documents[0]
                        edoc_id = last_document.eDocument["ID"]
                        versions = last_document.find_all("Version")
                        last_version = versions[-1]["Nr"]
                    except Exception as e:
                        logging.error(f"Error getting edoc_id or last_version: {e}")
                        continue

                    pdf_url = f"https://parlzhcdws.cmicloud.ch/parlzh5/cdws/Files/{edoc_id}/{last_version}/pdf"
                    # Add the data to entries
                    data = {
                        "vorlage_type": vorlage_type,
                        "vorlage_title": vorlage_title,
                        "krnr": vorlage_nr,
                        "decision": action,
                        "decision_abstract": decision_abstract,
                        "decision_date": decision_date.format("DD.MM.YYYY"),
                        "pdf_url": pdf_url,
                    }
                    entries.append(data)

        # Add the data to the JSON file
        with open("krzh_initiatives_data.json", "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=4, ensure_ascii=False)

        return entries

    try:
        response = requests.get(base_url, params=params)
        sleep(3)
        if response.status_code == 200:
            logging.info(f"API call successful. Parsing and downloading PDFs.")
            new_entries = parse_and_download(response.content)
            return new_entries
        else:
            logging.error(f"API call failed with status code {response.status_code}")
    except Exception as e:
        logging.error(f"Error during API call: {e}")


if __name__ == "__main__":
    krzh_initiatives()
