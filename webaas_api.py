import requests
import uuid
import sys
import json
import address_book_pb2
import websockets
import asyncio
import threading
ip = '202.120.40.82'
port_list = [11232, 11233]
port = 0
# appName = "python-crud"+str(uuid.uuid4())  # unique app name
appName = "python-crud01a66ecc-d7e0-43e4-97be-1958461b6a12"
appID = "cef8dd2d-f80a-4843-a471-a05c5f7afca2"
# appID = None

def get_endpoint():
    return ip + ':' + str(port)

def test_endpoint():
    global port
    for item in port_list:
        r = requests.get("http://" + ip + ":" + str(item) + "/hello")
        if r.status_code != 200:
            print("Error test hello: "+r.text)
            continue
        port = item
        break
    if port == 0:
        print("WeBaas Server Connection Fail!")
        sys.exit(1)

def register():
    global appID
    print("Registering app...")
    r = requests.post("http://" + get_endpoint() + "/app", params={"appName": appName})
    print(appName)
    if r.status_code == 200:
        appID = r.json()["appID"]
        print("App registered with ID: "+appID)
    else:
        print("Error registering app: "+r.text)
        sys.exit(1)

def create_schema():
    print("Creating schema...")
    # upload schema file
    with open("proto/address_book.proto", "rb") as f:
        r = requests.put("http://" + get_endpoint() + "/schema", data = f.read(),
                         params = {"appID": appID,
                                   "fileName": "address_book.proto",
                                   "version": "1.0.0"})
        if r.status_code != 200:
            print("Error creating schema: "+r.text)
            sys.exit(1)
    print("Schema file uploaded.")
    # update schema version
    r = requests.post("http://" + get_endpoint() + "/schema",
                      params={"appID": appID, "version": "1.0.0"})
    if r.status_code != 200:
        print("Error updating schema version: "+r.text)
        sys.exit(1)
    print("Schema version updated.")

def create_chatroom(chatroom: address_book_pb2.ChatRoom):
    print("Creating Chat Room...")
    r = requests.post("http://" + get_endpoint() + "/record",
                      params={"appID": appID, "schemaName": "example.ChatRoom"},
                      data=chatroom.SerializeToString())
    if r.status_code != 200:
        print("Error creating chat room: "+r.text)
        sys.exit(1)
    print("Chat Room created.")

def get_person(person_id):
    r = requests.get("http://" + get_endpoint() + "/query",
                     params={"appID": appID,
                             "schemaName": "example.Person",
                             "recordKey": person_id})
    if r.status_code != 200:
        print("Error getting person: "+r.text)
        return None
    person = address_book_pb2.Person().FromString(r.content)
    return person

def create_person(person):
    r = requests.post("http://" + get_endpoint() + "/record",
                      params={"appID": appID, "schemaName": "example.Person"},
                      data=person.SerializeToString())
    if r.status_code != 200:
        print("Error creating person: "+r.text)
        sys.exit(1)

def delete_person(person_id):
    r = requests.delete("http://" + get_endpoint() + "/record",
                        params={"appID": appID, 
                                "schemaName": "example.Person", 
                                "recordKey": person_id})
    if r.status_code != 200:
        print("Error deleting person: "+r.text)
        sys.exit(1)

def create_message(message):
    r = requests.post("http://" + get_endpoint() + "/record", params={
        "appID": appID, "schemaName": "example.Message"}, data=message.SerializeToString())
    if r.status_code != 200:
        print("Error creating person: "+r.text)
        sys.exit(1)

def create_notification(schema_name, record_key):
    params = {
        "appID": appID,
        "schemaName": schema_name,
        "recordKeys": [
            record_key
        ]
    }
#    print("Creating notification...")
#    print(json.dumps(params))
    r = requests.post('http://' + get_endpoint() + "/notification", data=json.dumps(params))
    if r.status_code != 200:
        print("Error creating notification: "+r.text)
        sys.exit(1)
#    print("Notification created.")
#    print(r.json())
    return r.json()["notificationID"]

def delete_notification(schema_name, notification_id):
#    print("Deleting notification...")
    r = requests.delete('http://' + get_endpoint() + "/notification", params = {
        "appID": appID, 
        "notificationID": notification_id
    })
    if r.status_code != 200:
        print("Error creating notification: "+r.text)
        sys.exit(1)
#    print("Notification deleted.")
#    print(r.json())
    return r.json()["notificationID"]

def add_message(message, chatroom_id):
    chatroom = get_chatroom(chatroom_id)
    new_message = chatroom.msg.add()
    new_message.CopyFrom(message)
    create_chatroom(chatroom)

def send_msg(chatroom_id, message):
    chatroom = get_chatroom(chatroom_id)
    add_message(message, chatroom_id)
    # notify other Person in ChatRoom

