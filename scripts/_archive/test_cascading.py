import json
import urllib.request

def test():
    res = urllib.request.urlopen("http://127.0.0.1:8000/api/v1/facilities")
    facilities = json.loads(res.read())["data"]
    print(f"Total facilities: {len(facilities)}")

    for f in facilities[:4]:
        fid = f["id"]
        fname = f["name"]
        f_res = urllib.request.urlopen(f"http://127.0.0.1:8000/api/v1/specialties?facility_id={fid}")
        specs = json.loads(f_res.read())["data"]
        print(f"Facility: {fname} -> {len(specs)} specialties")

    # Test reverse: specialty -> facilities
    s_res = urllib.request.urlopen("http://127.0.0.1:8000/api/v1/specialties?limit=5")
    specialties = json.loads(s_res.read())["data"]
    for s in specialties:
        sid = s["id"]
        sname = s["name"]
        sf_res = urllib.request.urlopen(f"http://127.0.0.1:8000/api/v1/facilities?specialty_id={sid}")
        facs = json.loads(sf_res.read())["data"]
        print(f"Specialty: {sname} -> {len(facs)} facilities")

if __name__ == "__main__":
    test()
