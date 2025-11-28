import gzip # For reading compressed dblp xml (.gz)
import xml.etree.ElementTree as ET # For parsing xml efficiently
import json

# Paths
CSRANKINGS_PATH = "data/csrankings_march.csv"
AREA_PATH = "data/area.csv"
DBLP_PATH = "data/dblp.xml.gz"

def load_faculty_names(csrankings_path):
    """
    Read csrankings.csv and return a set of faculty names.
    We only need the names so we can match DBLP authors to 'known' faculty.
    """
    faculty_set = set()
    count = 0
    with open(csrankings_path, "r") as f:
        next(f)  # skip header
        for line in f:
            # csrankings.csv format: name,affiliation,homepage,scholarid
            parts = line.strip().split(",")
            if len(parts) < 1:
                continue
            name = parts[0]
            faculty_set.add(name)
            count += 1
    print("Total number of faculties: ", count)
    return faculty_set

def load_conference_to_area(area_path):
    """
    Read area.csv and build a dict: 
        conference name -> area
        area -> parent_area
    area.csv: parent_area,area,abbrv,conference
    """
    conf_to_area = {}
    area_to_parent = {}
    with open(area_path, "r") as f:
        next(f)  # skip header
        for line in f:
            parent_area, area, abbrv, conference = line.strip().split(",")
            conf_to_area[conference] = area
            area_to_parent[area] = parent_area
    return conf_to_area, area_to_parent

def parse_dblp_and_count(dblp_path, conf_to_area, faculty_set, start_year, end_year):
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

                # We only care about start-end year
                if int(start_year) <= year <= int(end_year):
                    # find which area this booktitle belongs to
                    area = None
                    for conf, conf_area in conf_to_area.items():
                        if conf in booktitle:
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

def compute_iclr_points_year_range(start_year, end_year, faculty_set, conf_to_area, area_to_parent):
    area_to_pub, area_to_faculty = parse_dblp_and_count(DBLP_PATH, conf_to_area, faculty_set, start_year, end_year)

    area_to_fraction_fact = compute_fractional_faculty(area_to_faculty)

    #baseline
    ml_fact = area_to_fraction_fact.get("Machine learning")
    ml_pubs = area_to_pub.get("Machine learning")
    baseline = ml_fact / ml_pubs

    rows = []
    for area in sorted(area_to_pub.keys()):
        pubs = area_to_pub[area]
        frac_fac = area_to_fraction_fact.get(area, 0)
        factulty_per_pub = frac_fac / pubs
        iclr_points = factulty_per_pub / baseline

        parent_area = area_to_parent.get(area)

        rows.append({
            "area": area,
            "parent": parent_area,
            "faculty_count": round(frac_fac,2),
            "publication_count": pubs,
            "faculty_per_pub": round(factulty_per_pub,2),
            "iclr_points": round(iclr_points,2)
        })

    return rows

def iclr_json(start_year, end_year):

    faculty_set = load_faculty_names(CSRANKINGS_PATH)
    conf_to_area, area_to_parent = load_conference_to_area(AREA_PATH)

    rows = compute_iclr_points_year_range(
        start_year, end_year,
        faculty_set,
        conf_to_area,
        area_to_parent
    )

    return json.dumps(rows)

def main():
    start_year = 2019
    end_year = 2023
    json_str = iclr_json(start_year, end_year)

    output_path = "data/iclr_points.json"
    with open(output_path, "w") as f:
        f.write(json_str)
    
if __name__ == "__main__":
    main()
