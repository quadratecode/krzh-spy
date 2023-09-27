import requests
from bs4 import BeautifulSoup
import json
import logging
import arrow
from time import sleep
import re
import traceback

# Setup logging
logger = logging.getLogger(__name__)

# Base ufl from opendata.swiss
base_url_dispatch = (
    "https://parlzhcdws.cmicloud.ch/parlzh1/cdws/Index/KRVERSAND/searchdetails"
)

# Base URL vorlagen
base_url_vorlagen = (
    "https://parlzhcdws.cmicloud.ch/parlzh5/cdws/Index/GESCHAEFT/searchdetails"
)


def get_date_and_latest_ablaufschritt(vorlagen_nr):
    # Parameters
    params_vorlagen = {
        "q": f"vorlagennr any {vorlagen_nr} sortby beginn_start/sort.descending",
        # Number of fetched entries, max is 1k
        "m": "300",
        # Language
        "l": "de-CH",
    }

    # Make a request
    response = requests.get(base_url_vorlagen, params=params_vorlagen)
    response.raise_for_status()  # Raise an exception for HTTP errors

    # Parse the XML with BeautifulSoup
    soup = BeautifulSoup(response.content, "lxml")

    # Find the Ablaufschritt section with Antrag Regierungsrat
    rr_antrag_section = soup.find(
        "ablaufschritttyp", string="Antrag Regierungsrat"
    ).find_parent()

    # Extract the date from the Antrag Regierungsrat section
    date_tag = rr_antrag_section.find("text")
    rr_antrag_date = date_tag.text if date_tag else None

    # Initialize a dictionary to hold ablaufschritttyp and their respective dates
    date_dict = {}

    # Loop through all ablaufschritt sections
    for ablaufschritt in soup.find_all("ablaufschritt"):
        date_tag = ablaufschritt.find("text")
        if date_tag:
            date_str = date_tag.text
            # Convert the date string to an arrow object for comparison
            date_obj = arrow.get(date_str, "DD.MM.YYYY")  # Adjust format if needed
            ablaufschritttyp_tag = ablaufschritt.find("ablaufschritttyp")
            if ablaufschritttyp_tag:
                date_dict[ablaufschritttyp_tag.text] = date_obj

    # Find the ablaufschritttyp with the latest date
    latest_ablaufschritttyp = max(date_dict, key=date_dict.get)
    latest_date = date_dict[latest_ablaufschritttyp].format("DD.MM.YYYY")

    return rr_antrag_date, latest_ablaufschritttyp, latest_date


# Main function to scrape data from the krzh dispatch
def krzh_dispatch():
    # Parameters for the API call
    params_dispatch = {
        # Entries younger than 2040-01-01 to catch latest entries
        "q": 'datum_start < "2040-01-01 00:00:00" sortBy datum_start/sort.descending',
        # Number of fetched entries, max is 1k
        "m": "300",
        # Language
        "l": "de-CH",
    }

    # Load already scraped entries
    try:
        with open("krzh_dispatch_data.json", "r") as f:
            existing_data = json.load(f)
            stored_mails = [
                arrow.get(entry["Datum KR-Versand"], "DD.MM.YYYY")
                for entry in existing_data
            ]
    # If the entry doesn't exist, create an empty list
    except FileNotFoundError:
        existing_data = []
        stored_mails = []

    def parse_and_download(xml_data):
        soup = BeautifulSoup(xml_data, "lxml-xml")
        # Find all krzh entries, each entry contains multiple affairs
        dispatchs = soup.find_all("KRVersand")
        krversand_data = []

        for dispatch in dispatchs:
            # Get the date of the dispatch
            krversand_date = arrow.get(
                dispatch.Datum.contents[-1].text,
                ["YYYY-MM-DD", "DD.MM.YYYY", "YYYYMMDD"],
            )

            # Skip if the entry already exists
            if krversand_date in stored_mails:
                continue

            # Get all affairs from the dispatch, find_all is case sensitive
            affairs = [
                geschaeft
                for geschaeft in dispatch.find_all("Geschaeft")
                if geschaeft.find("Geschaeft") is not None
            ]

            entries = []
            # Loop through all affairs
            for affair in affairs:
                affair_type = affair.Geschaeftsart.text
                title = affair.Titel.text
                position = affair.parent

                # Skip if the affair is not a revision in law
                if re.search(r"vorlage", affair_type.lower()) and re.search(
                    r"gesetz", title.lower()
                ):
                    # Get the vorlage_nr
                    vorlage_nr = affair.VorlagenNr.text
                    # Get the last document and its last version
                    documents = position.find_all("Dokument")
                    try:
                        last_document = documents[0]
                        edoc_id = last_document.eDocument["ID"]
                        versions = last_document.find_all("Version")
                        last_version = versions[-1]["Nr"]
                    except Exception as e:
                        logging.error(f"Error getting edoc_id or last_version: {e}")
                        continue

                    # Construct the pdf url
                    pdf_url = f"https://parlzhcdws.cmicloud.ch/parlzh1/cdws/Files/{edoc_id}/{last_version}/pdf"

                    (
                        rr_date,
                        latest_step,
                        latest_step_date,
                    ) = get_date_and_latest_ablaufschritt(vorlage_nr)

                    # Append the data to the entries list
                    data = {
                        "Geschäftstitel": title,
                        "Geschäftsart": affair_type,
                        "PDF_URL": pdf_url,
                        "VorlagenNr": vorlage_nr,
                        "RR_Antrag": rr_date,
                        "latest_step": latest_step,
                        "latest_step_date": latest_step_date,
                    }
                    entries.append(data)

            # Append the data to the krversand_data list
            krversand_dict = {
                "Datum KR-Versand": krversand_date.format("DD.MM.YYYY"),
                "Vorlagen": entries,
            }
            krversand_data.append(krversand_dict)

        # Prepend the new data to the existing data
        for item in reversed(krversand_data):
            existing_data.insert(0, item)
        with open("krzh_dispatch_data.json", "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=4, ensure_ascii=False)

    try:
        response = requests.get(base_url_dispatch, params=params_dispatch)
        sleep(3)
        if response.status_code == 200:
            logging.info(f"API call successful. Parsing and downloading PDFs.")
            parse_and_download(response.content)
        else:
            logging.error(f"API call failed with status code {response.status_code}")
    except Exception as e:
        logging.error(f"Error during API call: {e}\n{traceback.format_exc()}")


if __name__ == "__main__":
    krzh_dispatch()
