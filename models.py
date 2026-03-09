import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash
from boto3.dynamodb.conditions import Key, Attr


def _now():
    return datetime.now(timezone.utc).isoformat()


def _uuid():
    return str(uuid.uuid4())


def _decimal(val):
    return Decimal(str(val)) if val is not None else Decimal("0")


def _clean_item(item):
    if item is None:
        return None
    cleaned = {}
    for k, v in item.items():
        if isinstance(v, Decimal):
            cleaned[k] = float(v)
        elif isinstance(v, dict):
            cleaned[k] = _clean_item(v)
        elif isinstance(v, list):
            cleaned[k] = [_clean_item(i) if isinstance(i, dict) else (float(i) if isinstance(i, Decimal) else i) for i in v]
        else:
            cleaned[k] = v
    return cleaned


def _clean_items(items):
    return [_clean_item(i) for i in items]


class UserModel:

    def __init__(self, table):
        self.table = table

    def create_user(self, username, email, password, role="user"):
        user_id = _uuid()
        user = {
            "_id": user_id,
            "username": username,
            "email": email.lower().strip(),
            "password_hash": generate_password_hash(password),
            "role": role,
            "phone": "",
            "address": "",
            "created_at": _now(),
        }
        self.table.put_item(Item=user)
        return user

    def find_by_email(self, email):
        resp = self.table.query(
            IndexName="email-index",
            KeyConditionExpression=Key("email").eq(email.lower().strip()),
        )
        items = resp.get("Items", [])
        return _clean_item(items[0]) if items else None

    def find_by_username(self, username):
        resp = self.table.query(
            IndexName="username-index",
            KeyConditionExpression=Key("username").eq(username),
        )
        items = resp.get("Items", [])
        return _clean_item(items[0]) if items else None

    def find_by_id(self, user_id):
        resp = self.table.get_item(Key={"_id": str(user_id)})
        return _clean_item(resp.get("Item"))

    def verify_password(self, stored_hash, password):
        return check_password_hash(stored_hash, password)

    def update_profile(self, user_id, data):
        allowed = {"username", "phone", "address"}
        update_data = {k: v for k, v in data.items() if k in allowed}
        if update_data:
            expr_parts = []
            attr_names = {}
            attr_vals = {}
            for i, (k, v) in enumerate(update_data.items()):
                placeholder = f"#k{i}"
                val_placeholder = f":v{i}"
                expr_parts.append(f"{placeholder} = {val_placeholder}")
                attr_names[placeholder] = k
                attr_vals[val_placeholder] = v
            self.table.update_item(
                Key={"_id": str(user_id)},
                UpdateExpression="SET " + ", ".join(expr_parts),
                ExpressionAttributeNames=attr_names,
                ExpressionAttributeValues=attr_vals,
            )

    def change_password(self, user_id, new_password):
        self.table.update_item(
            Key={"_id": str(user_id)},
            UpdateExpression="SET password_hash = :ph",
            ExpressionAttributeValues={":ph": generate_password_hash(new_password)},
        )

    def get_all_users(self):
        return _clean_items(self.table.scan().get("Items", []))

    def count(self):
        return self.table.scan(Select="COUNT").get("Count", 0)


