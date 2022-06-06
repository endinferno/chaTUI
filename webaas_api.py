import requests
import uuid
import sys
import json
import chatroom_pb2
import websockets
import asyncio
import threading
from google.protobuf.timestamp_pb2 import Timestamp
import datetime

ip = '202.120.40.82'
port_list = [11232, 11233]
port = 0
appName = 'python-ChaTUI' + str(uuid.uuid4())  # unique app name
appID = None

err_code = {
    1001: "Invalid Format",
    1002: "Data Not Found",
    1003: "Permission Denied",
    1004: "Repeated Request",
    1005: "Invalid Schema",
    1006: "Invalid Version",
}

def get_endpoint():
    return ip + ':' + str(port)

def get_err_code(response_json):
    return err_code.get(response_json['code'], "Invalid Response Code")

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
    r = requests.post("http://" + get_endpoint() + "/app", params={"appName": appName})
    if r.status_code == 200:
        appID = r.json()["appID"]
    else:
        sys.exit(1)

def unregister():
    global appID
    r = requests.delete("http://" + get_endpoint() + "/app",
                        params={"appName": appName, "appID": appID})
    if r.status_code == 200:
        return
    else:
        print("Fail to Delete APP")

def create_schema():
    # upload schema file
    with open("proto/chatroom.proto", "rb") as f:
        r = requests.put("http://" + get_endpoint() + "/schema", data = f.read(),
                         params = {"appID": appID,
                                   "fileName": "chatroom.proto",
                                   "version": "1.0.0"})
        if r.status_code != 200:
            sys.exit(1)
    # update schema version
    r = requests.post("http://" + get_endpoint() + "/schema",
                      params={"appID": appID, "version": "1.0.0"})
    if r.status_code != 200:
        sys.exit(1)

def get_used_chatroom_id():
    chatroom_id_list = []
    for idx in range(1, 100):
        r = requests.get("http://" + get_endpoint() + "/query",
                         params={"appID": appID,
                                 "schemaName": "example.ChatRoom",
                                 "recordKey": idx})
        if r.status_code != 200:
            break
        chatroom = chatroom_pb2.ChatRoom().FromString(r.content)
        if chatroom == None:
            break
        chatroom_id_list.append(idx)
    return chatroom_id_list

def get_avail_chatroom_id():
    chatroom_id_list = get_used_chatroom_id()
    if len(chatroom_id_list) == 0:
        cur_max_chatroom_id = 0
    else:
        cur_max_chatroom_id = chatroom_id_list[-1]
    return cur_max_chatroom_id + 1

def create_chatroom():
    chatroom = chatroom_pb2.ChatRoom()
    chatroom.id = get_avail_chatroom_id()
    r = requests.post("http://" + get_endpoint() + "/record",
                      params={"appID": appID, "schemaName": "example.ChatRoom"},
                      data=chatroom.SerializeToString())
    if r.status_code != 200:
        sys.exit(1)

def update_chatroom(chatroom: chatroom_pb2.ChatRoom):
    r = requests.post("http://" + get_endpoint() + "/record",
                      params={"appID": appID, "schemaName": "example.ChatRoom"},
                      data=chatroom.SerializeToString())
    if r.status_code != 200:
        sys.exit(1)

def get_person(person_id):
    r = requests.get("http://" + get_endpoint() + "/query",
                     params={"appID": appID,
                             "schemaName": "example.Person",
                             "recordKey": person_id})
    if r.status_code != 200:
        return None
    person = chatroom_pb2.Person().FromString(r.content)
    return person

def create_person(person):
    r = requests.post("http://" + get_endpoint() + "/record",
                      params={"appID": appID, "schemaName": "example.Person"},
                      data=person.SerializeToString())
    if r.status_code != 200:
        sys.exit(1)

def delete_person(person_id):
    r = requests.delete("http://" + get_endpoint() + "/record",
                        params={"appID": appID, 
                                "schemaName": "example.Person", 
                                "recordKey": person_id})
    if r.status_code != 200:
        sys.exit(1)

