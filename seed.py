import os
import json
import uuid
import random
from decimal import Decimal
from datetime import datetime, timedelta, timezone
import boto3
from botocore.exceptions import ClientError

AWS_REGION = "ap-south-1"
PREFIX = "travelgo"

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
dynamodb_client = boto3.client("dynamodb", region_name=AWS_REGION)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def _now():
    return datetime.now(timezone.utc)


CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai",
    "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
    "Kochi", "Chandigarh", "Bhopal", "Indore", "Coimbatore",
    "Nagpur", "Visakhapatnam", "Patna", "Vadodara", "Goa",
    "Thiruvananthapuram", "Mangalore", "Madurai", "Varanasi", "Amritsar",
    "Ranchi", "Surat", "Mysore", "Jodhpur", "Udaipur",
    "Dehradun", "Guwahati", "Bhubaneswar", "Raipur", "Tiruchirappalli",
    "Aurangabad", "Nashik", "Rajkot", "Hubli", "Belgaum",
]

AIRLINES = [
    "Air India", "IndiGo", "SpiceJet", "Vistara", "Go First",
    "AirAsia India", "Akasa Air", "Star Air", "Alliance Air",
]

HOTEL_CHAINS = [
    "Taj", "Oberoi", "ITC", "Leela", "Marriott",
    "Hyatt", "Radisson", "Novotel", "Lemon Tree", "OYO Premium",
    "Trident", "JW Marriott", "Vivanta", "Holiday Inn", "Crowne Plaza",
    "Sarovar", "Fortune", "Park", "Clarks", "WelcomHotel",
]

HOTEL_SUFFIXES = [
    "Grand", "Palace", "Residency", "Suites", "Plaza",
    "Inn", "Resort", "Continental", "Regency", "Royal",
]

AMENITIES_POOL = [
    "WiFi", "Pool", "Gym", "Spa", "Restaurant",
    "Bar", "Parking", "Room Service", "Laundry", "Airport Shuttle",
    "Business Center", "Concierge", "AC", "TV", "Mini Bar",
]

TRAIN_NAMES = [
    "Rajdhani Express", "Shatabdi Express", "Duronto Express",
    "Garib Rath", "Jan Shatabdi", "Humsafar Express",
    "Tejas Express", "Vande Bharat Express", "Gatimaan Express",
    "Sampark Kranti", "Superfast Express", "Mail Express",
    "Double Decker Express", "AC Express", "Antyodaya Express",
    "Mahamana Express", "Kavi Guru Express", "Vivek Express",
]

BUS_OPERATORS = [
    "KSRTC", "APSRTC", "MSRTC", "GSRTC", "UPSRTC",
    "RSRTC", "HRTC", "PEPSU", "TSRTC", "BMTC",
    "VRL Travels", "SRS Travels", "Neeta Travels", "Parveen Travels",
    "Orange Travels", "KPN Travels", "Jabbar Travels", "Paulo Travels",
    "Hans Travels", "Kaveri Travels",
]

BUS_TYPES = [
    "Volvo AC Sleeper", "AC Seater", "Non-AC Sleeper",
    "Non-AC Seater", "Volvo Multi-Axle", "Mercedes AC",
    "Semi-Sleeper AC", "Luxury AC", "Super Deluxe",
]


def _random_dates(n, start_offset_days=1, end_offset_days=30):
    base = datetime.now()
    dates = []
    for _ in range(n):
        delta = random.randint(start_offset_days, end_offset_days)
        d = base + timedelta(days=delta)
        dates.append(d.strftime("%Y-%m-%d"))
    return dates


def _random_time():
    h = random.randint(0, 23)
    m = random.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    return f"{h:02d}:{m:02d}"


def _add_hours(time_str, hours, minutes=0):
    h, m = map(int, time_str.split(":"))
    total = h * 60 + m + hours * 60 + minutes
    total %= 1440
    return f"{total // 60:02d}:{total % 60:02d}"


def _duration_str(hours, minutes=0):
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def _city_pairs(cities, n):
    pairs = []
    for _ in range(n):
        src, dst = random.sample(cities, 2)
        pairs.append((src, dst))
    return pairs


