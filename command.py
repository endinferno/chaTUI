import sys
import webaas_api
import pytermgui as ptg

class ChatRoomApp:
    def __init__(self, show_person, show_message, body_window):
        self.show_person_func = show_person
        self.show_message_func = show_message
        self.body_window = body_window
        self.chatroom_info = webaas_api.ChatRoomInfo(
            self.show_person_func, self.show_message_func)

    def process_join(self, join_command):
        username = join_command[0]
        chatroom_id = int(join_command[1])

        if self.in_chatroom():
            # Logout Current ChatRoom
            self.chatroom_info.logout()
            # Login Another ChatRoom
            self.chatroom_info.set_chatroom_id(chatroom_id)
            self.chatroom_info.login(username)
            corner = ["", "", "", ""]
            corner[ptg.VerticalAlignment.TOP] = "[bold #FCBA03]ChatRoom {}".format(chatroom_id)
            self.body_window.set_char("corner", corner)
        else:
            # Login ChatRoom
            self.chatroom_info.set_chatroom_id(chatroom_id)
            self.chatroom_info.login(username)
            corner = ["", "", "", ""]
            corner[ptg.VerticalAlignment.TOP] = "[bold #FCBA03]ChatRoom {}".format(chatroom_id)
            self.body_window.set_char("corner", corner)

    def process_show(self, show_command):
        chatroom_id = int(show_command[0])
        show_property = show_command[1]
        if show_property == 'People':
            people_list = []
            chatroom = webaas_api.ChatRoomInfo.get_chatroom(chatroom_id)
            if chatroom == None:
                people_list.append("There is No ChatRoom ID " + str(chatroom_id))
                self.show_person_func(people_list)
                return
            people_list = webaas_api.ChatRoomInfo.get_people_list(chatroom)
            if len(people_list) == 0:
                people_list.append("There is No People in ChatRoom " + str(chatroom_id))
            self.show_person_func(people_list)
        elif show_property == 'Message':
            message_list = []
            chatroom = webaas_api.ChatRoomInfo.get_chatroom(chatroom_id)
            if chatroom == None:
                message_list.append("There is No ChatRoom ID " + str(chatroom_id))
                self.show_message_func(message_list)
                return
            message_list = webaas_api.ChatRoomInfo.get_message_list(chatroom)
            if len(message_list) == 0:
                message_list.append("There is No Message in ChatRoom " + str(chatroom_id))
            self.show_message_func(message_list)
        elif show_property == 'ChatRoom':
            chatroom_print_list = []
            chatroom_id_list = webaas_api.get_used_chatroom_id()
            if len(chatroom_id_list) == 0:
                chatroom_print_list.append("There is No ChatRoom")
            else:
                for item in chatroom_id_list:
                    chatroom_print_list.append("ChatRoom ID: " + str(item))
            self.show_message_func(chatroom_print_list)

    def process_leave(self):
        if self.in_chatroom():
            # log out
            self.chatroom_info.logout()
            corner = ["", "", "", ""]
            self.body_window.set_char("corner", corner)
            self.show_message_func([])
            self.show_person_func([])
        else:
            self.show_message_func(["You Are Not Logged In!"])

    def process_message(self, message):
        if self.in_chatroom():
            self.chatroom_info.send_user_msg(message)
        else:
            self.show_message_func(["You Are Not in ChatRoom Now!"])
            return

    def process_help(self):
        message_list = []
        message_list.append("/help")
        message_list.append("    Command Help")
        message_list.append("/join")
        message_list.append("    /join \[username] \[chatroom_id]")
        message_list.append("/create")
        message_list.append("/show")
        message_list.append("    /show \[chatroom_id] \[show_property]")
        message_list.append("    \[show_property]")
        message_list.append("        People")
        message_list.append("        Message")
        message_list.append("        ChatRoom")
        self.show_message_func(message_list)

    def process_create(self):
        webaas_api.create_chatroom()

    def process_command(self, command_line):
        command = str.split(command_line, ' ')
        root_command = command[0][1:]
        command_len = len(command)
        if root_command == 'join' and command_len == 3:
            return self.process_join(command[1:])
        elif root_command == 'show' and command_len == 3:
            return self.process_show(command[1:])
        elif root_command == 'help':
            return self.process_help()
        elif root_command == 'leave':
            self.process_leave()
        elif root_command == 'create':
            self.process_create()

    def in_chatroom(self):
        return self.chatroom_info.is_in_chatroom()

    def init_app(self):
        webaas_api.test_endpoint()
        webaas_api.register()
        webaas_api.create_schema()

    def release(self):
        if self.in_chatroom() == False:
            webaas_api.unregister()
            return

        self.chatroom_info.logout()
        webaas_api.unregister()

