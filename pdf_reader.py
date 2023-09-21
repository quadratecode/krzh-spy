import logging
import re
import requests
from time import sleep
import pdfplumber
import io
import json

# Setup logging
logger = logging.getLogger(__name__)

# Norms pattern
norms_pattern = r"§.*?\."


def check_totalrevision(original_pdf_data):
    for page_text in original_pdf_data.values():
        if "Es wird folgendes Gesetz erlassen" in page_text:
            return True
    return False


def remove_hyphens(text):
    text = re.sub(r"-\n", "", text)
    text = re.sub(r"\n", " ", text).strip()

    return text


def custom_sort(norm):
    # Extract the number from the norm
    match = re.search(r"\d+", norm)
    if match:
        return int(match.group())
    return 0


def extract_primary_norms(text_dict):
    primary_norms = []

    # Iterate over each item in the dictionary
    for key, text in text_dict.items():
        # Find all matches in the limited text
        matches = re.findall(norms_pattern, text[:20])

        # Strip the period after detection
        stripped_matches = [match.rstrip(".") for match in matches]

        primary_norms.extend(stripped_matches)

        # Remove duplicates from the combined list
        primary_norms = list(set(primary_norms))

        # Sort using our custom sorting function
        primary_norms = sorted(primary_norms, key=custom_sort)

    return primary_norms


def extract_secondary_norms(text_list):
    laws_and_norms = {}
    current_law_name = None

    for text in text_list:
        if "wird wie folgt geändert" in text:
            # This text defines the law name.
            law_name_candidate = text.split(" wird wie folgt geändert")[0].strip()
            # Remove the pattern "ROMAN NUMERAL SPACE Das SPACE"
            current_law_name = re.sub(r"^\s*[IVXLCDM]+\. Das ", "", law_name_candidate)

        else:
            # This might be the text with the norms.
            norms_list = re.findall(norms_pattern, text)
            # Strip the period after detection
            stripped_norms_list = [norm.rstrip(".") for norm in norms_list]

            if stripped_norms_list and current_law_name:
                # If norms were found, associate them with the current law.
                laws_and_norms[current_law_name] = stripped_norms_list

    return laws_and_norms


def split_page_on_gaps(pdf_page, gap_threshold):
    # Get the bounding box of the entire page
    x0, y0, x1, y1 = pdf_page.bbox

    # Get the lines on the page, sorted by their vertical position (top edge)
    lines = pdf_page.extract_text_lines()

    # Create a list to store the split pages
    split_pages = []

    # For each line, if the gap to the next line is larger than the threshold,
    # split the page at that line
    for i, line in enumerate(lines[:-1]):  # Exclude the last line
        next_line = lines[i + 1]
        gap = next_line["top"] - line["bottom"]

        if gap > gap_threshold:
            split_point = line["bottom"] + gap / 2  # Split in the middle of the gap
            split_page = pdf_page.crop((x0, y0, x1, split_point))
            split_pages.append(split_page)

            # The split point becomes the top of the next page
            y0 = split_point

    # Add the last page
    split_pages.append(pdf_page.crop((x0, y0, x1, y1)))

    return split_pages


def split_pdf_and_extract_text_portrait(response, gap_threshold):
    # Open the PDF file with pdfplumber
    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
        # Initialize an empty dictionary to hold the PDF text
        full_pdf_text = {}

        # For each page in the PDF
        for i, page in enumerate(pdf.pages):
            # Calculate the crop dimensions based on the page number
            if (i + 1) % 2 == 0:  # even pages
                x0 = page.bbox[0] + 85
                x1 = page.bbox[2]
            else:  # odd pages
                x0 = page.bbox[0]
                x1 = page.bbox[2] - 85

            # Crop the header and footer
            top = page.bbox[1] + (21.9 * 2.83465)
            bottom = page.bbox[3] - (22.6 * 2.83465)

            cropped_page = page.crop((x0, top, x1, bottom))

            # Split the cropped page at large gaps
            split_pages = split_page_on_gaps(cropped_page, gap_threshold)

            # Extract the text from each split page
            for j, split_page in enumerate(split_pages):
                # Use a tuple (i, j) as the key to keep track of the original page number
                # and the split page number
                split_page_raw_text = split_page.extract_text()
                full_pdf_text[(i, j)] = remove_hyphens(split_page_raw_text)

    # Define the flags
    found_roman_ii = False
    main_pdf_text = {}
    secondary_pdf_text = {}

    # Extract the text from each split page
    for (i, j), text in full_pdf_text.items():
        # If we haven't encountered the "II." yet, it's part of the main_pdf_text
        if re.search(r"(?<![IVXLCDM])II\.(?![IVXLCDM])", text) and not found_roman_ii:
            found_roman_ii = True

        if found_roman_ii:
            if "Bericht" == text.strip():
                break  # exit if the current page only contains the word "Bericht"
            secondary_pdf_text[(i, j)] = text
        else:
            main_pdf_text[(i, j)] = text

    return full_pdf_text, main_pdf_text, secondary_pdf_text


