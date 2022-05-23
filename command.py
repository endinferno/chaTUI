import sys
import webaas_api

chatroom_info = None

class ChatRoomApp:
    def __init__(self, show_person, show_message):
        self.chatroom_info = None
        self.show_person_func = show_person
        self.show_message_func = show_message

    def process_join(self, join_command):
        username = join_command[0]
        chatroom_id = int(join_command[1])

        if self.chatroom_info == None:
            self.chatroom_info = webaas_api.ChatRoomInfo(
                chatroom_id, self.show_person_func, self.show_message_func)

        if self.in_chatroom():
            # Logout Current ChatRoom
            self.chatroom_info.logout()
            # Login Another ChatRoom
            self.chatroom_info.set_chatroom_id(chatroom_id)
            self.chatroom_info.login(username)
        else:
            # Login ChatRoom
            self.chatroom_info.set_chatroom_id(chatroom_id)
            self.chatroom_info.login(username)

    def process_show(self, show_command):
        chatroom_id = int(show_command[0])
        show_property = show_command[1]
        temp_chatroom_info = webaas_api.ChatRoomInfo(
                chatroom_id, self.show_person_func, self.show_message_func)
        if show_property == 'People':
            temp_chatroom_info.show_person()
        elif show_property == 'Message':
            temp_chatroom_info.show_message()
        elif show_property == 'ChatRoom':
            chatroom_print_list = []
            chatroom_id_list = webaas_api.get_used_chatroom_id()
            for item in chatroom_id_list:
                chatroom_print_list.append("ChatRoom ID: " + str(item))
            self.show_message_func(chatroom_print_list)

    def process_leave(self):
        if self.chatroom_info == None:
            self.show_message_func(["You Are Not Logged In!"])
            return

        if self.in_chatroom():
            # log out
            self.chatroom_info.logout()
        else:
            self.show_message_func(["You Are Not Logged In!"])

    def process_message(self, message):
        if self.chatroom_info == None:
            self.show_message_func(["You Are Not in ChatRoom Now!"])
            return

        if self.in_chatroom():
            self.chatroom_info.send_msg(message)
        else:
            self.show_message_func(["You Are Not Logged In!"])
            return

    def process_help(self):
        message_list = []
        message_list.append("/help")
        message_list.append("    Command Help")
        message_list.append("/join")
        message_list.append("    /join \[username] \[chatroom_id]")
        message_list.append("/show")
        message_list.append("    /show \[chatroom_id] \[show_property]")
        message_list.append("    \[show_property]")
        message_list.append("        People")
        message_list.append("        Message")
        message_list.append("        ChatRoom")
        self.show_message_func(message_list)

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

    def in_chatroom(self):
        return self.chatroom_info.is_in_chatroom()

    def init_app(self):
        webaas_api.test_endpoint()
#        webaas_api.register()
#        webaas_api.create_schema()