class FlightModel:

    def __init__(self, table):
        self.table = table

    def add(self, data):
        data["_id"] = _uuid()
        data.setdefault("created_at", _now())
        data.setdefault("availability", 60)
        data["availability"] = int(data["availability"])
        data["price"] = _decimal(data.get("price", 0))
        self.table.put_item(Item=data)
        return data

    def get_all(self):
        return _clean_items(self.table.scan().get("Items", []))

    def find_by_id(self, fid):
        resp = self.table.get_item(Key={"_id": str(fid)})
        return _clean_item(resp.get("Item"))

    def update(self, fid, data):
        if "price" in data:
            data["price"] = _decimal(data["price"])
        if "availability" in data:
            data["availability"] = int(data["availability"])
        expr_parts = []
        attr_names = {}
        attr_vals = {}
        for i, (k, v) in enumerate(data.items()):
            placeholder = f"#k{i}"
            val_placeholder = f":v{i}"
            expr_parts.append(f"{placeholder} = {val_placeholder}")
            attr_names[placeholder] = k
            attr_vals[val_placeholder] = v
        if expr_parts:
            self.table.update_item(
                Key={"_id": str(fid)},
                UpdateExpression="SET " + ", ".join(expr_parts),
                ExpressionAttributeNames=attr_names,
                ExpressionAttributeValues=attr_vals,
            )

    def delete(self, fid):
        self.table.delete_item(Key={"_id": str(fid)})

    def search(self, source, destination, date=None):
        items = self.table.scan().get("Items", [])
        src_lower = source.lower()
        dst_lower = destination.lower()
        results = []
        for item in items:
            if src_lower not in item.get("source", "").lower():
                continue
            if dst_lower not in item.get("destination", "").lower():
                continue
            if int(item.get("availability", 0)) <= 0:
                continue
            if date:
                try:
                    d = datetime.strptime(date, "%Y-%m-%d")
                    start = (d - timedelta(days=3)).strftime("%Y-%m-%d")
                    end = (d + timedelta(days=3)).strftime("%Y-%m-%d")
                    item_date = item.get("date", "")
                    if not (start <= item_date <= end):
                        continue
                except ValueError:
                    if item.get("date") != date:
                        continue
            results.append(item)
        return _clean_items(results)

    def decrement_availability(self, fid, count=1):
        self.table.update_item(
            Key={"_id": str(fid)},
            UpdateExpression="SET availability = availability - :c",
            ConditionExpression=Attr("availability").gte(count),
            ExpressionAttributeValues={":c": count},
        )

    def count(self):
        return self.table.scan(Select="COUNT").get("Count", 0)


class HotelModel:

    def __init__(self, table):
        self.table = table

    def add(self, data):
        data["_id"] = _uuid()
        data.setdefault("created_at", _now())
        data.setdefault("availability", 20)
        data["availability"] = int(data["availability"])
        data["price"] = _decimal(data.get("price", 0))
        data["rating"] = _decimal(data.get("rating", 3.0))
        self.table.put_item(Item=data)
        return data

    def get_all(self):
        return _clean_items(self.table.scan().get("Items", []))

    def find_by_id(self, hid):
        resp = self.table.get_item(Key={"_id": str(hid)})
        return _clean_item(resp.get("Item"))

    def update(self, hid, data):
        if "price" in data:
            data["price"] = _decimal(data["price"])
        if "availability" in data:
            data["availability"] = int(data["availability"])
        if "rating" in data:
            data["rating"] = _decimal(data["rating"])
        expr_parts = []
        attr_names = {}
        attr_vals = {}
        for i, (k, v) in enumerate(data.items()):
            placeholder = f"#k{i}"
            val_placeholder = f":v{i}"
            expr_parts.append(f"{placeholder} = {val_placeholder}")
            attr_names[placeholder] = k
            attr_vals[val_placeholder] = v
        if expr_parts:
            self.table.update_item(
                Key={"_id": str(hid)},
                UpdateExpression="SET " + ", ".join(expr_parts),
                ExpressionAttributeNames=attr_names,
                ExpressionAttributeValues=attr_vals,
            )

    def delete(self, hid):
        self.table.delete_item(Key={"_id": str(hid)})

    def search(self, destination, checkin=None):
        items = self.table.scan().get("Items", [])
        dst_lower = destination.lower()
        results = []
        for item in items:
            if dst_lower not in item.get("destination", "").lower():
                continue
            if int(item.get("availability", 0)) <= 0:
                continue
            if checkin:
                try:
                    d = datetime.strptime(checkin, "%Y-%m-%d")
                    start = (d - timedelta(days=3)).strftime("%Y-%m-%d")
                    end = (d + timedelta(days=3)).strftime("%Y-%m-%d")
                    item_date = item.get("checkin", "")
                    if not (start <= item_date <= end):
                        continue
                except ValueError:
                    if item.get("checkin") != checkin:
                        continue
            results.append(item)
        return _clean_items(results)

    def decrement_availability(self, hid, count=1):
        self.table.update_item(
            Key={"_id": str(hid)},
            UpdateExpression="SET availability = availability - :c",
            ConditionExpression=Attr("availability").gte(count),
            ExpressionAttributeValues={":c": count},
        )

    def count(self):
        return self.table.scan(Select="COUNT").get("Count", 0)


