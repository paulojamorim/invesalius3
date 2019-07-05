#---------------------------------------------------------------------
# Software: InVesalius Software de Reconstrucao 3D de Imagens Medicas

# Copyright: (c) 2001  Centro de Pesquisas Renato Archer
# Homepage: http://www.softwarepublico.gov.br
# Contact:  invesalius@cenpra.gov.br
# License:  GNU - General Public License version 2 (LICENSE.txt/
#                                                         LICENCA.txt)
#
#    Este programa eh software livre; voce pode redistribui-lo e/ou
#    modifica-lo sob os termos da Licenca Publica Geral GNU, conforme
#    publicada pela Free Software Foundation; de acordo com a versao 2
#    da Licenca.
#
#    Este programa eh distribuido na expectativa de ser util, mas SEM
#    QUALQUER GARANTIA; sem mesmo a garantia implicita de
#    COMERCIALIZACAO ou de ADEQUACAO A QUALQUER PROPOSITO EM
#    PARTICULAR. Consulte a Licenca Publica Geral GNU para obter mais
#    detalhes.
#---------------------------------------------------------------------


# ---------------------------------------------------------
# PROBLEM 1
# There are times when there are lots of groups on dict, but
# each group contains only one slice (DICOM file).
# 
# Equipments / manufacturer:
# TODO
#
# Cases:
# TODO 0031, 0056, 1093
#
# What occurs in these cases:
# <dicom.image.number> and <dicom.acquisition.series_number>
# were swapped


# -----------------------------------------------------------
# PROBLEM 2
# Two slices (DICOM file) inside a group have the same
# position.
#
# Equipments / manufacturer:
# TODO
#
# Cases:
# TODO 0031, 0056, 1093
#
# What occurs in these cases:
# <dicom.image.number> and <dicom.acquisition.series_number>
# were swapped

import sys
import math
import gdcm
import numpy

from invesalius.utils import Singleton
from six import with_metaclass

if sys.platform == 'win32':
    try:
        import win32api
        _has_win32api = True
    except ImportError:
        _has_win32api = False
else:
    _has_win32api = False

import invesalius.utils as utils
import invesalius.constants as const
import invesalius.reader.dicom as dcm_parser

ORIENT_MAP = {"SAGITTAL":0, "CORONAL":1, "AXIAL":2, "OBLIQUE":2}