class ChatRoomInfo:
    def __init__(self, chatroom_id, show_person_func, show_message_func):
        # Get ChatRoom By ID
        self.set_chatroom_id(chatroom_id)
        self.show_person_func = show_person_func
        self.show_message_func = show_message_func
        self.in_chatroom = False

    def login(self, username):
        self.in_chatroom = True
        # Create User
        self.person_id = self.get_avail_person_id()
        new_person = address_book_pb2.Person()
        new_person.id = self.person_id
        new_person.name = username
        create_person(new_person)
        # Add User To ChatRoom
        self.add_person_to_chatroom(self.person_id, self.chatroom_id)
        # Show People List in SideBar
        self.show_person()
        # 创建notification，当前用户对于Person的notification
        # 对于下一个Person的主键的notification
        self.chatroom = self.get_chatroom(self.chatroom_id)
        self.n_id = create_notification('example.ChatRoom', str(self.chatroom_id))
        self.thread_running = True
        event_loop = asyncio.new_event_loop()
        p = threading.Thread(target=self.wait_notification_person, 
                             args=(event_loop, ))
        p.start()

    def logout(self):
        self.in_chatroom = False
        # Stop the Thread
        self.thread_running = False
        # Delete User
        delete_person(self.person_id)
        self.del_person_from_chatroom(self.person_id, self.chatroom_id)
        self.show_person()
        delete_notification('example.ChatRoom', self.n_id)

    def get_chatroom(self, chatroom_id):
        r = requests.get("http://" + get_endpoint() + "/query",
                         params={"appID": appID,
                                 "schemaName": "example.ChatRoom",
                                 "recordKey": chatroom_id})
        if r.status_code != 200:
            print("Error getting address book: "+r.text)
            sys.exit(1)
        chatroom = address_book_pb2.ChatRoom().FromString(r.content)
        if chatroom == None:
            print("Error ChatRoom ID " + chatroom_id)
            sys.exit(1)
        return chatroom

    async def person_notification_worker(self):
        # Update ChatRoom
        path = 'ws://' + get_endpoint() + '/notification' + '?appID=' + appID + '&notificationID=' + self.n_id
        async with websockets.connect(path) as websocket:
            while self.thread_running:
                # Next User Join
                msg = await websocket.recv()
                # Get ChatRoom People
                self.chatroom = self.get_chatroom(self.chatroom_id)
                print("update person")
                people_list = []
                for item in self.chatroom.people:
                    people_list.append(item.name)
                print(people_list)
                self.show_person_func(people_list)
                # Get ChatRoom Message
                print("update message")
                message_list = []
                for item in self.chatroom.msg:
                    message_list.append(item.data)
                print(message_list)
                self.show_message_func(message_list)
            # Close Websockets
            await websocket.close(reason='exit')
        return

    def wait_notification_person(self, event_loop):
        asyncio.set_event_loop(event_loop)
        event_loop.run_until_complete(self.person_notification_worker())

    def set_chatroom_id(self, chatroom_id):
        self.chatroom_id = chatroom_id
        self.chatroom = get_chatroom(self.chatroom_id)

    def show_person(self):
        people_list = []
        self.chatroom = get_chatroom(self.chatroom_id)
        if self.chatroom == None:
            print("Error ChatRoom ID " + chatroom_id)
            sys.exit(1)
        for item in self.chatroom.people:
            people_list.append(item.name)
        self.show_person_func(people_list)

    def show_message(self):
        message_list = []
        self.chatroom = get_chatroom(self.chatroom_id)
        if self.chatroom == None:
            print("Error ChatRoom ID " + chatroom_id)
            sys.exit(1)
        for item in self.chatroom.msg:
            message_list.append(item.data)
        self.show_message_func(message_list)

    def show_chatroom(self):
        chatroom_id_list = []
        for idx in range(1, 100):
            r = requests.get("http://" + get_endpoint() + "/query",
                             params={"appID": appID,
                                     "schemaName": "example.ChatRoom",
                                     "recordKey": idx})
            if r.status_code != 200:
                break
            chatroom = address_book_pb2.ChatRoom().FromString(r.content)
            if chatroom == None:
                break
            chatroom_id_list.append('ChatRoom ID ' + str(idx))
        self.show_message_func(chatroom_id_list)
        return chatroom

    def is_in_chatroom(self):
        return self.in_chatroom

    def get_avail_person_id(self):
        self.chatroom = self.get_chatroom(self.chatroom_id)
        idx = 1
        for item in self.chatroom.people:
            if item.id == idx:
                idx += 1
                continue
            else:
                return idx
        return len(self.chatroom.people) + 1

    def send_msg(self, message):
        new_message = address_book_pb2.Message()
        new_message.data = message
        create_message(new_message)
        self.add_message_to_chatroom(new_message, self.chatroom_id)
        self.show_message_func([message])

    def add_person_to_chatroom(self, person_id, chatroom_id):
        chatroom = get_chatroom(chatroom_id)
        person = get_person(person_id)
        chatroom.people.insert(person_id - 1, person)
        create_chatroom(chatroom)

    def del_person_from_chatroom(self, person_id, chatroom_id):
        chatroom = get_chatroom(chatroom_id)
        for item in chatroom.people:
            if item.id == person_id:
                chatroom.people.remove(item)
                create_chatroom(chatroom)

    def add_message_to_chatroom(self, message, chatroom_id):
        chatroom = get_chatroom(chatroom_id)
        chatroom.msg.append(message)
        create_chatroom(chatroom)

def get_chatroom(chatroom_id):
    r = requests.get("http://" + get_endpoint() + "/query",
                     params={"appID": appID,
                             "schemaName": "example.ChatRoom",
                             "recordKey": chatroom_id})
    if r.status_code != 200:
        print("Error getting address book: "+r.text)
        sys.exit(1)
    chatroom = address_book_pb2.ChatRoom().FromString(r.content)
    if chatroom == None:
        print("Error ChatRoom ID " + chatroom_id)
        sys.exit(1)
    return chatroom

#if __name__ == "__main__":
#    print(chatroom.people)
#    print(chatroom.msg)
#    while True:
#        command = input("Enter command: ")
#        if command == "/join"
#        print("\n1. Join ChatRoom")
#        print("2. Create ChatRoom")
#        print("3. Exit")
#        choice = int(input("Enter choice: "))
#        if choice == 1:
#            # 检查房间号是否存在
#            chatroom_id = int(input("Enter ChatRoom: "))
#            login_chatroom(chatroom_id)
#        elif choice == 2:
#            chatroom = address_book_pb2.ChatRoom()
#            chatroom.id = int(input("Enter new ChatRoom ID: "))
#            create_chatroom(chatroom)
#        elif choice == 3:
#            break