class TrainModel:

    def __init__(self, table):
        self.table = table

    def add(self, data):
        data["_id"] = _uuid()
        data.setdefault("created_at", _now())
        data.setdefault("availability", 100)
        data["availability"] = int(data["availability"])
        data["price"] = _decimal(data.get("price", 0))
        self.table.put_item(Item=data)
        return data

    def get_all(self):
        return _clean_items(self.table.scan().get("Items", []))

    def find_by_id(self, tid):
        resp = self.table.get_item(Key={"_id": str(tid)})
        return _clean_item(resp.get("Item"))

    def update(self, tid, data):
        if "price" in data:
            data["price"] = _decimal(data["price"])
        if "availability" in data:
            data["availability"] = int(data["availability"])
        expr_parts = []
        attr_names = {}
        attr_vals = {}
        for i, (k, v) in enumerate(data.items()):
            placeholder = f"#k{i}"
            val_placeholder = f":v{i}"
            expr_parts.append(f"{placeholder} = {val_placeholder}")
            attr_names[placeholder] = k
            attr_vals[val_placeholder] = v
        if expr_parts:
            self.table.update_item(
                Key={"_id": str(tid)},
                UpdateExpression="SET " + ", ".join(expr_parts),
                ExpressionAttributeNames=attr_names,
                ExpressionAttributeValues=attr_vals,
            )

    def delete(self, tid):
        self.table.delete_item(Key={"_id": str(tid)})

    def search(self, source, destination, date=None):
        items = self.table.scan().get("Items", [])
        src_lower = source.lower()
        dst_lower = destination.lower()
        results = []
        for item in items:
            if src_lower not in item.get("source", "").lower():
                continue
            if dst_lower not in item.get("destination", "").lower():
                continue
            if int(item.get("availability", 0)) <= 0:
                continue
            if date:
                try:
                    d = datetime.strptime(date, "%Y-%m-%d")
                    start = (d - timedelta(days=3)).strftime("%Y-%m-%d")
                    end = (d + timedelta(days=3)).strftime("%Y-%m-%d")
                    item_date = item.get("date", "")
                    if not (start <= item_date <= end):
                        continue
                except ValueError:
                    if item.get("date") != date:
                        continue
            results.append(item)
        return _clean_items(results)

    def decrement_availability(self, tid, count=1):
        self.table.update_item(
            Key={"_id": str(tid)},
            UpdateExpression="SET availability = availability - :c",
            ConditionExpression=Attr("availability").gte(count),
            ExpressionAttributeValues={":c": count},
        )

    def count(self):
        return self.table.scan(Select="COUNT").get("Count", 0)


class BusModel:

    def __init__(self, table):
        self.table = table

    def add(self, data):
        data["_id"] = _uuid()
        data.setdefault("created_at", _now())
        data.setdefault("availability", 40)
        data["availability"] = int(data["availability"])
        data["price"] = _decimal(data.get("price", 0))
        self.table.put_item(Item=data)
        return data

    def get_all(self):
        return _clean_items(self.table.scan().get("Items", []))

    def find_by_id(self, bid):
        resp = self.table.get_item(Key={"_id": str(bid)})
        return _clean_item(resp.get("Item"))

    def update(self, bid, data):
        if "price" in data:
            data["price"] = _decimal(data["price"])
        if "availability" in data:
            data["availability"] = int(data["availability"])
        expr_parts = []
        attr_names = {}
        attr_vals = {}
        for i, (k, v) in enumerate(data.items()):
            placeholder = f"#k{i}"
            val_placeholder = f":v{i}"
            expr_parts.append(f"{placeholder} = {val_placeholder}")
            attr_names[placeholder] = k
            attr_vals[val_placeholder] = v
        if expr_parts:
            self.table.update_item(
                Key={"_id": str(bid)},
                UpdateExpression="SET " + ", ".join(expr_parts),
                ExpressionAttributeNames=attr_names,
                ExpressionAttributeValues=attr_vals,
            )

    def delete(self, bid):
        self.table.delete_item(Key={"_id": str(bid)})

    def search(self, source, destination, date=None):
        items = self.table.scan().get("Items", [])
        src_lower = source.lower()
        dst_lower = destination.lower()
        results = []
        for item in items:
            if src_lower not in item.get("source", "").lower():
                continue
            if dst_lower not in item.get("destination", "").lower():
                continue
            if int(item.get("availability", 0)) <= 0:
                continue
            if date:
                try:
                    d = datetime.strptime(date, "%Y-%m-%d")
                    start = (d - timedelta(days=3)).strftime("%Y-%m-%d")
                    end = (d + timedelta(days=3)).strftime("%Y-%m-%d")
                    item_date = item.get("date", "")
                    if not (start <= item_date <= end):
                        continue
                except ValueError:
                    if item.get("date") != date:
                        continue
            results.append(item)
        return _clean_items(results)

    def decrement_availability(self, bid, count=1):
        self.table.update_item(
            Key={"_id": str(bid)},
            UpdateExpression="SET availability = availability - :c",
            ConditionExpression=Attr("availability").gte(count),
            ExpressionAttributeValues={":c": count},
        )

    def count(self):
        return self.table.scan(Select="COUNT").get("Count", 0)