def create_message(message):
    r = requests.post("http://" + get_endpoint() + "/record", params={
        "appID": appID, "schemaName": "example.Message"}, data=message.SerializeToString())
    if r.status_code != 200:
        sys.exit(1)

def create_notification(schema_name, record_key):
    params = {
        "appID": appID,
        "schemaName": schema_name,
        "recordKeys": [
            record_key
        ]
    }
    r = requests.post('http://' + get_endpoint() + "/notification", data=json.dumps(params))
    if r.status_code != 200:
        sys.exit(1)
    return r.json()["notificationID"]

def delete_notification(schema_name, notification_id):
    r = requests.delete('http://' + get_endpoint() + "/notification", params = {
        "appID": appID, 
        "notificationID": notification_id
    })
    if r.status_code != 200:
        sys.exit(1)
    return r.json()["notificationID"]

class ChatRoomInfo:
    def __init__(self, show_person_func, show_message_func):
        self.show_person_func = show_person_func
        self.show_message_func = show_message_func
        self.in_chatroom = False
        self.msg_from_myself = False

    def login(self, username):
        self.in_chatroom = True
        self.username = username
        # Create User
        self.person_id = self.get_avail_person_id()
        new_person = chatroom_pb2.Person()
        new_person.id = self.person_id
        new_person.name = username
        create_person(new_person)
        # Add User To ChatRoom
        self.add_person_to_chatroom(self.person_id, self.chatroom_id)
        # Show People List in SideBar
        self.chatroom = self.get_chatroom(self.chatroom_id)
        self.people_list = self.get_people_list(self.chatroom)
        self.show_person_func(self.people_list)
        # Show History Messages
        message_list = self.get_message_list(self.chatroom)
        self.msg_list = message_list[-20:]
        self.show_message_func(self.msg_list)
        self.send_join_msg("joined the ChatRoom")
        # Create Notification of Current ChatRoom
        self.n_id = create_notification('example.ChatRoom', str(self.chatroom_id))
        self.thread_running = True
        event_loop = asyncio.new_event_loop()
        p = threading.Thread(target=self.wait_notification_person, 
                             args=(event_loop, ))
        p.start()

    def logout(self):
        self.send_left_msg("left ChatRoom")
        self.in_chatroom = False
        # Stop the Thread
        self.thread_running = False
        # Delete User
        delete_person(self.person_id)
        self.del_person_from_chatroom(self.person_id, self.chatroom_id)
        # Delete notification
        delete_notification('example.ChatRoom', self.n_id)

    async def person_notification_worker(self):
        # Update ChatRoom
        path = 'ws://' + get_endpoint() + '/notification' + '?appID=' + appID + '&notificationID=' + self.n_id
        async with websockets.connect(path) as websocket:
            while self.thread_running:
                # Next User Join
                msg = await websocket.recv()
                self.chatroom = self.get_chatroom(self.chatroom_id)
                if len(self.people_list) == len(self.chatroom.people):
                    if self.msg_from_myself:
                        self.msg_from_myself = False
                        continue
                    # Get ChatRoom Message
                    self.msg_list.append(
                        ChatRoomInfo.format_message(self.chatroom.msg[-1])
                    )
                    if self.in_chatroom:
                        self.show_message_func(self.msg_list)
                else:
                    # Get ChatRoom People
                    self.people_list = []
                    for person in self.chatroom.people:
                        self.people_list.append(person.name)
                    if self.in_chatroom:
                        self.show_person_func(self.people_list)
            # Close Websockets
            await websocket.close(reason='exit')
        return

    def wait_notification_person(self, event_loop):
        asyncio.set_event_loop(event_loop)
        event_loop.run_until_complete(self.person_notification_worker())

    def set_chatroom_id(self, chatroom_id):
        self.chatroom_id = chatroom_id
        self.chatroom = self.get_chatroom(self.chatroom_id)

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

    def send_join_msg(self, message_str):
        new_msg = self.create_msg(
            message_str, chatroom_pb2.MessageType.SYS_JOIN_MSG, self.username)
        self.send_msg(new_msg)
        self.msg_list.append(self.format_message(new_msg))
        self.show_message_func(self.msg_list)

    def send_left_msg(self, message_str):
        new_msg = self.create_msg(
            message_str, chatroom_pb2.MessageType.SYS_LEFT_MSG, self.username)
        self.send_msg(new_msg)
        self.msg_list.append(self.format_message(new_msg))
        self.show_message_func(self.msg_list)

    def send_user_msg(self, message_str):
        self.msg_from_myself = True
        new_msg = self.create_msg(
            message_str, chatroom_pb2.MessageType.USER_MSG, self.username)
        self.send_msg(new_msg)
        self.msg_list.append(self.format_message(new_msg))
        self.show_message_func(self.msg_list)

    def create_msg(self, message_str, message_type, username):
        new_message = chatroom_pb2.Message()
        new_message.data = message_str
        new_message.time.GetCurrentTime()
        new_message.type = message_type
        new_message.people = username
        return new_message

    def send_msg(self, message):
        create_message(message)
        self.add_message_to_chatroom(message, self.chatroom_id)

    def add_person_to_chatroom(self, person_id, chatroom_id):
        chatroom = self.get_chatroom(chatroom_id)
        person = get_person(person_id)
        chatroom.people.insert(person_id - 1, person)
        update_chatroom(chatroom)

    def add_message_to_chatroom(self, message, chatroom_id):
        chatroom = self.get_chatroom(chatroom_id)
        chatroom.msg.append(message)
        update_chatroom(chatroom)

    @staticmethod
    def format_message(proto_message):
        msg_date_time = proto_message.time.ToDatetime()
        username = proto_message.people
        message = proto_message.data
        msg_type = proto_message.type
        if msg_type == chatroom_pb2.MessageType.USER_MSG:
            time_color = '[#4D4D4D]'
            name_color = '[#95B253 bold]'
            message_color = '[#CFCFCF]'
            return "{}\[{}] {}<{}> {}{}".format(time_color, msg_date_time.strftime('%H:%M:%S'),
                                         name_color, username, message_color, message)
        elif msg_type == chatroom_pb2.MessageType.SYS_JOIN_MSG:
            time_color = '[#4D4D4D]'
            arrow_color = '[#A5C3A7]'
            name_color = '[#434343 bold]'
            message_color = '[#434343]'
            return "{}\[{}]{} -> {}{} {}{}".format(time_color, msg_date_time.strftime('%H:%M:%S'),
                                            arrow_color, name_color, username, message_color, message)
        elif msg_type == chatroom_pb2.MessageType.SYS_LEFT_MSG:
            time_color = '[#4D4D4D]'
            arrow_color = '[#EB7886]'
            name_color = '[#434343 bold]'
            message_color = '[#434343]'
            return "{}\[{}]{} <- {}{} {}{}".format(time_color, msg_date_time.strftime('%H:%M:%S'),
                                            arrow_color, name_color, username, message_color, message)
        else:
            return ""

    @staticmethod
    def del_person_from_chatroom(person_id, chatroom_id):
        chatroom = ChatRoomInfo.get_chatroom(chatroom_id)
        for item in chatroom.people:
            if item.id == person_id:
                chatroom.people.remove(item)
                update_chatroom(chatroom)

    @staticmethod
    def get_chatroom(chatroom_id):
        r = requests.get("http://" + get_endpoint() + "/query",
                         params={"appID": appID,
                                 "schemaName": "example.ChatRoom",
                                 "recordKey": chatroom_id})
        if r.status_code != 200:
            return None
        chatroom = chatroom_pb2.ChatRoom().FromString(r.content)
        if chatroom == None:
            return None
        return chatroom

    @staticmethod
    def get_people_list(chatroom):
        people_list = []
        for item in chatroom.people:
            people_list.append(item.name)
        return people_list

    @staticmethod
    def get_message_list(chatroom):
        message_list = []
        for item in chatroom.msg:
            message_list.append(
                ChatRoomInfo.format_message(item)
            )
        return message_list

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
