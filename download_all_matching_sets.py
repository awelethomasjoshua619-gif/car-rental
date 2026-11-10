import urllib.request
import urllib.parse
import json
import time
import os
import sqlite3

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

CAR_SETS = {
    1: { # BMW M4 Competition Coupe
        'front': 'File:BMW M4 (G82) IMG 4053.jpg',
        'side': 'File:BMW M4 (G82) IMG 4054.jpg',
        'rear': 'File:BMW M4 (G82) IMG 4183.jpg',
        'interior': 'File:BMW G82 M4 Competition Extended Merino Leather Kyalami Orange Black (17).jpg'
    },
    2: { # Mercedes-Benz S-Class
        'front': 'File:Mercedes-Benz W223 IMG 3927.jpg',
        'side': 'File:Mercedes-Benz W223 IMG 3951.jpg',
        'rear': 'File:Mercedes-Benz W223 IMG 3971.jpg',
        'interior': 'File:Mercedes-Benz W223 IMG 3949.jpg'
    },
    3: { # Tesla Model 3 Performance
        'front': 'File:2019 Tesla Model 3 Performance AWD Front.jpg',
        'side': 'File:2019 Tesla Model 3 Performance AWD.jpg',
        'rear': 'File:2019 Tesla Model 3 Performance AWD Rear.jpg',
        'interior': 'File:Tesla Model 3 interior.jpg'
    },
    4: { # Audi RS6 Avant Quattro
        'front': 'File:2019 Audi RS6 Avant 4.0 Front.jpg',
        'side': 'File:2019 Audi RS6 Avant 4.0 Front End.jpg',
        'rear': 'File:2019 Audi RS6 Avant 4.0 Rear.jpg',
        'interior': 'File:2019 Audi RS6 Avant 4.0 Interior.jpg'
    },
    5: { # Porsche 911 Carrera GTS / S
        'front': 'File:Porsche 992 Carrera S coupe IMG 5832.jpg',
        'side': 'File:Porsche 992 Carrera S coupe IMG 5843.jpg',
        'rear': 'File:Porsche 992 Carrera S coupe IMG 5847.jpg',
        'interior': 'File:Porsche 992 Carrera S coupe IMG 5838.jpg'
    },
    6: { # Toyota RAV4 Hybrid Limited
        'front': 'File:2019 Toyota RAV4 Excel HEV CVT 2.5 Front.jpg',
        'side': 'File:2019 Toyota RAV4 Excel Hybrid CVT 2.5 Front.jpg',
        'rear': 'File:2019 Toyota RAV4 Excel HEV CVT 2.5 Rear.jpg',
        'interior': 'File:2019 Toyota RAV4 Interior.jpg'
    },
    7: { # Ford Mustang GT 5.0 V8
        'front': 'File:2019 Ford Mustang GT 5.0 facelift Front.jpg',
        'side': 'File:2019 Ford Mustang GT 5.0 facelift Side.jpg',
        'rear': 'File:2019 Ford Mustang GT 5.0 facelift Rear.jpg',
        'interior': 'File:2018 Ford Mustang GT V8 5.0 facelift Interior.jpg'
    },
    8: { # Hyundai Ioniq 5 Electric Crossover
        'front': 'File:2021 Hyundai Ioniq 5 Premium EV Front.jpg',
        'side': 'File:2021 Hyundai Ioniq 5 Premium EV (1).jpg',
        'rear': 'File:2021 Hyundai Ioniq 5 Premium EV Rear.jpg',
        'interior': 'File:2021 Hyundai Ioniq 5 Premium EV (3).jpg'
    }
}

def resolve_commons_thumbnail(title):
    url = f"https://commons.wikimedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}&prop=imageinfo&iiprop=url&iiurlwidth=1280&format=json"
    for attempt in range(4):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=12) as r:
                d = json.loads(r.read().decode())
                for pid, p in d.get('query', {}).get('pages', {}).items():
                    ii = p.get('imageinfo', [{}])[0]
                    thumb = ii.get('thumburl') or ii.get('url')
                    return thumb
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"  Rate limited (429), waiting 6s before retry #{attempt+1}...")
                time.sleep(6)
            else:
                print(f"  HTTP error {e.code} for {title}")
                return None
        except Exception as e:
            print(f"  Error {e} for {title}")
            time.sleep(2)
    return None

def download_file(url, target_path):
    for attempt in range(3):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = r.read()
                with open(target_path, 'wb') as f:
                    f.write(data)
                return len(data)
        except Exception as e:
            print(f"  Download retry #{attempt+1} after error: {e}")
            time.sleep(3)
    return 0

def main():
    dest_dir = os.path.join('static', 'images', 'cars')
    os.makedirs(dest_dir, exist_ok=True)
    
    db_updates = {}

    for car_id, angles in CAR_SETS.items():
        print(f"\n================ Processing Car ID {car_id} ================")
        db_updates[car_id] = {}
        for angle_name, wiki_title in angles.items():
            filename = f"car_{car_id}_{angle_name}.jpg"
            target_path = os.path.join(dest_dir, filename)
            local_url = f"/static/images/cars/{filename}"
            
            if os.path.exists(target_path) and os.path.getsize(target_path) > 10000:
                print(f"[{angle_name.upper()}] Already downloaded: {target_path} ({os.path.getsize(target_path):,} bytes)")
                db_updates[car_id][angle_name] = local_url
                continue

            print(f"[{angle_name.upper()}] Resolving {wiki_title}...")
            thumb_url = resolve_commons_thumbnail(wiki_title)
            if not thumb_url:
                print(f"  FAILED to resolve {wiki_title}")
                continue
            
            print(f"  Downloading from: {thumb_url[:80]}...")
            try:
                size = download_file(thumb_url, target_path)
                if size > 0:
                    print(f"  SUCCESS: Saved {target_path} ({size:,} bytes)")
                    db_updates[car_id][angle_name] = local_url
            except Exception as e:
                print(f"  ERROR downloading {wiki_title}: {e}")
            
            time.sleep(2.0)

    print("\nUpdating SQLite database fastcars.db with local image paths...")
    conn = sqlite3.connect('fastcars.db')
    cur = conn.cursor()
    for car_id, urls in db_updates.items():
        front = urls.get('front')
        side = urls.get('side')
        rear = urls.get('rear')
        interior = urls.get('interior')
        
        cur.execute("""
            UPDATE vehicles
            SET image_url = coalesce(?, image_url),
                image_side = coalesce(?, image_side),
                image_rear = coalesce(?, image_rear),
                image_interior = coalesce(?, image_interior)
            WHERE id = ?
        """, (front, side, rear, interior, car_id))
        print(f"Updated car {car_id} in database -> {urls}")
    
    conn.commit()
    conn.close()
    print("Database update complete!")

if __name__ == '__main__':
    main()
