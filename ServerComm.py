import socket
import select
import threading
from Security import Security
from Protocol import Protocol


class ServerComm:
    """
    class to represent server (communication)
    """

    def __init__(self, port, msg_q, path=None):
        """
        initialize the object and run main loop
        :param port: the port of the server
        :param msg_q: queue to pass messages to main for handling
        """
        self.server_socket = socket.socket()    # server's socket
        self.port = port                        # server's port
        self.msg_q = msg_q                      # queue for incoming messages
        self.open_clients = {}                  # all connected clients: soc => (ip, key)
        self.security = Security()              # security object
        self.waiting = {}                       # all clients waiting for key exchanges: soc => ip
        self.path = path

        self.main_flag = True                   # flag that keeps whether the server is still alive
        threading.Thread(target=self._main_loop).start()

    def _main_loop(self):
        """
        set the server, accept new clients, get messages,
        decrypt, unpack and send to main to handle
        """

        # set up the server
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(3)

        while self.main_flag:
            rlist, wlist, xlist = select.select([self.server_socket] + list(self.open_clients.keys()) +
                                                list(self.waiting.keys()), list(self.open_clients.keys()), [])
            for current_socket in rlist:
                # run through all sockets that sent messages
                if current_socket is self.server_socket:
                    # if new client connecting
                    client, addr = self.server_socket.accept()
                    print(f"{addr[0]} - connected")
                    self.waiting[client] = addr[0]
                elif current_socket in self.waiting.keys():
                    # if client waits for key exchange
                    temp_security = Security()
                    try:
                        # receive client's public key
                        length = int(current_socket.recv(2).decode())
                        given_key = int(current_socket.recv(length).decode())
                    except Exception as e:
                        print("ServerComm - _main_loop - 1 (key recv)", str(e))
                        self._disconnect_client(current_socket)
                    else:
                        # create public key
                        public_key = temp_security.create_public_key()
                        try:
                            # send public key
                            current_socket.send(str(len(str(public_key))).zfill(2).encode())
                            current_socket.send(str(public_key).encode())
                        except Exception as e:
                            print("ServerComm - _main_loop - 2 (key send)", str(e))
                            self._disconnect_client(current_socket)
                        else:
                            # set key and approve client
                            key = temp_security.set_key(given_key)
                            self._approve_client(current_socket, key)
                elif current_socket in self.open_clients.keys():
                    if self.path is None:
                        # if got a message from client
                        try:
                            # receive the message
                            length = int(current_socket.recv(10).decode())
                            enc_msg = current_socket.recv(length)
                        except Exception as e:
                            print("ServerComm - _main_loop - (general recv)", str(e))
                            self._disconnect_client(current_socket)
                        else:
                            # decrypt, unpack and add to queue
                            raw_msg = self.security.decrypt(enc_msg, key=self.open_clients[current_socket][1])
                            msg_params = Protocol.unpack(raw_msg)
                            if not msg_params == []:
                                self.msg_q.put((self.open_clients[current_socket][0], msg_params))
                    else:
                        print("woop wooppp")
                        while True:
                            try:
                                # get full message length
                                msg_length = int(current_socket.recv(10).decode())
                            except ValueError:
                                break
                            except Exception as e:
                                print("ClientComm - _main_loop - 3", str(e))
                                break
                            else:
                                print("amen")
                                try:
                                    # get full message
                                    msg = current_socket.recv(msg_length)
                                except Exception as e:
                                    print("ClientComm - _main_loop - 4", str(e))
                                    break
                                else:
                                    # if path in the list - handle as a file
                                    ar = bytearray()
                                    ar += msg
                                    # receive file to byte array
                                    while len(ar) != msg_length:
                                        new_length = msg_length - len(ar)
                                        try:
                                            msg = current_socket.recv(new_length)
                                        except Exception as e:
                                            print("ClientComm - _main_loop", str(e))
                                        ar += msg
                                    msg = ar
                                    # decrypt file
                                    print(self.path)
                                    dec_file = self.security.decrypt_file(msg, key=self.open_clients[current_socket][1])
                                    self.msg_q.put((self.open_clients[current_socket][0], ["6", dec_file, self.path,
                                                                                           self.port]))
                                    break

    def _approve_client(self, soc, key):
        """
        move client to open_clients
        :param soc: client's socket
        :param key: client's encryption key
        """
        if soc not in self.open_clients.keys():
            # add to open clients
            self.open_clients[soc] = (self.waiting[soc], key)
            self.msg_q.put((self.waiting[soc], ["7"]))
        if soc in self.waiting.keys():
            # remove from waiting dict
            del self.waiting[soc]

    def _socket_by_ip(self, ip):
        """
        finds the socket of a given ip
        :param ip: ip of the client
        :return: the client's socket
        """
        sock = None
        for soc in self.open_clients.keys():
            # run over the ip's in open_clients
            if self.open_clients[soc][0] == ip:
                sock = soc
                break
        return sock

    def send(self, ip, msg):
        """
        encrypts and sends the message following the protocol
        :param ip: the ip of the wanted client
        :param msg: the message to send to the client
        """
        soc = self._socket_by_ip(ip)
        # encrypt the message
        enc_msg = self.security.encrypt(msg, key=self.open_clients[soc][1])
        length = str(len(enc_msg)).zfill(10)
        try:
            # send length of total message and the message
            soc.send(length.encode())
            soc.send(enc_msg)
        except Exception as e:
            print("ClientComm - send - 1", str(e))

    def send_all(self, msg):
        print("sending alllllllll   " + msg)
        for soc in self.open_clients.keys():
            enc_msg = self.security.encrypt(msg, key=self.open_clients[soc][1])
            length = str(len(enc_msg)).zfill(10)

            try:
                # send length of total message and the message
                soc.send(length.encode())
                soc.send(enc_msg)
            except Exception as e:
                print("ClientComm - send_all - 1", str(e))

    def send_file(self, ip, file):
        """
        encrypts and sends the file
        :param ip: the ip of the wanted client
        :param file: path of the file
        """
        soc = self._socket_by_ip(ip)
        # encrypt the file
        enc_file = self.security.encrypt_file(file, key=self.open_clients[soc][1])
        len_file = str(len(enc_file)).zfill(10)
        try:
            # send length of total message and the message
            soc.send(len_file.encode())
            soc.send(enc_file)
        except Exception as e:
            print("ClientComm - send - 1", str(e))

    def _disconnect_client(self, soc):
        """
        disconnect given client
       :param soc: the client's socket
       """
        if soc in self.open_clients.keys():
            # remove from connected clients
            print(f"{self.open_clients[soc]} - disconnected")
            del self.open_clients[soc]
            soc.close()
        elif soc in self.waiting.keys():
            # remove from waiting for validation if is waiting
            print(f"{self.waiting[soc]} - disconnected")
            del self.waiting[soc]
            soc.close()

    def close(self):
        """
        close the server and stop main
        thread using main_flag
        """
        self.main_flag = False
        self.server_socket.close()