class DicomSorter(with_metaclass(Singleton, object)):

    def __init__(self): 
        """
            self.groups_dict is a dictionary:
            
            ex:

            {('patient_name'): -> patient
                {('patient_name', 'study id', 'serie number', 'orientation label'): -> serie
                    [{'tag group':{'tag':'value', 'tag':'value'}.., 
                     {'tag group':{'tag':'value', 'tag':'value'}..}..]..}..}
        """
        
        self.groups_dict = {}


    def __GetItem(self, items, dcm_path):
        item = [group for group in items\
                if group['invesalius']['dicom_path'] == dcm_path]
        if item:
            return item[0] 
        else:
            return None

    def GetDicomPaths(self, serie):
        for patient in self.groups_dict.keys():
            if serie in self.groups_dict[patient].keys():
                dcm_paths = [dcm['invesalius']['dicom_path'] for dcm in\
                        self.groups_dict[patient][serie]]
                return dcm_paths
        return None

    def CalculateZSpacing(self):
        """
        Calculate z spacing based on slice distance.
        Call this method after read all DICOM slices.
        """

        for patient in self.groups_dict.keys():
            for serie in self.groups_dict[patient].keys():
                
                orientation_axis = ORIENT_MAP[serie[-1]]

                previous_pos = None
                acum_slices_dif = 0
                diferences = []

                if len(self.groups_dict[patient][serie]) > 1:
                    for _slice in self.groups_dict[patient][serie]:
                        parser = dcm_parser.Parser()
                        parser.SetData(_slice)
                       
                        img_pos = parser.GetImagePosition()
                       
                        if img_pos:
                            pos = img_pos[orientation_axis]
                            if not(previous_pos):
                                previous_pos = pos
                            else:
                                dif = round(math.fabs(pos - previous_pos), 2)
                                diferences.append(dif)
                                acum_slices_dif += dif
                                previous_pos = pos
                   
                    if len(self.groups_dict[patient][serie]) > 1:
                        zspacing = round(acum_slices_dif/(len(\
                            self.groups_dict[patient][serie]) - 1), 2)
                else:
                    zspacing = 1
                    
                #verify if all slices distances are equal
                diferences = numpy.unique(diferences)
                
                if diferences.shape[0] > 1:
                    #have diferences
                    slice_dif = True
                else:
                    slice_dif = False
             
                for i in range(len(self.groups_dict[patient][serie])):
                    
                    slice_ = self.groups_dict[patient][serie][i]

                    slice_['invesalius']['slices_dif_distance'] = slice_dif
                    slice_['invesalius']['z_spacing'] = zspacing
                    
                    parser = dcm_parser.Parser()
                    parser.SetData(_slice)
                    
                    if zspacing != parser.GetImageSpacingXYZByInVesalius()[2]:
                        slice_['invesalius']['thinckness_equal_zspacing'] = False
                    else:
                        slice_['invesalius']['thinckness_equal_zspacing'] = True

                    #update dictionary
                    #ARRUMAR!!!
                    self.groups_dict[patient][serie][i] = slice_


    def Add(self, item):
       
        dicom = dcm_parser.Parser()
        dicom.SetData(item)

        patient_name = dicom.GetPatientName()
        study_id = dicom.GetStudyID()
        serie_number = dicom.GetSerieNumber()
        orientation_label = dicom.GetOrientationLabelByInVesalius()

        series_key = (patient_name, study_id, serie_number,
                     orientation_label)#, index)

        if patient_name not in self.groups_dict.keys():
            self.groups_dict[patient_name] = {}

        if series_key not in self.groups_dict[patient_name].keys():
            self.groups_dict[patient_name][series_key] = []
        
        self.groups_dict[patient_name][series_key].append(item)


    def GetData(self):
        return self.groups_dict

    def Sort(self):
        """
        Sort DICOM file order into each serie.
        Call after add all slices.
        """
        for patient in self.groups_dict.keys():

            for serie in self.groups_dict[patient].keys():
        
                items = self.groups_dict[patient][serie]

                #get all dicom patches from dictionary
                dcm_paths = [i['invesalius']['dicom_path'] for i in items]
            
                parser = dcm_parser.Parser()
                parser.SetData(items[0])

                orientation_axis = ORIENT_MAP[serie[-1]]

                if parser.GetManufacturerName() == "Koning":
                    sorted_files = sorted(items, key=lambda items:\
                            utils.encode(items['invesalius']['dicom_path'], const.FS_ENCODE))
                else:

                    if orientation_axis != ORIENT_MAP["CORONAL"]:
                        
                        sorter = gdcm.IPPSorter()
                        sorter.SetComputeZSpacing(True)
                        sorter.SetZSpacingTolerance(1e-10)
                        sorter.Sort(dcm_paths)
                        
                        dcm_paths = sorter.GetFilenames()

                        if dcm_paths:
                            sorted_items = []
                        
                            for dcm in dcm_paths:
                               sorted_items.append(self.__GetItem(items, dcm))
                            
                            self.groups_dict[patient][serie] = sorted_items


                    else:
                        sorted_files = sorted(items, key=lambda items:\
                                items['0020']['0032'].replace(",", ".").split('\\')[0])
                        
                        self.groups_dict[patient][serie] = sorted_files



    def GetNumberOfSlicesByPatient(self, patient):
        n = 0
        for serie in self.groups_dict[patient].keys():
            n += len(self.groups_dict[patient][serie])
        return n

    #def GetNumberOfSlicesBySerie(self, patient, serie):
    #    n = len(self.groups_dict[patient][serie])
    #    return n

    def GetNumberOfSlicesBySerie(self, serie):
        for patient in self.groups_dict.keys():
            if serie in self.groups_dict[patient].keys():
                return len(self.groups_dict[patient][serie])
        return None
        
        n = len(self.groups_dict[patient][serie])
        return n


    def GetSerie(self, serie):
        for patient in self.groups_dict.keys():
            if serie in self.groups_dict[patient].keys():
                return self.groups_dict[patient][serie]
        return None
        
        #n = len(self.groups_dict[patient][serie])
        #return n


    def GetSeriesFromPatient(self, patient):
        return self.groups_dict[patient]


    def KeyIsPatientOrSerie(self, key):
        """
        Idenfity if key is from patient or a specific serie.
        """
        if key in self.groups_dict.keys():
            return const.PATIENT_GROUP
        else:
            for patient in self.groups_dict.keys():
                if key in self.groups_dict[patient].keys():
                    return const.SERIE_GROUP
        return None


    def CleanData(self):
        pass
















