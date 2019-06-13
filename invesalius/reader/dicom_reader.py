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
import os
import threading
import tempfile
import sys

from multiprocessing import cpu_count

import vtk
import vtkgdcm
import gdcm
from wx.lib.pubsub import pub as Publisher

import invesalius.constants as const
import invesalius.reader.dicom as dicom
import invesalius.reader.dicom_grouper as dicom_grouper
import invesalius.session as session
import glob
import invesalius.utils as utils

from invesalius import inv_paths
from invesalius.data import imagedata_utils

import plistlib

if sys.platform == 'win32':
    try:
        import win32api
        _has_win32api = True
    except ImportError:
        _has_win32api = False
else:
    _has_win32api = False

def ReadDicomGroup(dir_):

    patient_group = GetDicomGroups(dir_)
    if len(patient_group) > 0:
        filelist, dicom, zspacing = SelectLargerDicomGroup(patient_group)
        filelist = SortFiles(filelist, dicom)
        size = dicom.image.size
        bits = dicom.image.bits_allocad

        imagedata = CreateImageData(filelist, zspacing, size, bits)
        session.Session().project_status = const.NEW_PROJECT
        return imagedata, dicom
    else:
        return False


def SelectLargerDicomGroup(patient_group):
    maxslices = 0
    for patient in patient_group:
        group_list = patient.GetGroups()
        for group in group_list:
            if group.nslices > maxslices:
                maxslices = group.nslices
                larger_group = group

    return larger_group

def SortFiles(filelist, dicom):
    # Sort slices
    # FIXME: Coronal Crash. necessary verify
    if (dicom.image.orientation_label != "CORONAL"):
        ##Organize reversed image
        sorter = gdcm.IPPSorter()
        sorter.SetComputeZSpacing(True)
        sorter.SetZSpacingTolerance(1e-10)
        sorter.Sort(filelist)

        #Getting organized image
        filelist = sorter.GetFilenames()

    return filelist

main_dict = {}
dict_file = {}

class LoadDicom:
    def __init__(self, grouper, filepath):
        self.grouper = grouper
        self.filepath = utils.decode(filepath, const.FS_ENCODE)
        self.run()

    def run(self):
        grouper = self.grouper
        reader = gdcm.ImageReader()
        if _has_win32api:
            try:
                reader.SetFileName(utils.encode(win32api.GetShortPathName(self.filepath),
                                                const.FS_ENCODE))
            except TypeError:
                reader.SetFileName(win32api.GetShortPathName(self.filepath))
        else:
            try:
                reader.SetFileName(utils.encode(self.filepath, const.FS_ENCODE))
            except TypeError:
                reader.SetFileName(self.filepath)
        if (reader.Read()):
            file = reader.GetFile()
            # Retrieve data set
            dataSet = file.GetDataSet()
            # Retrieve header
            header = file.GetHeader()
            stf = gdcm.StringFilter()
            stf.SetFile(file)

            field_dict = {}
            data_dict = {}

            #to take DICOM encoding
            tag = gdcm.Tag(0x0008, 0x0005)
            ds = reader.GetFile().GetDataSet()
            if ds.FindDataElement(tag):
                encoding_value = str(ds.GetDataElement(tag).GetValue()).split('\\')[0]
                
                if encoding_value.startswith("Loaded"):
                    encoding = "ISO_IR 100"
                else:
                    try:
                        encoding = const.DICOM_ENCODING_TO_PYTHON[encoding_value]
                    except KeyError:
                        encoding = 'ISO_IR 100'
            else:
                encoding = "ISO_IR 100"
    
            #----- dump all dicom tags and extract values -----------------
            pds = gdcm.PythonDataSet(ds)
            sf = gdcm.StringFilter()
            pds.Start()
            dic={}
            sf.SetFile(file)

            while(not pds.IsAtEnd()):
                res = sf.ToStringPair(pds.GetCurrent().GetTag())
                tag = str(pds.GetCurrent().GetTag())
               
                #split group and field 
                tag = tag.replace("(","")
                tag = tag.replace(")","")
                tag = tag.split(",")

                group = tag[0]
                field = tag[1]

                if not group in data_dict.keys():
                    data_dict[group] = {}
                    
                if not group in field_dict.keys():    
                    field_dict[group] = {}

                #to save values
                if not(utils.VerifyInvalidPListCharacter(res[1])):
                    data_dict[group][field] = utils.decode(res[1], encoding, 'namereplace')
                else:
                    data_dict[group][field] = "Invalid Character"
               
                #to save dicom destription tags
                field_dict[group][field] = res[0]

                pds.Next()

            # -------------- To Create DICOM Thumbnail -----------
            try:
                data = data_dict['0028']['1050']
                level = [float(value) for value in data.split('\\')][0]
                data = data_dict['0028']['1051']
                window =  [float(value) for value in data.split('\\')][0]
            except(KeyError, ValueError):
                level = None
                window = None

            if _has_win32api:
                thumbnail_path = imagedata_utils.create_dicom_thumbnails(win32api.GetShortPathName(self.filepath), window, level)
            else:
                thumbnail_path = imagedata_utils.create_dicom_thumbnails(self.filepath, window, level)

            #------ Verify the orientation --------------------------------

            img = reader.GetImage()
            direc_cosines = img.GetDirectionCosines()
            orientation = gdcm.Orientation()
            try:
                _type = orientation.GetType(tuple(direc_cosines))
            except TypeError:
                _type = orientation.GetType(direc_cosines)
            label = orientation.GetLabel(_type)

 
            # ----------   Refactory --------------------------------------
            data_dict['invesalius'] = {'orientation_label' : label}

            # -------------------------------------------------------------
            dict_file[self.filepath] = data_dict
            
            #----------  Verify is DICOMDir -------------------------------
            is_dicom_dir = 1
            try: 
                if (data_dict['0002']['0002'] != "1.2.840.10008.1.3.10"): #DICOMDIR
                    is_dicom_dir = 0
            except(KeyError):
                    is_dicom_dir = 0
                                        
            if not(is_dicom_dir):
                parser = dicom.Parser()
                parser.SetDataImage(dict_file[self.filepath], self.filepath, thumbnail_path)
                
                dcm = dicom.Dicom()
                dcm.SetParser(parser)
                grouper.AddFile(dcm)


