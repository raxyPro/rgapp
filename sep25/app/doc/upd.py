import json
from collections import OrderedDict
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Update with your DB connection string
engine = create_engine("mysql+pymysql://rax:512@localhost/rcmain", echo=False)
Session = sessionmaker(bind=engine)
session = Session()

def add_two_col(session):
    # Step 1: Fetch all records
    results = session.execute(text("SELECT id, pf_data FROM profcv")).fetchall()

    # Step 2: Loop through each and update JSON
    for row in results:
        record_id = row[0]
        try:
            data = json.loads(row[1])

            # Add new keys if they don't exist
            data['public_name'] = data.get('name', 'Unknown')
            data['public_title'] = data.get('role', 'Professional')

            # Convert back to JSON string
            updated_json = json.dumps(data, ensure_ascii=False)

            # Update the row in DB
            session.execute(
                text("UPDATE profcv SET pf_data = :pf_data WHERE id = :id"),
                {"pf_data": updated_json, "id": record_id}
            )
        except Exception as e:
            print(f"Skipping ID {record_id} due to error: {e}")

    session.commit()
    print("✅ All records updated with public_name and public_title.")

def update_order(session):
    # Fetch all pf_data
    results = session.execute(text("SELECT id, pf_data FROM profcv")).fetchall()

    for row in results:
        record_id = row[0]
        try:
            original_data = json.loads(row[1])

            # Build new ordered JSON with public_name and public_title first
            new_data = OrderedDict()

            if "public_name" in original_data:
                new_data["public_name"] = original_data.pop("public_name")
            if "public_title" in original_data:
                new_data["public_title"] = original_data.pop("public_title")

            # Add remaining keys
            for k, v in original_data.items():
                new_data[k] = v

            updated_json = json.dumps(new_data, ensure_ascii=False)

            # Update DB
            session.execute(
                text("UPDATE profcv SET pf_data = :pf_data WHERE id = :id"),
                {"pf_data": updated_json, "id": record_id}
            )

        except Exception as e:
            print(f"Error on ID {record_id}: {e}")

    session.commit()
    print("✅ Reordered pf_data JSON fields.")

def add_location(session):
    # Fetch all profcv records
    results = session.execute(text("SELECT id, pf_data FROM profcv")).fetchall()

    for row in results:
        record_id = row[0]
        try:
            data = json.loads(row[1])

            # Add default location if not already present
            if "location" not in data:
                data["location"] = "New Delhi, India"  # You can customize this default

                # Convert back to JSON
                updated_json = json.dumps(data, ensure_ascii=False)

                # Update the record
                session.execute(
                    text("UPDATE profcv SET pf_data = :pf_data WHERE id = :id"),
                    {"pf_data": updated_json, "id": record_id}
                )
        except Exception as e:
            print(f"Error on ID {record_id}: {e}")

    session.commit()
    print("✅ Location added to all applicable pf_data entries.")


if __name__ == "__main__":
    # First ensure columns are added
    add_location(session)

    # Then reorder the JSON
    update_order(session)

    session.close()
    print("✅ Script completed successfully.")