#------------------------------------------------------------------------------------------------

#------------------------------------------------------------------------------------------------

#------------------------------------------------------------------------------------------------

#------------------------------------------------------------------------------------------------


class DicomGroup:

    general_index = -1
    def __init__(self):
        DicomGroup.general_index += 1
        self.index = DicomGroup.general_index
        # key:
        # (dicom.patient.name, dicom.acquisition.id_study,
        #  dicom.acquisition.series_number,
        #  dicom.image.orientation_label, index)
        self.key = ()
        self.title = ""
        self.slices_dict = {} # slice_position: Dicom.dicom
        # IDEA (13/10): Represent internally as dictionary,
        # externally as list
        self.nslices = 0
        self.zspacing = 1
        self.dicom = None
        
    def AddSlice(self, dicom):
        if not self.dicom:
            self.dicom = dicom

        pos = tuple(dicom.image.position)

        #Case to test: \other\higroma
        #condition created, if any dicom with the same
        #position, but 3D, leaving the same series.
        if not "DERIVED" in dicom.image.type:
            #if any dicom with the same position
            if pos not in self.slices_dict.keys():
                self.slices_dict[pos] = dicom
                self.nslices += dicom.image.number_of_frames
                return True
            else:
                return False
        else:
            self.slices_dict[dicom.image.number] = dicom
            self.nslices += dicom.image.number_of_frames
            return True

    def GetList(self):
        # Should be called when user selects this group
        # This list will be used to create the vtkImageData
        # (interpolated)
        return self.slices_dict.values()

    def GetFilenameList(self):
        # Should be called when user selects this group
        # This list will be used to create the vtkImageData
        # (interpolated)
        if _has_win32api:
            filelist = [win32api.GetShortPathName(dicom.image.file)
                        for dicom in
                        self.slices_dict.values()]
        else:
            filelist = [dicom.image.file for dicom in
                        self.slices_dict.values()]
       
        # Sort slices using GDCM
        if (self.dicom.image.orientation_label != "CORONAL"):
            #Organize reversed image
            sorter = gdcm.IPPSorter()
            sorter.SetComputeZSpacing(True)
            sorter.SetZSpacingTolerance(1e-10)
            try:
                sorter.Sort([utils.encode(i, const.FS_ENCODE) for i in filelist])
            except TypeError:
                sorter.Sort(filelist)
            filelist = sorter.GetFilenames()

        # for breast-CT of koning manufacturing (KBCT)
        if list(self.slices_dict.values())[0].parser.GetManufacturerName() == "Koning":
            filelist.sort()
        
        return filelist

    def GetHandSortedList(self):
        # This will be used to fix problem 1, after merging
        # single DicomGroups of same study_id and orientation
        list_ = list(self.slices_dict.values())
        dicom = list_[0]
        axis = ORIENT_MAP[dicom.image.orientation_label]
        #list_ = sorted(list_, key = lambda dicom:dicom.image.position[axis])
        list_ = sorted(list_, key = lambda dicom:dicom.image.number)
        return list_

    def UpdateZSpacing(self):
        list_ = self.GetHandSortedList()
        
        if (len(list_) > 1):
            dicom = list_[0]
            axis = ORIENT_MAP[dicom.image.orientation_label]
            p1 = dicom.image.position[axis]
            
            dicom = list_[1]
            p2 = dicom.image.position[axis]
            
            self.zspacing = abs(p1 - p2)
        else:
            self.zspacing = 1

    def GetDicomSample(self):
        size = len(self.slices_dict)
        dicom = self.GetHandSortedList()[size//2]
        return dicom
            











class PatientGroup:
    def __init__(self):
        # key:
        # (dicom.patient.name, dicom.patient.id)
        self.key = ()
        self.groups_dict = {} # group_key: DicomGroup
        self.nslices = 0
        self.ngroups = 0
        self.dicom = None

    def AddFile(self, dicom, index=0):
        # Given general DICOM information, we group slices according
        # to main series information (group_key)

        # WARN: This was defined after years of experience
        # (2003-2009), so THINK TWICE before changing group_key

        # Problem 2 is being fixed by the way this method is
        # implemented, dinamically during new dicom's addition
        group_key = (dicom.patient.name,
                     dicom.acquisition.id_study,
                     dicom.acquisition.serie_number,
                     dicom.image.orientation_label,
                     index) # This will be used to deal with Problem 2
        if not self.dicom:
            self.dicom = dicom

        self.nslices += 1
        # Does this group exist? Best case ;)
        if group_key not in self.groups_dict.keys():
            group = DicomGroup()
            group.key = group_key
            group.title = dicom.acquisition.series_description
            group.AddSlice(dicom)
            self.ngroups += 1
            self.groups_dict[group_key] = group
        # Group exists... Lets try to add slice
        else:
            group = self.groups_dict[group_key]
            slice_added =  group.AddSlice(dicom)
            if not slice_added:
                # If we're here, then Problem 2 occured
                # TODO: Optimize recursion 
                self.AddFile(dicom, index+1)
                
            #Getting the spacing in the Z axis
            group.UpdateZSpacing()
                    

    def GetGroups(self):
        glist = self.groups_dict.values()
        glist = sorted(glist, key = lambda group:group.title,
                reverse=True)
        return glist

    def GetDicomSample(self):
        return self.dicom


class DicomPatientGrouper:
    # read file, check if it is dicom...
    # dicom = dicom.Dicom
    # grouper = DicomPatientGrouper()
    # grouper.AddFile(dicom)
    # ... (repeat to all files on folder)
    # grouper.Update()
    # groups = GetPatientGroups()
    
    def __init__(self):
        self.patients_dict = {}
    
    def AddFile(self, dicom):
        patient_key = (dicom.patient.name,
                       dicom.patient.id)
    
        # Does this patient exist?
        if patient_key not in self.patients_dict.keys():
            patient = PatientGroup()
            patient.key = patient_key
            patient.AddFile(dicom)
            self.patients_dict[patient_key] = patient
        # Patient exists... Lets add group to it
        else:
            patient = self.patients_dict[patient_key]
            patient.AddFile(dicom)
       
    #def Update(self):
    #    for patient in self.patients_dict.values():
    #        patient.Update()
    
    def GetPatientsGroups(self):
        """
        How to use:
        patient_list = grouper.GetPatientsGroups()
        for patient in patient_list:
            group_list = patient.GetGroups()
            for group in group_list:
                group.GetList()
                # :) you've got a list of dicom.Dicom
                # of the same series
        """
        plist = self.patients_dict.values()
        plist = sorted(plist, key = lambda patient:patient.key[0])
        return plist