def pdf_reader():
    # Load JSON data
    with open("krzh_dispatch_data.json", "r", encoding="utf-8") as f:
        krversand_data = json.load(f)

    # Go through all records
    for record in krversand_data:
        # Go through all vorlagen in record
        for vorlage in record["Vorlagen"]:
            # Get PDF_URL
            pdf_url = vorlage["PDF_URL"]

            # Check if fields already exist, skip the current loop iteration if they do
            if all(
                key in vorlage
                for key in [
                    "original_pdf_data",
                    "primary_pdf_data",
                    "secondary_pdf_data",
                    "primary_norms",
                    "secondary_norms",
                ]
            ):
                continue

            try:
                # Download PDF content
                response = requests.get(pdf_url)
                response.raise_for_status()
                sleep(1)  # Be polite to the server

                # Open the PDF file with pdfplumber
                with pdfplumber.open(io.BytesIO(response.content)) as pdf:
                    # Check orientation of the first page
                    is_landscape = pdf.pages[0].width > pdf.pages[0].height

                    # Manual extraction if law is in new format
                    if is_landscape:
                        primary_norms = ["Neues Format: Manuelle Prüfung erforderlich."]
                        secondary_norms = ["Synopse: Manuelle Prüfung erforderlich."]
                    else:
                        (
                            original_pdf_data,
                            primary_pdf_data,
                            secondary_pdf_data,
                        ) = split_pdf_and_extract_text_portrait(response, 7.75)
                        primary_norms = extract_primary_norms(primary_pdf_data)
                        # Manual extraction of secondary norms if law is a totalrevision is true
                        if check_totalrevision(primary_pdf_data):
                            vorlage["Totalrevision"] = True
                            secondary_norms = [
                                "Totalrevision: Manuelle Prüfung gemäss Anhang erforderlich."
                            ]
                        else:
                            secondary_norms = extract_secondary_norms(
                                list(secondary_pdf_data.values())
                            )

                        # Note if no norms were found
                        if not primary_norms:
                            primary_norms = ["Keine Normen gefunden."]
                        if not secondary_norms:
                            secondary_norms = ["Keine Normen gefunden."]

                        # Get law as list
                        original_pdf_data = [
                            text for text in original_pdf_data.values()
                        ]
                        primary_pdf_data = [text for text in primary_pdf_data.values()]
                        secondary_pdf_data = [
                            text for text in secondary_pdf_data.values()
                        ]

                    # Add norms to vorlage in krversand_data
                    vorlage["original_pdf_data"] = original_pdf_data
                    vorlage["primary_pdf_data"] = primary_pdf_data
                    vorlage["secondary_pdf_data"] = secondary_pdf_data
                    vorlage["primary_norms"] = primary_norms
                    vorlage["secondary_norms"] = secondary_norms

            except requests.exceptions.RequestException as e:
                logging.error(f"Error downloading PDF from {pdf_url}: {e}")
            except Exception as e:
                logging.error(f"Error processing PDF from {pdf_url}: {e}")

    # Write data back to JSON
    with open("krzh_dispatch_data.json", "w", encoding="utf-8") as f:
        json.dump(krversand_data, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    pdf_reader()
