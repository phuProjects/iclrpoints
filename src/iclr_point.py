import gzip
import xml.etree.ElementTree as ET

def parse():
    inst_map = {}
    total_us_univs = 0
    total_num_fact = 0

    with open ("data/raw/country-info.csv", "r") as f, open("data/raw/csrankings.csv", "r") as f2:
        next(f)
        next(f2)
        #non-US countries
        for line in f:
            institution,region,countryabbrv = line.strip().split(",")
            if region == "canada":
                inst_map[institution] = ("north america", countryabbrv)
            else:
                inst_map[institution] = (region, countryabbrv)
            total_us_univs += 1
        #include US countries
        for line in f2:
            name,affiliation,homepage,scholarid = line.strip().split(",")

            if affiliation not in inst_map:
                inst_map[affiliation] = ("north america", "us")
                total_us_univs += 1
            total_num_fact += 1

    print("Total number of universities:", total_us_univs)
    print("Total number of factulties:", total_num_fact)

    #Write to faculties.csv combining faculty info with region & country
    faculty_set = set()
    with open("data/raw/csrankings.csv") as readfile, open("data/processed/faculties.csv", "w") as writefile:
        next(readfile)
        writefile.write("name,institution,homepage,scholarid,region,country\n")

        for line in readfile:
            name,affiliation,homepage,scholarid = line.strip().split(",")

            faculty_set.add(name)

            if affiliation in inst_map:
                region, country = inst_map[affiliation]
            else:
                region, country = "Unknown", "Unknown"

            row = f"{name},{affiliation},{homepage},{scholarid},{region},{country}\n"
            writefile.write(row)
    print("Written")

    #step 2: map conference to area
    conf_to_area = {}
    with open("data/processed/area.csv", "r") as area_file:
        next(area_file)
        for line in area_file:
            parent_area,area,abbrv,conference = line.strip().split(",")
            conf_to_area[conference] = area
    # count = 1
    # for key,value in conf_to_area.items():
    #     print(key, value, count)
    #     count += 1
    #Step 3: Parse DBLP to count publications per area
    area_to_pub = {}
    area_to_faculty = {}
    
    with gzip.open("data/raw/dblp.xml.gz", "rb") as dblp_file:
        #Stream-parse instead of loading the whole thing
        context = ET.iterparse(dblp_file, events=("end",))
        #Get the root elem <dblp>
        _, root = next(context)
        d = set()
        a = set()
        for event, elem in context:
            if elem.tag == "inproceedings":
                year = int(elem.findtext("year"))
                booktitle = elem.findtext("booktitle")
                
                # booktitle = booktitle.split('(')[0].strip()  # removes things like "(1)" or "(Poster)"
                # booktitle = booktitle.replace("Conference", "").replace("Symposium", "").strip()
                # booktitle = booktitle.replace("USENIX", "usenix Security").replace("ieee symposium on security and privacy", "ieee s&p")

                #Year range 2019 - 2023
                if 2019 <= year <= 2023:
                    # a.add(booktitle)
                    area = None
                    for conf,conf_area in conf_to_area.items():
                        if conf.lower() in booktitle.lower():
                            area = conf_area
                    # d.add(area)
                    if area:
                        area_to_pub[area] = area_to_pub.get(area, 0) + 1
                        #All authors of pub: student, faculty, 
                        authors = [a.text for a in elem.findall("author") if a.text]
                        #Include only faculties
                        for author in authors:
                            if author in faculty_set:
                                if area not in area_to_faculty:
                                    area_to_faculty[area] = set()
                                area_to_faculty[area].add(author)
            root.clear()
        #print(d)
        #print(a)
    # Step 4: fractional faculty counting
    area_to_fraction_fact = {}

    # Build faculty → areas mapping
    faculty_to_areas = {}
    for area, faculties in area_to_faculty.items():
        for faculty in faculties:
            if faculty not in faculty_to_areas:
                faculty_to_areas[faculty] = set()
            faculty_to_areas[faculty].add(area)

    # Apply fractional distribution
    for faculty, areas in faculty_to_areas.items():
        if len(areas) == 0:
            continue
        share = 1 / len(areas)
        for area in areas:
            area_to_fraction_fact[area] = area_to_fraction_fact.get(area, 0) + share

    #Step 5: Print results
    with open("data/processed/iclr_points.csv", "w") as writefile:
        writefile.write("area,publication_count,factulty_count,faculty_per_pub,iclr_points\n") #header

        print("Publications per area (2019–2023):")

        for area in sorted(area_to_pub.keys()):
            pubs = area_to_pub[area]
            faculty_count = len(area_to_faculty.get(area,[]))
            faculty_frac = area_to_fraction_fact.get(area, 0)
            faculty_per_pub = faculty_frac / pubs
            baseline = area_to_fraction_fact.get("Machine learning", 0) / area_to_pub['Machine learning']
            iclr_points = faculty_per_pub / baseline

            #print(f"{area}: {pubs} publications, faculty count {faculty_frac:.2f}")
            row = (f"{area},{pubs},{faculty_frac:.2f},{faculty_per_pub:.2f},{iclr_points:.2f}\n")
            writefile.write(row)

parse()


