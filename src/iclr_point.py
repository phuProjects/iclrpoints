import gzip # For reading compressed dblp xml (.gz)
import xml.etree.ElementTree as ET # For parsing xml efficiently

# Paths
CSRANKINGS_PATH = "data/csrankings.csv"
AREA_PATH = "data/area.csv"
DBLP_PATH = "data/dblp.xml.gz"
OUTPUT_PATH = "data/iclr_points.csv"

def load_faculty_names(csrankings_path):
    """
    Read csrankings.csv and return a set of faculty names.
    We only need the names so we can match DBLP authors to 'known' faculty.
    """
    faculty_set = set()
    with open(csrankings_path, "r") as f:
        next(f)  # skip header
        for line in f:
            # csrankings.csv format: name,affiliation,homepage,scholarid
            parts = line.strip().split(",")
            if len(parts) < 1:
                continue
            name = parts[0]
            faculty_set.add(name)
    return faculty_set


def load_conference_to_area(area_path):
    """
    Read area.csv and build a dict: conference name -> area
    Example CSV header (your file): parent_area,area,abbrv,conference
    We only need the 'conference' and its 'area'.
    """
    conf_to_area = {}
    with open(area_path, "r") as f:
        next(f)  # skip header
        for line in f:
            parent_area, area, abbrv, conference = line.strip().split(",")
            conf_to_area[conference] = area
    return conf_to_area


def parse_dblp_and_count(dblp_path, conf_to_area, faculty_set):
    """
    Stream-parse DBLP and:
    - count publications per area (2019–2023)
    - collect which faculty appeared in each area
    Returns:
      area_to_pub:      {area: pub_count}
      area_to_faculty:  {area: set([faculty1, faculty2, ...])}
    """
    area_to_pub = {}
    area_to_faculty = {}

    with gzip.open(dblp_path, "rb") as dblp_file:
        # iterparse so we don't load the whole XML at once
        context = ET.iterparse(dblp_file, events=("end",))
        _, root = next(context)  # root <dblp>

        for event, elem in context:
            if elem.tag == "inproceedings":
                # year and venue
                year_text = elem.findtext("year")
                booktitle = elem.findtext("booktitle")

                if not year_text or not booktitle:
                    root.clear()
                    continue

                year = int(year_text)
                # We only care about 2019–2023
                if 2019 <= year <= 2023:
                    # find which area this booktitle belongs to
                    area = None
                    for conf, conf_area in conf_to_area.items():
                        if conf.lower() in booktitle.lower():
                            area = conf_area
                            break

                    if area:
                        # count publication
                        area_to_pub[area] = area_to_pub.get(area, 0) + 1

                        # collect faculty authors
                        for author_elem in elem.findall("author"):
                            author_name = author_elem.text
                            if author_name and author_name in faculty_set:
                                area_to_faculty.setdefault(area, set()).add(author_name)

            # free memory
            root.clear()

    return area_to_pub, area_to_faculty


def compute_fractional_faculty(area_to_faculty):
    """
    Some faculty publish in multiple areas. We split their '1' across all
    areas they appear in. So if a faculty appears in 2 areas, each area gets 0.5.
    Returns: area_to_fraction_fact {area: fractional_faculty_count}
    """
    # Build faculty -> areas
    faculty_to_areas = {}
    for area, facs in area_to_faculty.items():
        for fac in facs:
            faculty_to_areas.setdefault(fac, set()).add(area)

    area_to_fraction_fact = {}
    for faculty, areas in faculty_to_areas.items():
        share = 1 / len(areas)  # split evenly
        for area in areas:
            area_to_fraction_fact[area] = area_to_fraction_fact.get(area, 0) + share

    return area_to_fraction_fact


def write_iclr_points_csv(output_path, area_to_pub, area_to_fraction_fact):
    """
    Compute:
      faculty_per_pub = frac_faculty / pubs
      baseline = ML_faculty / ML_pubs
      iclr_points = faculty_per_pub / baseline
    and write to CSV.
    """
    # we assume "Machine learning" exists in the data
    ml_faculty = area_to_fraction_fact.get("Machine learning", 0)
    ml_pubs = area_to_pub.get("Machine learning", 0)
    if ml_pubs == 0:
        raise ValueError("Machine learning baseline not found or has 0 pubs")

    baseline = ml_faculty / ml_pubs

    with open(output_path, "w") as f:
        f.write("area,faculty_count,publication_count,faculty_per_pub,iclr_points\n")
        for area in sorted(area_to_pub.keys()):
            pubs = area_to_pub[area]
            frac_fac = area_to_fraction_fact.get(area, 0)
            faculty_per_pub = frac_fac / pubs if pubs else 0
            iclr_points = faculty_per_pub / baseline if baseline else 0

            row = f"{area},{frac_fac:.2f},{pubs},{faculty_per_pub:.2f},{iclr_points:.2f}\n"
            f.write(row)


def main():
    # 1) load input data
    faculty_set = load_faculty_names(CSRANKINGS_PATH)
    conf_to_area = load_conference_to_area(AREA_PATH)

    # 2) parse DBLP and collect counts
    area_to_pub, area_to_faculty = parse_dblp_and_count(
        DBLP_PATH, conf_to_area, faculty_set
    )

    # 3) fractionalize faculty across areas
    area_to_fraction_fact = compute_fractional_faculty(area_to_faculty)

    # 4) compute + write final csv
    write_iclr_points_csv(OUTPUT_PATH, area_to_pub, area_to_fraction_fact)

    print("ICLR points written to", OUTPUT_PATH)


if __name__ == "__main__":
    main()
