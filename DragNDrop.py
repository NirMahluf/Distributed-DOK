import wx
import threading


class MyFileDropTarget(wx.FileDropTarget):
    def __init__(self, window, file_queue):
        """Constructor"""
        wx.FileDropTarget.__init__(self)
        self.window = window
        self.my_queue = file_queue

    def OnDropFiles(self, x, y, filenames):
        """
        When files are dropped, write where they were dropped and then
        the file paths themselves
        """
        self.window.set_insertion_point_end()
        self.window.update_text("%d file(s) dropped:\n" %
                                (len(filenames)))
        print(filenames)
        for filepath in filenames:
            self.window.update_text(filepath + '\n\n')
            self.my_queue.put(filepath)
        return True


class DnDPanel(wx.Panel):
    def __init__(self, parent, file_q, instruction_text):
        """Constructor"""
        wx.Panel.__init__(self, parent=parent)
        self.instruction_text = instruction_text

        file_drop_target = MyFileDropTarget(self, file_q)
        lbl = wx.StaticText(self, label=self.instruction_text)
        self.fileTextCtrl = wx.TextCtrl(self,
                                        style=wx.TE_MULTILINE | wx.HSCROLL | wx.TE_READONLY)
        self.fileTextCtrl.SetDropTarget(file_drop_target)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(lbl, 0, wx.ALL, 5)
        sizer.Add(self.fileTextCtrl, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)

    def set_insertion_point_end(self):
        """
        Put insertion point at end of text control to prevent overwriting
        """
        self.fileTextCtrl.SetInsertionPointEnd()

    def update_text(self, text):
        """
        Write text to the text control
        """
        self.fileTextCtrl.WriteText(text)


class DnDFrame(wx.Frame):
    def __init__(self, download_file_q, upload_file_q, ip_by_drive):
        """Constructor"""
        wx.Frame.__init__(self, parent=None, title="DDOK")

        # create a notebook widget to hold the tabs
        self.notebook = wx.Notebook(self)
        self.ip_by_drive = ip_by_drive

        # create the first tab and add it to the notebook
        panel1 = DnDPanel(self.notebook, download_file_q, "Drag the wanted file from the Disk On Key:")
        self.notebook.AddPage(panel1, "Download")

        # create the second tab and add it to the notebook
        panel2 = DnDPanel(self.notebook, upload_file_q, "Drag the wanted file you want to upload to a Disk On Key:")
        self.notebook.AddPage(panel2, "Upload")

        list_tab = wx.Panel(self.notebook)
        self.notebook.AddPage(list_tab, "Drives")

        self.list_ctrl = wx.ListCtrl(list_tab, style=wx.LC_REPORT)

        self.list_ctrl.InsertColumn(0, "Drive")
        self.list_ctrl.InsertColumn(1, "ip")

        list_sizer = wx.BoxSizer(wx.VERTICAL)
        list_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        list_tab.SetSizer(list_sizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)

        self.Show()

        threading.Thread(target=self.change_drive_list).start()

    def change_drive_list(self):
        """
        add or remove drives from the list if needed
        :return:
        """
        length = 0
        while True:
            if len(self.ip_by_drive) > length:
                self.list_ctrl.InsertItem(0, f"{list(self.ip_by_drive.keys())[-1]}")
                self.list_ctrl.SetItem(0, 1, f"{self.ip_by_drive[list(self.ip_by_drive.keys())[-1]]}")
                length = len(self.ip_by_drive)
            elif len(self.ip_by_drive) < length:
                self.list_ctrl.DeleteAllItems()
                for drive in list(self.ip_by_drive.keys()):
                    self.list_ctrl.InsertItem(0, f"{drive}")
                    self.list_ctrl.SetItem(0, 1, f"{self.ip_by_drive[drive]}")
                length = len(self.ip_by_drive)
