import json
import arrow
import logging

# Setup logging
logger = logging.getLogger(__name__)


def setup_html_string(title):
    """Set up the initial HTML structure and styles."""
    return f"""
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8">
            <link rel="stylesheet" type="text/css" href="styles.css">
            <title>{title}</title>
        </head>
        <body>
            <div class="container">
                <h1>{title}</h1>
                <div class="updated">Last updated: {arrow.now().format("DD.MM.YYYY HH:mm")}</div>
    """


def format_secondary_norms(secondary_norms):
    # If it is a list, return the contents of the list
    if isinstance(secondary_norms, list):
        return ", ".join(secondary_norms)

    formatted_norms = []
    for law, norms in secondary_norms.items():
        if not isinstance(norms, list):  # Ensure the value for each law is a list
            continue
        # Remove all § signs
        norms_without_symbols = ", ".join([norm.replace("§", "") for norm in norms])
        formatted_norms.append(f"{law}: {norms_without_symbols}")

    return "<br></br>".join(formatted_norms)


def process_krzh_dispatch_data(data):
    """Process data specific to krzh_dispatch_data.json."""
    one_year_ago = arrow.utcnow().shift(years=-1)
    html_string = ""

    for item in data:
        datum = item.get("Datum KR-Versand", "")
        published = arrow.get(datum, "DD.MM.YYYY")

        if published < one_year_ago:
            continue

        html_string += f"<h3>KR-Versand vom {datum}</h3>"
        vorlagen = item.get("Vorlagen", [])

        if vorlagen:
            for vorlage in vorlagen:
                primary_norms = ", ".join(
                    vorlage.get("primary_norms", ["N/A"])
                ).replace("§", "")
                secondary_norms = format_secondary_norms(
                    vorlage.get("secondary_norms", {})
                )

                html_string += f"""
                <table>
                    <tr><th>Geschäftstitel</th><td>{vorlage.get("Geschäftstitel", "N/A")}</td></tr>
                    <tr><th>PDF URL</th><td><a href="{vorlage.get("PDF_URL", "#")}">{vorlage.get("PDF_URL", "N/A")}</a></td></tr>
                    <tr><th>Datum Antrag RR</th><td>{vorlage.get("RR_Antrag", "N/A")}</td></tr>
                    <tr><th>Letzter Verfahrensschritt</th><td>{vorlage.get("latest_step", "N/A")} am {vorlage.get("latest_step_date", "N/A")}</td></tr>
                    <tr><th>Geänderte § Haupterlass</th><td>{primary_norms}</td></tr>
                    <tr><th>Geänderte § Nebenerlasse</th><td>{secondary_norms}</td></tr>
                </table>
                """
        else:
            html_string += "<p>Keine Vorlagen gefunden</p>"

    return html_string


def process_krzh_initiatives(data):
    one_year_ago = arrow.utcnow().shift(years=-1)
    html_string = ""

    for item in data:
        decision_date = item.get("decision_date", "")
        published = arrow.get(decision_date, "YYYYMMDD")

        if published < one_year_ago:
            continue

        html_string += f"<h3>{item.get('krnr', 'N/A')}</h3>"
        html_string += "<table>"

        for key, value in item.items():
            if key != "krnr":
                # Base field_name and formatted_value on the key
                field_name = key
                formatted_value = value

                # Adjust field_name and formatted_value for specific keys
                if key == "vorlage_type":
                    field_name = "Art der Vorlage"
                elif key == "vorlage_title":
                    field_name = "Betreff"
                elif key == "decision":
                    field_name = "Entscheid"
                elif key == "decision_abstract":
                    field_name = "Zusammenfassung des Entscheids"
                elif key == "decision_date":
                    field_name = "Datum Entscheid"
                    formatted_value = arrow.get(value, "YYYYMMDD").format("DD.MM.YYYY")
                elif key == "pdf_url":
                    field_name = "PDF URL"
                    formatted_value = f'<a href="{value}">{value}</a>'

                # Add this row to the HTML string
                html_string += (
                    f"<tr><th>{field_name}</th><td>{formatted_value}</td></tr>"
                )

        html_string += "</table>"

    return html_string


def generate_page(filename, title, htmlname):
    """Main function to create the HTML files from JSON data."""
    html_string = setup_html_string(title)

    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        if filename == "krzh_dispatch_data.json":
            html_string += process_krzh_dispatch_data(data)
        elif filename == "krzh_initiatives_data.json":
            html_string += process_krzh_initiatives(data)

        html_string += "</body></html>"

        with open(f"{htmlname}.html", "w", encoding="utf-8") as f:
            f.write(html_string)

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error processing {filename}: {e}")


if __name__ == "__main__":
    generate_page(
        "krzh_dispatch_data.json", "KRZH - Vorlagen Ratsversand", "krzh_dispatch"
    )
    generate_page(
        "krzh_initiatives_data.json",
        "KRZH - Initiativen",
        "krzh_initiatives",
    )