def _write(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  ✅  {filename}: {len(data)} records")


def _load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_flights(count=50):
    records = []
    pairs = _city_pairs(CITIES, count)
    dates = _random_dates(count)
    for i, ((src, dst), date) in enumerate(zip(pairs, dates), start=1):
        airline = random.choice(AIRLINES)
        code = airline[:2].upper() + "-" + str(random.randint(100, 9999))
        dep = _random_time()
        dur_h = random.randint(1, 4)
        dur_m = random.choice([0, 10, 15, 20, 25, 30, 35, 40, 45, 50])
        arr = _add_hours(dep, dur_h, dur_m)
        records.append({
            "name": f"{airline} {code}",
            "airline": airline,
            "source": src,
            "destination": dst,
            "date": date,
            "departure": dep,
            "arrival": arr,
            "duration": _duration_str(dur_h, dur_m),
            "price": round(random.uniform(2500, 18000), 2),
            "availability": random.randint(5, 180),
        })
    _write("flights.json", records)
    return records


def generate_hotels(count=50):
    records = []
    dates = _random_dates(count, 1, 120)
    for i in range(count):
        city = random.choice(CITIES)
        chain = random.choice(HOTEL_CHAINS)
        suffix = random.choice(HOTEL_SUFFIXES)
        name = f"{chain} {suffix} {city}"
        checkin = dates[i]
        checkout_dt = datetime.strptime(checkin, "%Y-%m-%d") + timedelta(
            days=random.randint(1, 7)
        )
        checkout = checkout_dt.strftime("%Y-%m-%d")
        num_amenities = random.randint(3, 8)
        amenities = ", ".join(random.sample(AMENITIES_POOL, num_amenities))
        records.append({
            "name": name,
            "destination": city,
            "checkin": checkin,
            "checkout": checkout,
            "price": round(random.uniform(1500, 25000), 2),
            "rating": round(random.uniform(3.0, 5.0), 1),
            "rooms": random.randint(1, 50),
            "amenities": amenities,
            "availability": random.randint(1, 50),
        })
    _write("hotels.json", records)
    return records


def generate_trains(count=50):
    records = []
    pairs = _city_pairs(CITIES, count)
    dates = _random_dates(count)
    for i, ((src, dst), date) in enumerate(zip(pairs, dates), start=1):
        train_name = random.choice(TRAIN_NAMES)
        number = random.randint(10001, 99999)
        dep = _random_time()
        dur_h = random.randint(2, 36)
        dur_m = random.choice([0, 10, 15, 20, 30, 45])
        arr = _add_hours(dep, dur_h, dur_m)
        records.append({
            "name": f"{number} {train_name}",
            "operator": "Indian Railways",
            "source": src,
            "destination": dst,
            "date": date,
            "departure": dep,
            "arrival": arr,
            "duration": _duration_str(dur_h, dur_m),
            "price": round(random.uniform(250, 5500), 2),
            "availability": random.randint(5, 500),
        })
    _write("trains.json", records)
    return records


def generate_buses(count=50):
    records = []
    pairs = _city_pairs(CITIES, count)
    dates = _random_dates(count)
    for i, ((src, dst), date) in enumerate(zip(pairs, dates), start=1):
        operator = random.choice(BUS_OPERATORS)
        bus_type = random.choice(BUS_TYPES)
        dep = _random_time()
        dur_h = random.randint(2, 18)
        dur_m = random.choice([0, 10, 15, 20, 30, 45])
        arr = _add_hours(dep, dur_h, dur_m)
        records.append({
            "name": f"{operator} — {bus_type}",
            "operator": operator,
            "source": src,
            "destination": dst,
            "date": date,
            "departure": dep,
            "arrival": arr,
            "duration": _duration_str(dur_h, dur_m),
            "price": round(random.uniform(300, 3500), 2),
            "availability": random.randint(5, 45),
        })
    _write("buses.json", records)
    return records


TABLE_DEFS = {
    f"{PREFIX}-users": {
        "KeySchema": [{"AttributeName": "_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "_id", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"},
            {"AttributeName": "username", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "email-index",
                "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "username-index",
                "KeySchema": [{"AttributeName": "username", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
    },
    f"{PREFIX}-flights": {
        "KeySchema": [{"AttributeName": "_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "_id", "AttributeType": "S"},
        ],
    },
    f"{PREFIX}-hotels": {
        "KeySchema": [{"AttributeName": "_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "_id", "AttributeType": "S"},
        ],
    },
    f"{PREFIX}-trains": {
        "KeySchema": [{"AttributeName": "_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "_id", "AttributeType": "S"},
        ],
    },
    f"{PREFIX}-buses": {
        "KeySchema": [{"AttributeName": "_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "_id", "AttributeType": "S"},
        ],
    },
    f"{PREFIX}-bookings": {
        "KeySchema": [{"AttributeName": "_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "_id", "AttributeType": "S"},
            {"AttributeName": "user_id", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "user_id-index",
                "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
    },
    f"{PREFIX}-notifications": {
        "KeySchema": [{"AttributeName": "_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "_id", "AttributeType": "S"},
            {"AttributeName": "user_id", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "user_id-index",
                "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
    },
}


def _create_tables():
    existing = dynamodb_client.list_tables()["TableNames"]
    for table_name, schema in TABLE_DEFS.items():
        if table_name in existing:
            print(f"  Table {table_name} already exists, skipping.")
            continue
        params = {
            "TableName": table_name,
            "KeySchema": schema["KeySchema"],
            "AttributeDefinitions": schema["AttributeDefinitions"],
            "BillingMode": "PAY_PER_REQUEST",
        }
        if "GlobalSecondaryIndexes" in schema:
            params["GlobalSecondaryIndexes"] = schema["GlobalSecondaryIndexes"]
        dynamodb_client.create_table(**params)
        print(f"  Creating {table_name} ...")
        waiter = dynamodb_client.get_waiter("table_exists")
        waiter.wait(TableName=table_name)
        print(f"  ✅  {table_name} ready.")


def _batch_put(table_name, items):
    table = dynamodb.Table(table_name)
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
    print(f"  [+] Inserted {len(items)} items into {table_name}.")


def seed():
    print("Creating DynamoDB tables …")
    _create_tables()
    print()

    print("Generating Indian travel datasets (50 each) …")
    generate_flights()
    generate_hotels()
    generate_trains()
    generate_buses()
    print()

    flights = _load_json("flights.json")
    for doc in flights:
        doc["_id"] = str(uuid.uuid4())
        doc["created_at"] = _now()
        doc["price"] = Decimal(str(doc["price"]))
        doc["availability"] = int(doc["availability"])
    _batch_put(f"{PREFIX}-flights", flights)

    hotels = _load_json("hotels.json")
    for doc in hotels:
        doc["_id"] = str(uuid.uuid4())
        doc["created_at"] = _now()
        doc["price"] = Decimal(str(doc["price"]))
        doc["rating"] = Decimal(str(doc["rating"]))
        doc["rooms"] = int(doc["rooms"])
        doc["availability"] = int(doc["availability"])
    _batch_put(f"{PREFIX}-hotels", hotels)

    trains = _load_json("trains.json")
    for doc in trains:
        doc["_id"] = str(uuid.uuid4())
        doc["created_at"] = _now()
        doc["price"] = Decimal(str(doc["price"]))
        doc["availability"] = int(doc["availability"])
    _batch_put(f"{PREFIX}-trains", trains)

    buses = _load_json("buses.json")
    for doc in buses:
        doc["_id"] = str(uuid.uuid4())
        doc["created_at"] = _now()
        doc["price"] = Decimal(str(doc["price"]))
        doc["availability"] = int(doc["availability"])
    _batch_put(f"{PREFIX}-buses", buses)

    total = len(flights) + len(hotels) + len(trains) + len(buses)
    print(f"\n✅  DynamoDB seeded successfully! ({total} bookable records)")


if __name__ == "__main__":
    seed()
