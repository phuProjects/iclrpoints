import gzip
import xml.etree.ElementTree as ET
import json

CSRANKINGS_PATH = "data/csrankings_march.csv"
AREA_PATH = "data/area.csv"
DBLP_PATH = "data/dblp.xml.gz"

def load_faculty_names(csrankings_path):
    faculty_set = set()
    count = 0
    with open(csrankings_path, "r") as f:
        next(f)
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 1:
                continue
            name = parts[0]
            faculty_set.add(name)
            count += 1
    print("Total number of faculties: ", count)
    return faculty_set

def load_conference_to_area(area_path):
    conf_to_area = {}
    area_to_parent = {}
    with open(area_path, "r") as f:
        next(f)
        for line in f:
            parent_area, area, abbrv, conference = line.strip().split(",")
            conf_to_area[conference] = area
            area_to_parent[area] = parent_area
    return conf_to_area, area_to_parent

def parse_dblp_and_count(dblp_path, conf_to_area, faculty_set, start_year, end_year):
    area_to_pub = {}
    area_to_faculty = {}

    with gzip.open(dblp_path, "rb") as dblp_file:
        context = ET.iterparse(dblp_file, events=("end",))
        _, root = next(context)

        for event, elem in context:
            if elem.tag == "inproceedings":
                year_text = elem.findtext("year")
                booktitle = elem.findtext("booktitle")
                
                if not year_text or not booktitle:
                    root.clear()
                    continue

                year = int(year_text)

                if int(start_year) <= year <= int(end_year):
                    area = None
                    for conf, conf_area in conf_to_area.items():
                        if conf in booktitle:
                            area = conf_area
                            break

                    if area:
                        area_to_pub[area] = area_to_pub.get(area, 0) + 1

                        for author_elem in elem.findall("author"):
                            author_name = author_elem.text
                            if author_name and author_name in faculty_set:
                                area_to_faculty.setdefault(area, set()).add(author_name)   
            root.clear()

    return area_to_pub, area_to_faculty

def compute_fractional_faculty(area_to_faculty):
    faculty_to_areas = {}
    for area, facs in area_to_faculty.items():
        for fac in facs:
            faculty_to_areas.setdefault(fac, set()).add(area)

    area_to_fraction_fact = {}
    for faculty, areas in faculty_to_areas.items():
        share = 1 / len(areas)
        for area in areas:
            area_to_fraction_fact[area] = area_to_fraction_fact.get(area, 0) + share

    return area_to_fraction_fact

def compute_iclr_points_year_range(start_year, end_year, faculty_set, conf_to_area, area_to_parent):
    area_to_pub, area_to_faculty = parse_dblp_and_count(DBLP_PATH, conf_to_area, faculty_set, start_year, end_year)

    area_to_fraction_fact = compute_fractional_faculty(area_to_faculty)

    ml_fact = area_to_fraction_fact.get("Machine learning")
    ml_pubs = area_to_pub.get("Machine learning")
    baseline = ml_fact / ml_pubs

    rows = []
    for area in sorted(area_to_pub.keys()):
        pubs = area_to_pub[area]
        frac_fac = area_to_fraction_fact.get(area, 0)
        faculty_per_pub = frac_fac / pubs
        iclr_points = faculty_per_pub / baseline

        parent_area = area_to_parent.get(area)

        rows.append({
            "area": area,
            "parent": parent_area,
            "faculty_count": round(frac_fac,2),
            "publication_count": pubs,
            "faculty_per_pub": round(faculty_per_pub,2),
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