def yGetDicomGroups(directory, recursive=True, gui=True):
    """
    Return all full paths to DICOM files inside given directory.
    """
    nfiles = 0
    # Find total number of files
    if recursive:
        for dirpath, dirnames, filenames in os.walk(directory):
            nfiles += len(filenames)
    else:
        dirpath, dirnames, filenames = os.walk(directory)
        nfiles = len(filenames)

    counter = 0
    grouper = dicom_grouper.DicomPatientGrouper() 

    if recursive:
        for dirpath, dirnames, filenames in os.walk(directory):
            for name in filenames:
                filepath = os.path.join(dirpath, name)
                counter += 1
                if gui:
                    yield (counter,nfiles)
                LoadDicom(grouper, filepath)
    else:
        dirpath, dirnames, filenames = os.walk(directory)
        for name in filenames:
            filepath = str(os.path.join(dirpath, name))
            counter += 1
            if gui:
                yield (counter,nfiles)

    yield grouper.GetPatientsGroups()


def GetDicomGroups(directory, recursive=True):
    return next(yGetDicomGroups(directory, recursive, gui=False))


class ProgressDicomReader:
    def __init__(self):
        Publisher.subscribe(self.CancelLoad, "Cancel DICOM load")

    def CancelLoad(self):
        self.running = False
        self.stoped = True

    def SetWindowEvent(self, frame):
        self.frame = frame          

    def SetDirectoryPath(self, path,recursive=True):
        self.running = True
        self.stoped = False
        self.GetDicomGroups(path,recursive)

    def UpdateLoadFileProgress(self,cont_progress):
        Publisher.sendMessage("Update dicom load", data=cont_progress)

    def EndLoadFile(self, patient_list):
        Publisher.sendMessage("End dicom load", patient_series=patient_list)

    def GetDicomGroups(self, path, recursive):

        if not const.VTK_WARNING:
            log_path = utils.encode(str(inv_paths.USER_LOG_DIR.joinpath('vtkoutput.txt')), const.FS_ENCODE)
            fow = vtk.vtkFileOutputWindow()
            fow.SetFileName(log_path)
            ow = vtk.vtkOutputWindow()
            ow.SetInstance(fow)

        y = yGetDicomGroups(path, recursive)
        for value_progress in y:
            if not self.running:
                break
            if isinstance(value_progress, tuple):
                self.UpdateLoadFileProgress(value_progress)
            else:
                self.EndLoadFile(value_progress)
        self.UpdateLoadFileProgress(None)

        #Is necessary in the case user cancel
        #the load, ensure that dicomdialog is closed
        if(self.stoped):
            self.UpdateLoadFileProgress(None)
            self.stoped = False   


