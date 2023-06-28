class Protocol:
    @staticmethod
    def unpack(packed_msg):
        """
        sends to unpack function by op code
        :param packed_msg: the message to unpack
        :return: list of op code and needed elements according to protocol
        """
        unpacks = {"0": Protocol._unpack_discover_msg, "1": Protocol._unpack_file_list_msg,
                   "2": Protocol._unpack_file_from_dok, "3": Protocol._unpack_file_port_msg,
                   "4": Protocol._unpack_file_request, "5": Protocol._unpack_file_upload_request,
                   "6": Protocol._unpack_file_to_dok, "8": Protocol._unpack_new_computer,
                   "9": Protocol._unpack_disconnected_drive}

        unpacked_msg = []
        op_code = packed_msg[:1]
        if op_code in unpacks.keys():
            unpacked_msg = unpacks[op_code](packed_msg)
        return unpacked_msg

    @staticmethod
    def pack_discover_msg(general_port):
        """
        pack the msg by the protocol
        :param general_port: port for general communication
        :return: the msg packed in 1 string
        """
        op_code = "0"                               # the op code
        msg = op_code + str(general_port).zfill(4)  # the message packed
        return msg

    @staticmethod
    def _unpack_discover_msg(packed_msg):
        """
        unpacks the message by relevant protocol
        :param packed_msg: the message to unpack
        :return: the op code and elements after unpacking the msg
        """
        op_code = packed_msg[:1]
        general_port = packed_msg[1:]
        if general_port.isnumeric():
            return [op_code, int(general_port)]
        return []

    @staticmethod
    def pack_file_list_msg(file_list):
        """
        pack the msg by the protocol
        :param file_list: list of files and directories in the disk on key
        :return: the msg packed in 1 string
        """
        op_code = "1"                            # the op code
        length = str(len(file_list)).zfill(8)    # the length of the file list
        msg = op_code + length + str(file_list)  # the message packed
        return msg

    @staticmethod
    def _unpack_file_list_msg(packed_msg):
        """
        unpacks the message by relevant protocol
        :param packed_msg: the message to unpack
        :return: the op code and elements after unpacking the msg
        """
        msg = []
        op_code = packed_msg[:1]
        length = packed_msg[1:9]
        if length.isnumeric():
            length = int(length)
            file_list = packed_msg[9:]
            print(file_list)
            msg = [op_code, length, file_list]
        return msg

    @staticmethod
    def pack_file_from_dok(file_path):
        """
        pack the msg by the protocol
        :param file_path: path of the file
        :return: the msg packed in 1 string
        """
        op_code = "2"                                       # the op code
        file_path_length = str(len(file_path)).zfill(2)     # the length of the path
        file = open(file_path, 'rb')
        f = file.read()                                     # the file
        length = str(len(f))                                # the length of the file
        length_len = str(len(length))                       # the length og the length
        msg = op_code + file_path_length + file_path +\
            length_len + length + str(f)                    # the message packed
        return msg

    @staticmethod
    def _unpack_file_from_dok(packed_msg):
        """
        unpacks the message by relevant protocol
        :param packed_msg: the message to unpack
        :return: the op code and elements after unpacking the msg
        """
        msg = []
        op_code = packed_msg[:1]
        path_length = packed_msg[1:3]
        if path_length.isnumeric():
            path = packed_msg[3:3+int(path_length)]
            packed_msg = packed_msg[3+int(path_length):]
            length_len = packed_msg[0]
            if length_len.isnumeric():
                length = packed_msg[1:1+int(length_len)]
                if length.isnumeric():
                    file = packed_msg[1+int(length_len):]
                    msg = [op_code, int(path_length), path, int(length_len), int(length), file]
        return msg

    @staticmethod
    def pack_file_port_msg(file_server_port, path):
        """
        pack the msg by the protocol
        :param file_server_port:
        :return: the msg packed in 1 string
        """
        op_code = "3"                               # the op code
        msg = op_code + file_server_port.zfill(4) + path   # the message packed
        return msg

    @staticmethod
    def _unpack_file_port_msg(packed_msg):
        """
        unpacks the message by relevant protocol
        :param packed_msg: the message to unpack
        :return: the op code and elements after unpacking the msg
        """
        op_code = packed_msg[0]
        file_port = packed_msg[1:5]
        path = packed_msg[5:]
        msg = [op_code, file_port, packed_msg]
        return msg

    @staticmethod
    def pack_file_request(file_path):
        """
        pack the msg by the protocol
        :param file_path: path of the file
        :return: the msg packed in 1 string
        """
        op_code = "4"                           # the op code
        length = str(len(file_path)).zfill(2)   # length of the path
        msg = op_code + length + file_path      # the message packed
        return msg

    @staticmethod
    def _unpack_file_request(packed_msg):
        """
        unpacks the message by relevant protocol
        :param packed_msg: the message to unpack
        :return: the op code and elements after unpacking the msg
        """
        op_code = packed_msg[0]
        length = packed_msg[1:3]
        path = packed_msg[3:]
        msg = [op_code, length, path]
        return msg

    @staticmethod
    def pack_file_upload_request(file_path):
        """
        pack the msg by the protocol
        :param file_path: path of the file
        :return: the msg packed in 1 string
        """
        op_code = "5"                           # the op code
        length = str(len(file_path)).zfill(2)   # length of the path
        msg = op_code + length + file_path      # the message packed
        return msg

    @staticmethod
    def _unpack_file_upload_request(packed_msg):
        """
        unpacks the message by relevant protocol
        :param packed_msg: the message to unpack
        :return: the op code and elements after unpacking the msg
        """
        op_code = packed_msg[0]
        length = packed_msg[1:3]
        path = packed_msg[3:]
        msg = [op_code, length, path]
        return msg

    @staticmethod
    def pack_file_to_dok(file_path):
        """
        pack the msg by the protocol
        :param file_path: path of the file
        :return: the msg packed in 1 string
        """
        op_code = "6"                                       # the op code
        file_path_length = str(len(file_path)).zfill(2)     # the length of the path
        file = open(file_path, 'rb')
        f = file.read()                                     # the file
        length = str(len(f))                                # the length of the file
        length_len = str(len(length))                       # the length og the length
        msg = op_code + file_path_length + file_path + \
            length_len + length + str(f)                    # the message packed
        return msg

    @staticmethod
    def _unpack_file_to_dok(packed_msg):
        """
        unpacks the message by relevant protocol
        :param packed_msg: the message to unpack
        :return: the op code and elements after unpacking the msg
        """
        msg = []
        op_code = packed_msg[:1]
        path_length = packed_msg[1:3]
        if path_length.isnumeric():
            path = packed_msg[3:3 + int(path_length)]
            packed_msg = packed_msg[3 + int(path_length):]
            length_len = packed_msg[0]
            if length_len.isnumeric():
                length = packed_msg[1:1 + int(length_len)]
                if length.isnumeric():
                    file = packed_msg[1 + int(length_len):]
                    msg = [op_code, int(path_length), path, int(length_len), int(length), file]
        return msg

    @staticmethod
    def _unpack_new_computer(packed_msg):
        """
        unpacks the message by relevant protocol
        :param packed_msg: the message to unpack
        :return: the op code and elements after unpacking the msg
        """
        op_code = "8"
        return [op_code]

    @staticmethod
    def _unpack_disconnected_drive(packed_msg):
        """
        unpacks the message by relevant protocol
        :param packed_msg: the message to unpack
        :return: the op code and elements after unpacking the msg
        """
        op_code = "9"
        return [op_code]
