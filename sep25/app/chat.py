from app.models import db, ChatManager, Vemp
manager = ChatManager(db)
creator_id = 1
user_id_2 = 2
# Create topic
topic = manager.create_topic("Team Discussion", creator_id)
print("Created Topic:", topic.name)

# Add users to topic
manager.add_user_to_topic(topic.id, creator_id)
manager.add_user_to_topic(topic.id, user_id_2)
print(f"Added users {creator_id} and {user_id_2} to topic {topic.name}")

# Send message
message = manager.send_message(topic.id, creator_id, "Welcome to the team chat!")
print("Sent Message:", message.message)