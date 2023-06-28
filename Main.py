import win32api
import win32file
import win32ui
import threading
import queue
import os
import shutil
import subprocess
import wx
from FileMonitor import FileMonitor
from DragNDrop import DnDFrame
from ClientComm import ClientComm
from ServerComm import ServerComm
from Broadcast import Broadcast
from Protocol import Protocol


class Main:
    def __init__(self):
        # DOK side
        self.drive = None                       # the letter of the drive connected
        self.files_list = None                  # string represents the DOK content
        self.general_server = None              # the server that represents the DOK
        self.file_servers = {}                  # ip => ServerComm
        self.ports = []                         # ports of file servers taken
        self.file_editors = {}                  # file path => ip

        # no-DOK side
        self.general_clients = {}               # all the clients (for all DOKs): ip => ClientComm
        self.drive_by_ip = {}                   # dict of all drives: ip => drive
        self.ip_by_drive = {}                   # dict of all ip's: drive => ip
        self.download_file_q = queue.Queue()    # queue of all files to download
        self.upload_file_q = queue.Queue()      # queue of all files to upload
        self.file_name = []                     # list of all file names to download
        self.event_q = queue.Queue()            # queue of events
        self.monitoring = {}
        self.file_client = None
        self.upload_file_path = ""
        self.LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        # msg handling
        self.actions = {"0": self.handle_discover_msg, "1": self.handle_file_list_msg,
                        "2": self.handle_file_from_dok, "3": self.handle_file_port_msg,
                        "4": self.handle_file_request, "5": self.handle_file_upload_request,
                        "6": self.handle_file_to_dok, "7": self.send_files_list, "8": self.handle_new_computer,
                        "9": self.handle_disconnect_drive_msg, "10": self.upload_file}

        self.msg_q = queue.Queue()      # queue for message handling

        print("hello")
        threading.Thread(target=self.main).start()
        threading.Thread(target=self.main_logic).start()

    def main(self):
        """
        activates the graphics
        """
        app = wx.App(False)
        DnDFrame(self.download_file_q, self.upload_file_q, self.ip_by_drive)
        app.MainLoop()

    def main_logic(self):
        """
        loop for the logic of the program
        """
        # run the receive from broadcast and the waiting for DOK loops
        threading.Thread(target=Broadcast.recv, args=(self.msg_q,)).start()
        threading.Thread(target=self.get_connected_drive).start()
        Broadcast.send("8")     # message to all computer to inform new computer connected
        while True:
            if not self.msg_q.empty():
                # if message received
                msg = self.msg_q.get()  # getting incoming message's attributes
                ip, params = msg        # break the message to ip and other params
                self.actions[params[0]](ip, params)  # call the relevant action by op code
            if not self.download_file_q.empty():
                # if the user added a file to the download window
                full_path = self.download_file_q.get()
                if full_path[:2] in self.ip_by_drive.keys():
                    from_drive = full_path[:2]
                    path = full_path[2:]
                    wanted_ip = self.ip_by_drive[from_drive]
                    # handle file downloading
                    self.download_file(wanted_ip, path, full_path)
            if not self.upload_file_q.empty():
                full_path = self.upload_file_q.get()
                if full_path[:2] in self.ip_by_drive.keys():
                    from_drive = full_path[:2]
                    path = full_path[2:]
                    self.upload_file_path = full_path
                    wanted_ip = self.ip_by_drive[from_drive]
                    # handle file downloading
                    self.upload_file_request(wanted_ip, path)

    def get_connected_drive(self):
        """
        keep checking if there is a disk on
        key connected to the computer,
        and update the letter when there is.
        """
        connected = False   # if a drive is connected to the computer
        while not connected:
            # getting list of connected drive
            drive_list = win32api.GetLogicalDriveStrings()
            drive_list = drive_list.split("\x00")[0:-1]  # the last element is ""
            for letter in drive_list:
                # letters of all the drives connected
                if win32file.GetDriveType(letter) == \
                        win32file.DRIVE_REMOVABLE:  # check if the drive is of type removable
                    connected = True
                    self.drive = letter             # define the dok that connected
                    break
        print(self.drive)
        drive_to_define = self.drive
        self.files_list = self.wrapped_define_file_list(drive_to_define)    # choose wanted files to share
        self.general_server = ServerComm(2000, self.msg_q)   # open server for the connected drive
        Broadcast.send(Protocol.pack_discover_msg(2000))
        threading.Thread(target=self.handle_disconnect_drive).start()   # handle for when the drive will disconnect

    def wrapped_define_file_list(self, directory):
        """
        wrapped function for the _define_file_list
        :param directory: the DOK's drive letter
        :return: string that represents the content of the DOK
        """
        return self._define_file_list(directory, "")[1:-1]

    def _define_file_list(self, total_directory, current):
        """
        extracts the hierarchy of the DOK
        :param total_directory: the entire path of the current directory
        :param current: the string of the files so far
        :return: string that represents the content of the DOK
        """
        files_str = current + "<"   # represents the start of a folder
        ls = os.listdir(total_directory)
        for d in ls:
            # running over all files and directories in the current
            if d != "System Volume Information":
                joined = os.path.join(total_directory, d)
                if os.path.isdir(joined):
                    # if the path is another directory - dive in
                    files_str += f"{self._define_file_list(joined, d)}"
                else:
                    # if a regular file - add it to the string
                    files_str += d
                    files_str += "?"    # represents end of file
        files_str += ">"    # end of directory
        return files_str

    def handle_disconnect_drive(self):
        """
        get when the current disk on key disconnected
        """
        while True:
            # getting list of connected drive
            drive_list = win32api.GetLogicalDriveStrings()
            drive_list = drive_list.split("\x00")[0:-1]  # the last element is ""
            # letters of all the drives connected
            if self.drive not in drive_list:
                # if the drive no longer connected
                self.drive = None
                break
        self.general_server.close()
        Broadcast.send("9")     # send the message regarding the disconnection to the other users
        self.general_server = None
        threading.Thread(target=self.get_connected_drive).start()   # check for connected drive

    def handle_discover_msg(self, ip, params):
        """
        when new DOK connected to the network
        :param ip: ip of the sender
        :param params: relevant input for the function
        """
        drive_created = False

        for letter in self.LETTERS:
            # run over all letters of the alphabet to find letter
            # to define the drive for the new DOK
            drive_list = win32api.GetLogicalDriveStrings()
            drive_list = drive_list.split("\x00")[0:-1]  # the last element is ""
            letter_drive = letter + ":"
            letter_drive_value = letter_drive + "\\"
            if letter_drive_value not in drive_list:
                # if current letter not used yet
                letter_dir = f"C:\\{letter.lower()}"
                os.makedirs(letter_dir, exist_ok=True)  # create folder with the letter
                subprocess.run(['subst', letter_drive, letter_dir], capture_output=True)    # create the drive
                self.monitoring[letter_drive] = FileMonitor(f"C:\\{letter.lower()}", self.event_q)
                # inform the user
                text = f"new drive {letter_drive} connected\nfrom ip: {ip}"
                head = "New Drive Connected"
                threading.Thread(target=self.message_box, args=(text, head,)).start()
                # win32ui.MessageBox(f"new drive {letter_drive} connected\nfrom ip: {ip}", "New Drive Connected", 0)
                self.drive_by_ip[ip] = letter_drive
                self.ip_by_drive[letter_drive] = ip
                drive_created = True
                break

        if drive_created:
            # create a client and connect to the DOK's server
            self.general_clients[ip] = ClientComm(ip, params[1], self.msg_q, self.file_name)

    def check_edited(self):
        office_endings = ["docx", "xlsx", "doc", "pptx"]
        open_files = []
        while True:
            if not self.event_q.empty():
                change = self.event_q.get()
                change_status = change[1]
                file_path = change[0]
                # print(change)
                ending = "tmp"
                if "." in file_path:
                    ending = file_path.split(".")[-1]
                file_name = file_path.split("\\")[-1]
                if change_status == "edited" and not ending.endswith("tmp") and ending not in office_endings:
                    while True:
                        try:
                            with open(file_path, 'a') as f:
                                pass
                        except PermissionError:
                            # File is currently open and cannot be accessed
                            pass
                        else:
                            # the file is saved
                            print("non office file path: " + file_path)
                            # packed_msg = clientProtocol.pack_edited_file_msg(file_name)
                            # self.send_file(file_path, packed_msg)
                            self.upload_file_q.put(file_path)
                            break
                elif ending in office_endings and file_name.startswith("~$"):
                    if change_status == 'created':
                        open_files.append(file_path)
                    elif change_status == 'deleted' and file_path in open_files:
                        open_files.remove(file_path)
                        new_file_name = file_name[2:]
                        file_dirs = file_path.split("\\")
                        del file_dirs[-1]
                        file_dirs.append(new_file_name)
                        file_path = "\\".join(file_dirs)
                        print("office file path: " + file_path)
                        # packed_msg = clientProtocol.pack_edited_file_msg(new_file_name)
                        # self.send_file(file_path, packed_msg)
                        self.upload_file_q.put(file_path)

    def send_files_list(self, ip, params):
        """
        sends the file list to the client
        :param ip: ip of the client to send to
        :param params: relevant parameters for the function
        """
        self.general_server.send(ip, Protocol.pack_file_list_msg(self.files_list))

    def send_all_files_list(self):
        self.general_server.send_all(Protocol.pack_file_list_msg(self.files_list))

    def handle_file_list_msg(self, ip, params):
        """
        handle the receive of DOK's file list
        :param ip: ip of the sender
        :param params: relevant parameters for the function
        """
        heir = params[2]
        origin = self.drive_by_ip[ip]
        self.replicate_dok(origin, heir)  # call the function that imitates the DOK as in the computer
        print("done")

    def replicate_dok(self, origin, heir):
        """
        create empty files and folders so the
        drive seems exactly like the DOK
        :param origin: the root of the "files tree" to create
        :param heir: the string that represents the hierarchy
        """
        cur = ""
        sub_dir = ""
        count = 0
        for char in heir:
            # run over every character of the string
            if count == 0:
                # if not in a folder
                if char not in "?<>":
                    # Part of a file or a folder
                    cur += char
                if char == "?":
                    # Creating file
                    with open(os.path.join(origin, cur), "w"):
                        pass
                    cur = ""
                if char == "<":
                    # creating a folder
                    os.makedirs(os.path.join(origin, cur), exist_ok=True)
                    sub_dir = cur
                    cur = ""
                    count += 1  # count the depth level
            else:
                cur += char
                if char == "<":
                    # going into another folder
                    count += 1
                elif char == ">":
                    # getting out of a folder
                    count -= 1
                    if count == 0:
                        # if got entirely out of folder
                        self.replicate_dok(os.path.join(origin, sub_dir), cur[:-1])
                        sub_dir = ""
                        cur = ""

    def download_file(self, ip, path, full_path):
        """
        sends download request to the server
        :param ip: ip of the server
        :param path: path of wanted file to download
        :param full_path: the full path (drive included) of the file
        """
        self.general_clients[ip].send(Protocol.pack_file_request(path))
        self.file_name.append(full_path)

    def handle_file_from_dok(self, ip, params):
        """
        open the file from the dok
        :param ip: ip of the server
        :param params: relevant parameters for the function
        """
        full_path = params[1]
        try:
            # open the file received
            os.startfile(full_path)
        except OSError:
            # if there is no associated program to open the file
            text = "file has no associated program to it"
            head = "Can't Open File"
            threading.Thread(target=self.message_box, args=(text, head,)).start()
            # win32ui.MessageBox("file has no associated program to it", "Can't Open File", 0)

    def handle_new_computer(self, ip, params):
        """
        if new computer connected to network
        :param ip: ip of the new computer
        :param params: relevant parameters for the function
        """
        if self.drive is not None:
            # send the reveal message individually
            Broadcast.send_one(Protocol.pack_discover_msg(2000), ip)

    def handle_disconnect_drive_msg(self, ip, params):
        """
        handle the disconnection of a drive from the network
        :param ip: the ip of the sender
        :param params: relevant parameters for the function
        """
        if ip in self.drive_by_ip.keys():
            # if the drive existed
            drive = self.drive_by_ip[ip]
            letter_drive = drive[0].lower()
            # delete the drive
            self.monitoring[drive].monitor = False
            subprocess.run(['subst', f"{drive}", '/d'], capture_output=True)
            if os.path.exists(f"C:\\{letter_drive}"):
                # delete the folder that created for the drive
                shutil.rmtree(f"C:\\{letter_drive}")
            del self.drive_by_ip[ip]
            del self.ip_by_drive[drive]
            del self.monitoring[drive]
            del self.general_clients[ip]    # close the client

    def handle_file_request(self, ip, params):
        """
        handle file request from client
        :param ip: ip of the client
        :param params: relevant parameters for the function
        """
        path = params[2]
        full_path = self.drive + path[1:]
        file = open(full_path, 'rb')    # open the requested file
        f = file.read()
        if full_path not in self.file_editors.keys():
            self.file_editors[full_path] = ip
        self.general_server.send_file(ip, f)    # send the requested file

    def upload_file_request(self, ip, path):
        self.general_clients[ip].send(Protocol.pack_file_upload_request(path))

    def upload_file(self, ip, params):
        print("1")
        if self.file_client is not None:
            print("2")
            self.file_client.send_file(self.upload_file_path)
            self.upload_file_path = ""
            self.file_client = None

    def handle_file_port_msg(self, ip, params):
        port = params[1]
        path = params[2]
        # full_path = self.drive_by_ip[ip] + path
        self.file_client = ClientComm(ip, int(port), self.msg_q, [])

    def handle_file_upload_request(self, ip, params):
        path = params[2]
        full_path = self.drive + path
        server_port = 2030
        for port in range(2001, 2030):
            if port not in self.ports:
                self.file_servers[ip] = ServerComm(port, self.msg_q, path=full_path)
                self.ports.append(port)
                server_port = port
                break
        self.general_server.send(ip, Protocol.pack_file_port_msg(str(server_port), path))

    def handle_file_to_dok(self, ip, params):
        file = params[1]
        path = params[2]
        port = params[3]
        print("why yo doin this")
        # print(self.file_editors)
        # if self.file_editors[path] == ip:
        #     print(self.file_editors[path])
        # if path in self.file_editors.keys() and self.file_editors[path] == ip:
        w_file = open(path, 'wb')
        w_file.write(file)
        w_file.close()
        print("yoyoy")
        drive_to_define = self.drive
        self.files_list = self.wrapped_define_file_list(drive_to_define)
        self.send_all_files_list()
        # del self.file_editors[path]
        self.file_servers[ip].close()
        del self.file_servers[ip]
        self.ports.remove(port)

    @staticmethod
    def message_box(text, head):
        win32ui.MessageBox(text, head, 0)


if __name__ == "__main__":
    main = Main()
