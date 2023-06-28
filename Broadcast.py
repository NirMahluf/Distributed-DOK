import socket
import os
from Protocol import Protocol


class Broadcast:

    @staticmethod
    def send(msg):
        """
        sends message to all computers in the network
        :param msg: the message to send
        """
        network = f"192.168.4."  # the network mask

        done = False
        while not done:

            for i in range(70, 100):
                # run over all ips in the network
                print(f'sending to {network}{i}')
                # send UDP message
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.sendto(msg.encode(), (f"{network}{i}", 1000))
                print("sent")
                sock.close()
            print("done")
            done = True

    @staticmethod
    def send_one(msg, ip):
        """
        send UDP message to just one ip address
        :param msg: the message to send
        :param ip: the ip to send to
        """
        print(f'sending to {ip}')
        # send UDP message
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(msg.encode(), (f"{ip}", 1000))
        print("sent")
        sock.close()
        print("done")

    @staticmethod
    def recv(q):
        """
        receive UDP message
        :param q: add the message to queue to handle
        """
        ip = ""
        conf = os.popen('ipconfig').read()
        conf_split = conf.split(" ")
        for i in conf_split:
            # getting hosts ip
            if i.startswith("192.168.4."):
                ip = i
                break

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(('', 1000))  # binding to the default address
        while True:
            try:
                # getting message by UDP
                msg, addr = s.recvfrom(5)
                msg_params = Protocol.unpack(msg.decode())
                if not addr[0] == ip[:-1]:
                    # if I'm not the sender
                    q.put((addr[0], msg_params))
            except Exception as e:
                print("Broadcast - recv", str(e))
