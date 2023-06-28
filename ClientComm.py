import socket
import threading
from Security import Security
from Protocol import Protocol


class ClientComm:
    """
    class to represent client's communication object
    """

    def __init__(self, server_ip, port, msg_q, file_names):
        """
        initializing attributes and
        running _main_loop as thr
        :param server_ip: server's ip
        :param port: port of communication
        :param msg_q: deliver messages to main client program
        :param file_names: list of all files waiting to be received
        """
        self.socket = None           # communication object
        self.server_ip = server_ip   # server's ip
        self.port = port             # server's port
        self.msg_q = msg_q           # queue for message handling
        self.file_name = file_names  # list of all file paths waiting to be received
        self.crypto = Security()     # security object
        threading.Thread(target=self._main_loop, daemon=True).start()

    def _main_loop(self):
        """
        connecting to server, receiving all messages
        and files from server and transfer
        them to queue for handling
        """
        self.socket = socket.socket()
        print(self.server_ip, self.port)
        try:
            # connect to server
            self.socket.connect((self.server_ip, self.port))
        except Exception as e:
            print("ClientComm - _main_loop - 1", str(e))
        else:
            # creating keys
            public_key = self.crypto.create_public_key()
            given_key = None
            try:
                # changing the keys - sending the generated key
                self.socket.send(str(len(str(public_key))).zfill(2).encode())
                self.socket.send(str(public_key).encode())
                # receiving the generated key from server
                length = int(self.socket.recv(2).decode())
                given_key = int(self.socket.recv(length).decode())
            except Exception as e:
                print("ClientComm - _main_loop - 2", str(e))
                exit()
            # set the AES key
            self.crypto.set_key(given_key)
            self.msg_q.put((self.server_ip, ["10"]))
            print("walla")
            while True:
                try:
                    # get full message length
                    msg_length = int(self.socket.recv(10).decode())
                except ValueError:
                    break
                except Exception as e:
                    print("ClientComm - _main_loop - 3", str(e))
                    break
                else:
                    try:
                        # get full message
                        msg = self.socket.recv(msg_length)
                    except Exception as e:
                        print("ClientComm - _main_loop - 4", str(e))
                        break
                    else:
                        if len(self.file_name) > 0:
                            # if path in the list - handle as a file
                            ar = bytearray()
                            ar += msg
                            # receive file to byte array
                            while len(ar) != msg_length:
                                new_length = msg_length - len(ar)
                                try:
                                    msg = self.socket.recv(new_length)
                                except Exception as e:
                                    print("ClientComm - _main_loop", str(e))
                                ar += msg
                            msg = ar
                            # decrypt file
                            dec_file = self.crypto.decrypt_file(msg)
                            path = self.file_name[0]
                            # save file to the path given
                            w_file = open(path, 'wb')
                            self.file_name.remove(path)
                            w_file.write(dec_file)
                            w_file.close()
                            # send file path to main to handle
                            self.msg_q.put((self.server_ip, ["2", path]))
                        else:
                            # decrypt and unpack the message -> to main to handle
                            raw_msg = self.crypto.decrypt(msg)
                            msg_unpacked = Protocol.unpack(raw_msg)
                            if not msg_unpacked == []:
                                self.msg_q.put((self.server_ip, msg_unpacked))

    def send(self, msg):
        """
        encrypt and send the message
        :param msg: the raw message
        """
        # encrypt the message
        enc_msg = self.crypto.encrypt(msg)
        length = str(len(enc_msg)).zfill(10)
        try:
            # send length of total message and the message
            self.socket.send(length.encode())
            self.socket.send(enc_msg)
        except Exception as e:
            print("ClientComm - send - 1", str(e))

    def send_file(self, path):
        """
        encrypts and sends the file
        :param file: path of the file
        """
        print("send file - 1")
        file = open(path, 'rb')  # open the requested file
        f = file.read()
        # encrypt the file
        enc_file = self.crypto.encrypt_file(f)
        len_file = str(len(enc_file)).zfill(10)
        try:
            # send length of total message and the message
            self.socket.send(len_file.encode())
            self.socket.send(enc_file)
        except Exception as e:
            print("ClientComm - send - 1", str(e))

    def recv_file(self, path):
        """
        Whenever incoming file, receive it,
        decrypt and save it in the proper path.
        :param path: the path to save the file to.
        """
        try:
            # receive file's length + file's content
            len_file = int(self.socket.recv(10).encode())
            file = self.socket.recv(len_file)
        except Exception as e:
            print("ClientComm - recv_file: ", str(e))
        else:
            # decrypt file and save it to computer
            dec_file = self.crypto.decrypt_file(file)
            w_file = open(path, 'wb')
            w_file.write(dec_file)
            w_file.close()
