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

import invesalius.constants as const
import invesalius.gui.dialogs as dlg
import invesalius.gui.dicom_preview_panel as dpp
import invesalius.reader.dicom_grouper as dcm_grouper
import invesalius.reader.dicom as dcm_parser

myEVT_SELECT_SERIE = wx.NewEventType()
EVT_SELECT_SERIE = wx.PyEventBinder(myEVT_SELECT_SERIE, 1)

myEVT_SELECT_SLICE = wx.NewEventType()
EVT_SELECT_SLICE = wx.PyEventBinder(myEVT_SELECT_SLICE, 1)

myEVT_SELECT_PATIENT = wx.NewEventType()
EVT_SELECT_PATIENT = wx.PyEventBinder(myEVT_SELECT_PATIENT, 1)

myEVT_SELECT_SERIE_TEXT = wx.NewEventType()
EVT_SELECT_SERIE_TEXT = wx.PyEventBinder(myEVT_SELECT_SERIE_TEXT, 1)

class SelectEvent(wx.PyCommandEvent):
    def __init__(self , evtType, id):
        super(SelectEvent, self).__init__(evtType, id)

    def GetSelectID(self):
        return self.SelectedID

    def SetSelectedID(self, id):
        self.SelectedID = id

    def GetItemData(self):
        return self.data

    def SetItemData(self, data):
        self.data = data


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


# Inner fold panel
class InnerPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, pos=wx.Point(5, 5))#,
                          #size=wx.Size(680, 656))

        self.dicom_groups = []
        self.first_image_selection = None
        self.last_image_selection = None
        self._init_ui()
        self._bind_events()
        self._bind_pubsubevt()

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
        inner_sizer.Add(btnsizer, 0, wx.LEFT|wx.TOP, 5)
        inner_sizer.Add(self.combo_interval, 0, wx.LEFT|wx.RIGHT|wx.TOP, 5)
        panel.SetSizer(inner_sizer)
        inner_sizer.Fit(panel)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(splitter, 20, wx.EXPAND)
        sizer.Add(panel, 0, wx.EXPAND|wx.LEFT, 90)

        self.text_panel = TextPanel(splitter)
        splitter.AppendWindow(self.text_panel, 250)

        self.image_panel = ImagePanel(splitter)
        splitter.AppendWindow(self.image_panel, 250)
        
        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Layout()
        self.Update()
        self.SetAutoLayout(1)

    def _bind_pubsubevt(self):
        Publisher.subscribe(self.ShowDicomPreview, "Load import panel")
        Publisher.subscribe(self.GetSelectedImages ,"Selected Import Images")  

    def GetSelectedImages(self, selection):
        self.first_image_selection = selection[0]
        self.last_image_selection = selection[1]
        
    def _bind_events(self):
        self.Bind(EVT_SELECT_SERIE, self.OnSelectSerie)
        self.Bind(EVT_SELECT_SLICE, self.OnSelectSlice)
        self.Bind(EVT_SELECT_PATIENT, self.OnSelectPatient)
        self.btn_ok.Bind(wx.EVT_BUTTON, self.OnClickOk)
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.OnClickCancel)
        self.text_panel.Bind(EVT_SELECT_SERIE_TEXT, self.OnDblClickTextPanel)

    def ShowDicomPreview(self, dicom_groups):
        #self.dicom_groups.extend(dicom_groups)
        self.dicom_groups = dicom_groups

        self.text_panel.Populate(dicom_groups)

    def OnSelectSerie(self, evt):
        patient_id = evt.GetSelectID()
        self.text_panel.SelectSerie(evt.GetSelectID())
    
        for patient in self.dicom_groups.keys():
            for serie in self.dicom_groups[patient].keys():
                if patient_id == serie:
                    self.image_panel.SetSerie(serie)

    def OnSelectSlice(self, evt):
        pass

    def OnSelectPatient(self, evt):
        pass

    def OnDblClickTextPanel(self, evt):
        group = evt.GetItemData()
        self.LoadDicom(group)

    def OnClickOk(self, evt):
        group = self.text_panel.GetSelection()
        if group:
            self.LoadDicom(group)

    def OnClickCancel(self, evt):
        Publisher.sendMessage("Cancel DICOM load")

    def LoadDicom(self, group_key):
        interval = self.combo_interval.GetSelection()
        
        #if not isinstance(group, dcm.DicomGroup):
        #    group = max(group.GetGroups(), key=lambda g: g.nslices)
        
        dcm_sorter = dcm_grouper.DicomSorter()
        
        if dcm_sorter.KeyIsPatientOrSerie(group_key) == const.PATIENT_GROUP:
            serie_to_open = dcm_sorter.GetSerie(list(dcm_sorter.GetSeriesFromPatient(group_key).keys())[0])
        else:
            serie_to_open = dcm_sorter.GetSerie(group_key)
        
        slice_amont = len(serie_to_open)
        if (self.first_image_selection != None) and (self.first_image_selection != self.last_image_selection):
            slice_amont = (self.last_image_selection) - self.first_image_selection
            slice_amont += 1
            if slice_amont == 0:
                slice_amont = len(serie_to_open)

        nslices_result = slice_amont / (interval + 1)
        if (nslices_result > 1):
            Publisher.sendMessage('Open DICOM group', group=serie_to_open,
                                  interval=interval,
                                  file_range=(self.first_image_selection, self.last_image_selection))
        else:
            dlg.MissingFilesForReconstruction()

class TextPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self._selected_by_user = True
        self.idserie_treeitem = {}
        self.treeitem_idpatient = {}

        self.__init_gui()
        self.__bind_events_wx()
        self.__bind_pubsub_evt()

    def __bind_pubsub_evt(self):
        Publisher.subscribe(self.SelectSeries, 'Select series in import panel')

    def __bind_events_wx(self):
        self.Bind(wx.EVT_SIZE, self.OnSize)

    def __init_gui(self):
        tree = gizmos.TreeListCtrl(self, -1, style =
                                   wx.TR_DEFAULT_STYLE
                                   | wx.TR_HIDE_ROOT
                                   | wx.TR_ROW_LINES
                                   #  | wx.TR_COLUMN_LINES
                                   | wx.TR_FULL_ROW_HIGHLIGHT
                                   | wx.TR_SINGLE
                                  )


        tree.AddColumn(_("Patient name"))
        tree.AddColumn(_("Patient ID"))
        tree.AddColumn(_("Age"))
        tree.AddColumn(_("Gender"))
        tree.AddColumn(_("Study description"))
        tree.AddColumn(_("Modality"))
        tree.AddColumn(_("Date acquired"))
        tree.AddColumn(_("# Images"))
        tree.AddColumn(_("Institution"))
        tree.AddColumn(_("Date of birth"))
        tree.AddColumn(_("Accession Number"))
        tree.AddColumn(_("Referring physician"))

        tree.SetMainColumn(0)        # the one with the tree in it...
        tree.SetColumnWidth(0, 280)  # Patient name
        tree.SetColumnWidth(1, 110)  # Patient ID
        tree.SetColumnWidth(2, 40)   # Age
        tree.SetColumnWidth(3, 60)   # Gender
        tree.SetColumnWidth(4, 160)  # Study description
        tree.SetColumnWidth(5, 70)   # Modality
        tree.SetColumnWidth(6, 200)  # Date acquired
        tree.SetColumnWidth(7, 70)   # Number Images
        tree.SetColumnWidth(8, 130)  # Institution
        tree.SetColumnWidth(9, 100)  # Date of birth
        tree.SetColumnWidth(10, 140) # Accession Number
        tree.SetColumnWidth(11, 160) # Referring physician

        self.root = tree.AddRoot(_("InVesalius Database"))
        self.tree = tree

    def SelectSeries(self, group_index):
        pass

    def Populate(self, patient_list):
        tree = self.tree

        first = 0
        for patient in patient_list.keys():
            #if not isinstance(patient, dcm.PatientGroup):
            #    return None
            
            #get numbers of series
            nseries = len(patient_list[patient].keys())

            #get first serie from patient 
            first_serie = list(patient_list[patient].keys())[0]
            
            #get first slice from first serie
            first_dcm = patient_list[patient][first_serie]
            
            dcm = dcm_parser.Parser()
            dcm.SetData(first_dcm[0])

            title = patient + " (%d series)"%(nseries)

            date_time = "%s %s"%(dcm.GetAcquisitionDate(),
                                dcm.GetAcquisitionTime())

            parent = tree.AppendItem(self.root, title)

            if not first:
                parent_select = parent
                first += 1

            tree.SetItemPyData(parent, patient)
            tree.SetItemText(parent, "%s" % dcm.GetPatientID(), 1)
            tree.SetItemText(parent, "%s" % dcm.GetPatientAge(), 2)
            tree.SetItemText(parent, "%s" % dcm.GetPatientGender(), 3)
            tree.SetItemText(parent, "%s" % dcm.GetStudyDescription(), 4)
            #tree.SetItemText(parent, "%s" % dcm.GetAcquisitionModality(), 5)
            #tree.SetItemText(parent, "%s" % date_time, 6)
            tree.SetItemText(parent, "%s" % dcm_grouper.DicomSorter().GetNumberOfSlicesByPatient(patient), 7)#patient.nslices, 7)
            tree.SetItemText(parent, "%s" % dcm.GetInstitutionName(), 8)
            tree.SetItemText(parent, "%s" % dcm.GetPatientBirthDate(), 9)
            tree.SetItemText(parent, "%s" % dcm.GetAccessionNumber(), 10)
            tree.SetItemText(parent, "%s" % dcm.GetPhysicianReferringName(), 11)

            group_list = patient_list[patient].keys()
            for n, serie in enumerate(group_list):
                
                #dicom = group.GetDicomSample()

                child = tree.AppendItem(parent, dcm.GetSeriesDescription())
                tree.SetItemPyData(child, serie)

                tree.SetItemText(child, "%s" % dcm.GetSeriesDescription(), 0)
                tree.SetItemText(child, "%s" % dcm.GetProtocolName(), 4)
                tree.SetItemText(child, "%s" % dcm.GetAcquisitionModality(), 5)
                tree.SetItemText(child, "%s" % date_time, 6)
                tree.SetItemText(child, "%s" % dcm_grouper.DicomSorter().GetNumberOfSlicesBySerie(serie), 7)

                #self.idserie_treeitem[(dcm.GetPatientID(),
                #                       dcm.GetSerieNumber())] = child


                self.idserie_treeitem[(serie)] = child


        tree.Expand(self.root)
        tree.SelectItem(parent_select)
        tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate)
        tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged)

    def OnSelChanged(self, evt):
        item = self.tree.GetSelection()
        if self._selected_by_user:
            #take clicked group of the treecrl
            group = self.tree.GetItemPyData(item)
            
            #group type is to verify if click is on patient or serie group of the treecrl
            group_type = dcm_grouper.DicomSorter().KeyIsPatientOrSerie(group)

            if group_type == const.SERIE_GROUP:
                Publisher.sendMessage('Load group into import panel',
                                            group=group)
            elif group_type == const.PATIENT_GROUP:
                
                #id = group.GetDicomSample().patient.id
                
                my_evt = SelectEvent(myEVT_SELECT_PATIENT, self.GetId())
                #my_evt.SetSelectedID(id)
                my_evt.SetSelectedID(group)
                
                self.GetEventHandler().ProcessEvent(my_evt)

                Publisher.sendMessage('Load patient into import panel',
                                            patient=group)
        else:
            parent_id = self.tree.GetItemParent(item)
            self.tree.Expand(parent_id)
        evt.Skip()

    def OnActivate(self, evt):
        item = evt.GetItem()
        group = self.tree.GetItemPyData(item)
        my_evt = SelectEvent(myEVT_SELECT_SERIE_TEXT, self.GetId()) 
        my_evt.SetItemData(group)
        self.GetEventHandler().ProcessEvent(my_evt)

    def OnSize(self, evt):
        self.tree.SetSize(self.GetSize())

    def SelectSerie(self, serie):
        self._selected_by_user = False
        item = self.idserie_treeitem[serie]
        self.tree.SelectItem(item)
        self._selected_by_user = True

    def GetSelection(self):
        """Get selected item"""
        item = self.tree.GetSelection()
        group = self.tree.GetItemPyData(item)
        return group


class ImagePanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        self._init_ui()
        self._bind_events()

    def _init_ui(self):
        splitter = spl.MultiSplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetOrientation(wx.HORIZONTAL)
        self.splitter = splitter

        # TODO Rever isso
        #  splitter.ContainingSizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(splitter, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.text_panel = SeriesPanel(splitter)
        splitter.AppendWindow(self.text_panel, 600)

        self.image_panel = SlicePanel(splitter)
        splitter.AppendWindow(self.image_panel, 250)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Layout()
        self.Update()
        self.SetAutoLayout(1)

    def _bind_events(self):
        self.text_panel.Bind(EVT_SELECT_SERIE, self.OnSelectSerie)
        self.text_panel.Bind(EVT_SELECT_SLICE, self.OnSelectSlice)

    def OnSelectSerie(self, evt):
        print("SELF.ONSELECT_SERIE")
        evt.Skip()

    def OnSelectSlice(self, evt):
        print("ONSELECT_SLICE", evt.GetItemData())
        self.image_panel.dicom_preview.ShowSlice(evt.GetItemData())
        evt.Skip()

    def SetSerie(self, serie):
        self.image_panel.dicom_preview.SetDicomGroup(serie)


class SeriesPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        #self.SetBackgroundColour((0,0,0))

        self.serie_preview = dpp.DicomPreviewSeries(self)
        self.dicom_preview = dpp.DicomPreviewSlice(self)
        self.dicom_preview.Show(0)
        

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.serie_preview, 1, wx.EXPAND | wx.ALL, 5)
        self.sizer.Add(self.dicom_preview, 1, wx.EXPAND | wx.ALL, 5)
        self.sizer.Fit(self)

        self.SetSizer(self.sizer)

        self.Layout()
        self.Update()
        self.SetAutoLayout(1)

        self.__bind_evt()
        self._bind_gui_evt()

    def __bind_evt(self):
        Publisher.subscribe(self.ShowDicomSeries, 'Load dicom preview')
        Publisher.subscribe(self.SetDicomSeries, 'Load group into import panel')
        Publisher.subscribe(self.SetPatientSeries, 'Load patient into import panel')

    def _bind_gui_evt(self):
        self.serie_preview.Bind(dpp.EVT_CLICK_SERIE, self.OnSelectSerie)
        self.dicom_preview.Bind(dpp.EVT_CLICK_SLICE, self.OnSelectSlice)

    def SetDicomSeries(self, group):
        self.dicom_preview.SetDicomGroup(group)
        self.dicom_preview.Show(1)
        self.serie_preview.Show(0)
        self.sizer.Layout()
        self.Update()

    def GetSelectedImagesRange(self):
        return [self.dicom_preview.first_selected, self.dicom_preview_last_selection]

    def SetPatientSeries(self, patient):
        self.dicom_preview.Show(0)
        self.serie_preview.Show(1)

        self.serie_preview.SetPatientGroups(patient)
        self.dicom_preview.SetPatientGroups(patient)

        self.Update()

    def OnSelectSerie(self, evt):
        serie = evt.GetItemData()
        my_evt = SelectEvent(myEVT_SELECT_SERIE, self.GetId())
        my_evt.SetSelectedID(evt.GetSelectID())
        my_evt.SetItemData(evt.GetItemData())
        self.GetEventHandler().ProcessEvent(my_evt)
        self.dicom_preview.SetDicomGroup(serie)
        self.dicom_preview.Show(1)
        self.serie_preview.Show(0)
        self.sizer.Layout()
        self.Show()
        self.Update()

    def OnSelectSlice(self, evt):
        my_evt = SelectEvent(myEVT_SELECT_SLICE, self.GetId())
        my_evt.SetSelectedID(evt.GetSelectID())
        my_evt.SetItemData(evt.GetItemData())
        self.GetEventHandler().ProcessEvent(my_evt)

    def ShowDicomSeries(self, patient):
        #if isinstance(patient, dcm.PatientGroup):
        self.serie_preview.SetPatientGroups(patient)
        self.dicom_preview.SetPatientGroups(patient)


class SlicePanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        self.__init_gui()
        self.__bind_evt()

    def __bind_evt(self):
        Publisher.subscribe(self.ShowDicomSeries, 'Load dicom preview')
        Publisher.subscribe(self.SetDicomSeries, 'Load group into import panel')
        Publisher.subscribe(self.SetPatientSeries, 'Load patient into import panel')

    def __init_gui(self):
        self.SetBackgroundColour((255,255,255))
        self.dicom_preview = dpp.SingleImagePreview(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.dicom_preview, 1, wx.GROW|wx.EXPAND)
        sizer.Fit(self)
        self.SetSizer(sizer)
        self.Layout()
        self.Update()
        self.SetAutoLayout(1)
        self.sizer = sizer

    def SetPatientSeries(self, patient):
        #series = dcm_grouper.DicomSorter().GetSeriesFromPatient(patient)
        #group = series[list(series.keys())[0]]
        self.dicom_preview.SetDicomGroup(patient)
        self.sizer.Layout()
        self.Update()

    def SetDicomSeries(self, group):
        self.dicom_preview.SetDicomGroup(group)
        self.sizer.Layout()
        self.Update()

    def ShowDicomSeries(self, patient):
        #group = patient.GetGroups()[0]
        self.dicom_preview.SetDicomGroup(patient)
        self.sizer.Layout()
        self.Update()


