#--------------------------------------------------------------------------
# Software:     InVesalius - Software de Reconstrucao 3D de Imagens Medicas
# Copyright:    (C) 2001  Centro de Pesquisas Renato Archer
# Homepage:     http://www.softwarepublico.gov.br
# Contact:      invesalius@cti.gov.br
# License:      GNU - GPL 2 (LICENSE.txt/LICENCA.txt)
#--------------------------------------------------------------------------
#    Este programa e software livre; voce pode redistribui-lo e/ou
#    modifica-lo sob os termos da Licenca Publica Geral GNU, conforme
#    publicada pela Free Software Foundation; de acordo com a versao 2
#    da Licenca.
#
#    Este programa eh distribuido na expectativa de ser util, mas SEM
#    QUALQUER GARANTIA; sem mesmo a garantia implicita de
#    COMERCIALIZACAO ou de ADEQUACAO A QUALQUER PROPOSITO EM
#    PARTICULAR. Consulte a Licenca Publica Geral GNU para obter mais
#    detalhes.
#--------------------------------------------------------------------------
import wx
import wx.gizmos as gizmos
from wx.lib.pubsub import pub as Publisher
import wx.lib.splitter as spl
import constants as const

#import import_panel

class Panel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, pos=wx.Point(5, 5))#,
                          #size=wx.Size(280, 656))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(InnerPanel(self), 1, wx.EXPAND|wx.GROW|wx.ALL, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Layout()
        self.Update()
        self.SetAutoLayout(1)

class InnerPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, pos=wx.Point(5, 5))#,
                          #size=wx.Size(680, 656))

        self.patients = []
        self.first_image_selection = None
        self.last_image_selection = None
        self._init_ui()
        #self._bind_events()
        #self._bind_pubsubevt()

    def _init_ui(self):
        splitter = spl.MultiSplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetOrientation(wx.VERTICAL)
        self.splitter = splitter

        panel = wx.Panel(self)
        self.btn_cancel = wx.Button(panel, wx.ID_CANCEL)
        self.btn_ok = wx.Button(panel, wx.ID_OK, _("Import"))

        btnsizer = wx.StdDialogButtonSizer()
        btnsizer.AddButton(self.btn_ok)
        btnsizer.AddButton(self.btn_cancel)
        btnsizer.Realize()

        self.combo_interval = wx.ComboBox(panel, -1, "", choices=const.IMPORT_INTERVAL,
                                     style=wx.CB_DROPDOWN|wx.CB_READONLY)
        self.combo_interval.SetSelection(0)

        inner_sizer = wx.BoxSizer(wx.HORIZONTAL)
        inner_sizer.AddSizer(btnsizer, 0, wx.LEFT|wx.TOP, 5)
        inner_sizer.Add(self.combo_interval, 0, wx.LEFT|wx.RIGHT|wx.TOP, 5)
        panel.SetSizer(inner_sizer)
        inner_sizer.Fit(panel)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(splitter, 20, wx.EXPAND)
        sizer.Add(panel, 1, wx.EXPAND|wx.LEFT, 90)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.text_panel = TextPanel(splitter)
        splitter.AppendWindow(self.text_panel, 250)

        #self.image_panel = ImagePanel(splitter)
        #splitter.AppendWindow(self.image_panel, 250)

        self.Layout()
        self.Update()
        self.SetAutoLayout(1)


class TextPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        self.__bind_events_wx()

    def __bind_pubsub_evt(self):
        #Publisher.subscribe(self.SelectSeries, 'Select series in import panel')
        pass

    def __bind_events_wx(self):
        #self.Bind(wx.EVT_SIZE, self.OnSize)

        tree = gizmos.TreeListCtrl(self, -1, style =
                                   wx.TR_DEFAULT_STYLE
                                   | wx.TR_HIDE_ROOT
                                   | wx.TR_ROW_LINES
                                   | wx.TR_COLUMN_LINES
                                   | wx.TR_FULL_ROW_HIGHLIGHT
                                   | wx.TR_SINGLE
                                  )


        tree.AddColumn(_("Selected"))
        tree.AddColumn(_("Name"))
        tree.AddColumn(_("Directory"))
        tree.AddColumn(_("Format"))
        tree.AddColumn(_("Size"))
        #tree.AddColumn(_("Study description"))
        #tree.AddColumn(_("Modality"))
        #tree.AddColumn(_("Date acquired"))
        #tree.AddColumn(_("# Images"))
        #tree.AddColumn(_("Institution"))
        #tree.AddColumn(_("Date of birth"))
        #tree.AddColumn(_("Accession Number"))
        #tree.AddColumn(_("Referring physician"))

        tree.SetMainColumn(0)        # the one with the tree in it...
        tree.SetColumnWidth(0, 280)  # Patient name
        tree.SetColumnWidth(1, 110)  # Patient ID
        tree.SetColumnWidth(2, 40)   # Age
        tree.SetColumnWidth(3, 60)   # Gender
        tree.SetColumnWidth(4, 160)  # Study description
        #tree.SetColumnWidth(5, 70)   # Modality
        #tree.SetColumnWidth(6, 200)  # Date acquired
        #tree.SetColumnWidth(7, 70)   # Number Images
        #tree.SetColumnWidth(8, 130)  # Institution
        #tree.SetColumnWidth(9, 100)  # Date of birth
        #tree.SetColumnWidth(10, 140) # Accession Number
        #tree.SetColumnWidth(11, 160) # Referring physician

        self.root = tree.AddRoot(_("InVesalius Database"))
        self.tree = tree

