import logging

from krzh_dispatch_scraper import krzh_dispatch
from krzh_initiatives_scraper import krzh_initiatives
from pdf_reader import pdf_reader
from generate_page import generate_page

logging.basicConfig(
    filename="log.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)


def main():
    try:
        logging.info("Starting scraping Ratsversand")
        krzh_dispatch()
        ###
        logging.info("Starting scraping Initiativen")
        krzh_initiatives()
        ###
        logging.info("Starting reading PDFs")
        pdf_reader()
        ###
        logging.info("Starting generating page for KRZH - Vorlagen Ratsversand")
        generate_page(
            "krzh_dispatch_data.json", "KRZH - Vorlagen Ratsversand", "krzh_dispatch"
        )
        logging.info("Page for KRZH - Vorlagen Ratsversand generated successfully")
        ###
        logging.info("Starting generating page for KRZH - Initiativen")
        generate_page(
            "krzh_initiatives_data.json", "KRZH - Initiativen", "krzh_initiatives"
        )
        logging.info("Page for KRZH - Initiativen generated successfully")
    except Exception as e:
        logging.error(f"Error during main(): {e}")


if __name__ == "__main__":
    main()