class BookingModel:

    def __init__(self, table):
        self.table = table

    def create(self, data):
        data["_id"] = _uuid()
        data.setdefault("created_at", _now())
        data.setdefault("status", "confirmed")
        data["price"] = _decimal(data.get("price", 0))
        if "payment" in data:
            pay = data["payment"]
            if "paid_at" in pay:
                pay["paid_at"] = pay["paid_at"].isoformat() if hasattr(pay["paid_at"], "isoformat") else str(pay["paid_at"])
        self.table.put_item(Item=data)

        class _Result:
            def __init__(self, bid):
                self.inserted_id = bid
        return _Result(data["_id"])

    def find_by_user(self, user_id):
        resp = self.table.query(
            IndexName="user_id-index",
            KeyConditionExpression=Key("user_id").eq(str(user_id)),
        )
        items = _clean_items(resp.get("Items", []))
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items

    def find_by_id(self, booking_id):
        resp = self.table.get_item(Key={"_id": str(booking_id)})
        return _clean_item(resp.get("Item"))

    def is_duplicate(self, user_id, item_type, item_id, date):
        resp = self.table.query(
            IndexName="user_id-index",
            KeyConditionExpression=Key("user_id").eq(str(user_id)),
        )
        for item in resp.get("Items", []):
            if (item.get("item_type") == item_type
                    and item.get("item_id") == str(item_id)
                    and item.get("date") == date
                    and item.get("status") == "confirmed"):
                return _clean_item(item)
        return None

    def cancel(self, booking_id):
        self.table.update_item(
            Key={"_id": str(booking_id)},
            UpdateExpression="SET #s = :cancelled",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":cancelled": "cancelled"},
        )

    def get_all(self):
        items = _clean_items(self.table.scan().get("Items", []))
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items

    def count(self):
        return self.table.scan(Select="COUNT").get("Count", 0)

    def count_by_type(self):
        items = self.table.scan(
            ProjectionExpression="item_type",
        ).get("Items", [])
        counts = {}
        for item in items:
            t = item.get("item_type", "unknown")
            counts[t] = counts.get(t, 0) + 1
        return counts


class NotificationModel:

    def __init__(self, table):
        self.table = table

    def create(self, user_id, message, notif_type="info"):
        notif = {
            "_id": _uuid(),
            "user_id": str(user_id),
            "message": message,
            "type": notif_type,
            "read": False,
            "created_at": _now(),
        }
        self.table.put_item(Item=notif)
        return notif

    def get_for_user(self, user_id, limit=20):
        resp = self.table.query(
            IndexName="user_id-index",
            KeyConditionExpression=Key("user_id").eq(str(user_id)),
        )
        items = _clean_items(resp.get("Items", []))
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items[:limit]

    def mark_read(self, notif_id):
        self.table.update_item(
            Key={"_id": str(notif_id)},
            UpdateExpression="SET #r = :t",
            ExpressionAttributeNames={"#r": "read"},
            ExpressionAttributeValues={":t": True},
        )

    def unread_count(self, user_id):
        resp = self.table.query(
            IndexName="user_id-index",
            KeyConditionExpression=Key("user_id").eq(str(user_id)),
            FilterExpression=Attr("read").eq(False),
            Select="COUNT",
        )
        return resp.get("Count", 0)
