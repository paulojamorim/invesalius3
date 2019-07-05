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
import time
#import gdcm
import sys
import invesalius.utils as utils
import invesalius.constants as const
# In DICOM file format, if multiple values are present for the
# "Window Center" (Level) and "Window Width", both attributes
# shall have the same number of values and shall be considered as
# pairs. Multiple values indicate that multiple alternative views
# may be presented. In this Parser, by default, we only consider
# one pair per  time. This pair is determined by WL_PRESET
# constant or might be set by the user when calling GetWindowWidth
# and GetWindowLevel.


WL_PRESET = 0 # index of selected window and level tuple (if multiple)
WL_MULT = 0 # allow selection of multiple window and level tuples if 1

## dictionary to be used by module functions
#info = {}
## keys to be used to generate dictionary info
#INFO_KEYS = \
#['AcquisitionDate',
# 'AcquisitionGantryTilt',
# 'AcquisitionModality',
# 'AcquisitionNumber',
# 'AcquisionSequence',
# 'AcquisitionTime',
# 'EquipmentKVP',
# 'EquipmentInstitutionName',
# 'EquipmentManufacturer',
# 'EquipmentXRayTubeCurrent',
# 'ImageColumnOrientation',
# 'ImageConvolutionKernel',
# 'ImageDataType',
# 'ImageLocation',
# 'ImageNumber',
# 'ImagePixelSpacingX',
# 'ImagePixelSpacingY',
# 'ImagePosition',
# 'ImageRowOrientation',
# 'ImageSamplesPerPixel',
# 'ImageSeriesNumber',
# 'ImageThickness',
# 'ImageWindowLevel',
# 'ImageWindowWidth',
# 'PatientAge',
# 'PatientBirthDate',
# 'PatientGender',
# 'PatientName',
# 'PhysicianName',
# 'StudyID',
# 'StudyInstanceUID',
# 'StudyAdmittingDiagnosis',
# ]

class Parser():
    """
    Medical image parser. Used to parse medical image tags.
    It supports:
      - ACR-NEMA version 1 and 2
      - DICOM 3.0 (including JPEG-lossless and lossy-, RLE)
      - Papyrus V2 and V3 file headers
    GDCM was used to develop this class.

    How to use:
      >>> image = ivMedicalImageParser()
      >>> image.SetFileName("/home/usr/0.dcm")
      # then you might call method related to tag of interest
      >>> print image.GetImagePixelSpacing()
    """

    def __init__(self):
        self.filename = ""
        self.encoding = ""
        self.filepath = ""

    #def SetDataImage(self, data_image, filename, thumbnail_path):
    #    self.data_image = data_image
    #    self.filename = self.filepath = filename    
    #    self.thumbnail_path = thumbnail_path

    def SetData(self, data):
        self.data = data

    def GetData(self):
        return self.data

    def __format_time(self,value):
        sp1 = value.split(".")
        sp2 = value.split(":")

        if (len(sp1) ==  2) and (len(sp2) == 3):
            new_value = str(sp2[0]+sp2[1]+
                            str(int(float(sp2[2]))))
            data = time.strptime(new_value, "%H%M%S")
        elif (len(sp1) ==  2):
            data = time.gmtime(float(value))
        elif (len(sp1) >  2):
            data = time.strptime(value, "%H.%M.%S")
        elif(len(sp2) > 1):
            data = time.strptime(value, "%H:%M:%S")
        else:
            try:
                data = time.strptime(value, "%H%M%S")
            # If the time is not in a bad format only return it.
            except ValueError:
                return value
        return time.strftime("%H:%M:%S",data)

    def __format_date(self, value):

        sp1 = value.split(".")
        try:

            if (len(sp1) >  1):
                if (len(sp1[0]) <= 2):
                    data = time.strptime(value, "%D.%M.%Y")
                else:
                    data = time.strptime(value, "%Y.%M.%d")
            elif(len(value.split("//")) > 1):
                data = time.strptime(value, "%D/%M/%Y")
            else:
                data = time.strptime(value, "%Y%M%d")
            return time.strftime("%d/%M/%Y",data)

        except(ValueError):
                return ""

    def GetImageOrientationLabel(self):
        """
        Return Label regarding the orientation of
        an image. (AXIAL, SAGITTAL, CORONAL,
        OBLIQUE or UNKNOWN)
        """
        label = self.data['invesalius']['orientation_label']

        if (label):
            return label
        else:
            return ""

    def GetDimensionX(self):
        """
        Return integer associated to X dimension. This is related
        to the number of columns on the image.
        Return "" if not defined.
        """
        data = self.data['0028']['0011']
        if (data):
            return int(str(data))
        return ""


    def GetDimensionY(self):
        """
        Return integer associated to Y dimension. This is related
        to the number of rows on the image.
        Return "" if not defined.
        """
        data = self.data['0028']['0010']
        if (data):
            return int(str(data))
        return ""


    def GetImageDataType(self):
        """
        Return image's pixel representation data type (string). This
        might be:
          - Float64
          - Int8
          - Int16
          - Int32
          - UInt16
        Return "" otherwise.
        """
        repres = self._GetPixelRepresentation()

        bits = self._GetBitsAllocated()

        if not bits:
            answer = ""
        else:
            answer = "UInt16"

        if bits == 8:
            answer = "Int8"
        elif bits == 16:
            if repres:
                answer = "Int16"
        elif bits == 32:
            answer = "Int32"
        elif bits == 64:
            answer = "Float64"

        return answer

    def GetPixelSpacing(self):
        """
        Return [x, y] (number list) related to the distance between
        each pair of pixel. That is, adjacent row spacing (delimiter)
        and adjacent column spacing. Values are usually floating point
        and represent mm.
        Return "" if field is not defined.

        DICOM standard tag (0x0028, 0x0030) was used.
        """
        try:
            data = self.data['0028']['0030'].replace(",", ".")
        except(KeyError):
            return ""
        if (data):
            return [eval(value) for value in data.split('\\')]
        return ""

    def GetImagePixelSpacingY(self):
        """
        Return spacing between adjacent pixels considerating y axis
        (height). Values are usually floating point and represent mm.
        Return "" if field is not defined.

        DICOM standard tag (0x0028, 0x0030) was used.
        """
        spacing = self.GetPixelSpacing()
        if spacing:
            return spacing[1]
        return ""

    def GetImagePixelSpacingX(self):
        """
        Return spacing between adjacent pixels considerating x axis
        (width). Values are usually floating point and represent mm.
        Return "" if field is not defined.

        DICOM standard tag (0x0028, 0x0030) was used.
        """

        spacing = self.GetPixelSpacing()
        if spacing:
            return spacing[0]
        return ""


    def GetAcquisitionDate(self):
        """
        Return string containing the acquisition date using the
        format "dd/mm/yyyy".
        Return "" (empty string) if not set.

        DICOM standard tag (0x0008,0x0022) was used.
        """
        # TODO: internationalize data
        try:
            date = self.data['0008']['0022'] 
        except(KeyError):
            return ""

        if (date) and (date != ''):
            return self.__format_date(str(date))
        return ""

    def GetAcquisitionNumber(self):
        """
        Return integer related to acquisition of this slice.
        Return "" if field is not defined.

        DICOM standard tag (0x0020, 0x0012) was used.
        """
        data = self.data['0020']['0012'] 
        if (data):
            return int(str(data))
        return ""

    def GetAccessionNumber(self):
        """
        Return integer related to acession number

        DICOM standard tag (0x0008, 0x0050) was used.
        """
        #data = self.data[0x008][0x050]
        return ""
        if (data):
            try:
                value = int(str(data))
            except(ValueError): #Problem in the other\iCatDanielaProjeto
                value = 0
            return value
        return ""

    def GetImageWindowLevel(self, preset=WL_PRESET, multiple=WL_MULT):
        """
        Return image window center / level (related to brightness).
        This is an integer or a floating point. If the value can't
        be read, return "".
        By default, only one level value is returned, according to
        "preset" parameter. If no value is passed, WL_PRESET constant
        is used. In case one wishes to acquire a list with all
        level values, one should set "multiple" parameter to True.
        Return "" if field is not defined.
        DICOM standard tag (0x0028,0x1050) was used.
        """
        try:
            data = self.data['0028']['1050']
        except(KeyError):
            return "300"
        if (data):
            # Usually 'data' is a number. However, in some DICOM
            # files, there are several values separated by '\'.
            # If multiple values are present for the "Window Center"
            # we choose only one. As this should be paired to "Window
            # Width", it is set based on WL_PRESET
            value_list = [float(value) for value in data.split('\\')]
            if multiple:
                return value_list
            else:
                return value_list[preset]
        return "300"

    def GetImageWindowWidth(self, preset=WL_PRESET, multiple=WL_MULT):
        """
        Return image window width (related to contrast). This is an
        integer or a floating point. If the value can't be read,
        return "".

        By default, only one width value is returned, according to
        "preset" parameter. If no value is passed, WL_PRESET constant
        is used. In case one wishes to acquire a list with all
        preset values, one should set "multiple" parameter to True.

        Return "" if field is not defined.

        DICOM standard tag (0x0028,0x1051) was used.
        """
        try:
            data = self.data['0028']['1051']
        except(KeyError):
            return "2000"

        if (data):
            # Usually 'data' is a number. However, in some DICOM
            # files, there are several values separated by '\'.
            # If multiple values are present for the "Window Center"
            # we choose only one. As this should be paired to "Window
            # Width", it is set based on WL_PRESET
            value_list = [float(value) for value in data.split('\\')]

            if multiple:
                return str(value_list)
            else:
                return str(value_list[preset])
        return "2000"

    def GetImagePosition(self):
        """
        Return [x, y, z] (number list) related to coordinates
        of the upper left corner voxel (first voxel transmitted).
        This value is given in mm. Number might be floating point
        or integer.
        Return "" if field is not defined.

        DICOM standard tag (0x0020, 0x0032) was used.
        """
        try:
            data = self.data['0020']['0032'].replace(",", ".")
        except(KeyError):
            return ""
        if (data):
            return [eval(value) for value in data.split('\\')]
        return ""

    def GetImageLocation(self):
        """
        Return image location (floating value), related to the
        series acquisition.
        Return "" if field is not defined.

        DICOM standard tag (0x0020, 0x0032) was used.
        """
        data = self.data['0020']['1041']
        if (data):
            return eval(data)
        return ""

    def GetPhysicianReferringName(self):
        """
        Return string containing physician
        of the patient.
        Return "" if field is not defined.

        DICOM standard tag (0x0008, 0x0090) was used.
        """
        try:
            data = self.data['0008']['0090']
        except(KeyError):
            return ""

        if data == "None":
            return ""
        if (data):
            return data
        return ""

    def GetProtocolName(self):
        """
        Return string containing the protocal name
        used in the acquisition

        DICOM standard tag (0x0018, 0x1030) was used.
        """
        try:
            data = self.data['0018']['1030']
        except(KeyError):
            return None

        if (data):
            return data
        return None

    def GetImageType(self):
        """
        Return list containing strings related to image origin.
        Eg: ["ORIGINAL", "PRIMARY", "AXIAL"] or ["DERIVED",
        "SECONDARY", "OTHER"]
        Return "" if field is not defined.

        Critical DICOM tag (0x0008, 0x0008). Cannot be editted.
        """
        try:
            data = self.data['0008']['0008']
        except(IndexError):
            return []
        # TODO: Check if set image type to empty is the right way of handling
        # the cases where there is not this tag.
        except KeyError:
            return []

        if (data):
            try:
                return data.split('\\')
            except(IndexError):
                return []
        return []

    def GetSOPClassUID(self):
        """
        Return string containing the Unique Identifier for the SOP
        class.
        Return "" if field is not defined.

        Critical DICOM tag (0x0008, 0x0016). Cannot be edited.
        """
        try:
            data = self.data['0008']['0016']
        except(KeyError):
            return ""

        if (data):
            return data
        return ""

    def GetImagePatientOrientation(self):
        """
        Return matrix [x0, x1, x2, y0, y1, y2] related to patient
        image acquisition orientation. All values are in floating
        point representation. The first three values are associated
        to row orientation and the three last values are related
        to column orientation.
        Return "" if field is not defined.

        Critical DICOM tag (0x0020,0x0037). Cannot be edited.
        """
        try:
            data = self.data['0020']['0037'].replace(",", ".")
        except(KeyError):
            return [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]

        if (data):
            return [float(value) for value in data.split('\\')]
        return [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]

    def GetProtocolName(self):
        """
        Return protocol name (string). This info varies according to
        manufactor and software interface. Eg. "FACE", "aFaceSpi",
        "1551515/2" or "./protocols/user1.pfossa.pro".
        Return "" if field is not defined.

        DICOM standard tag (0x0018, 0x1030) was used.
        """
        try:
            data = self.data['0018']['1030']
            if (data):
                return data
        except(KeyError):
            return ""
        return ""

    def GetInstitutionName(self):
        """
        Return instution name (string) of the institution where the
        acquisitin quipment is located.

        DICOM standard tag (0x0008, 0x0080) was used.
        """
        try:
            data = self.data['0008']['0080']    
        except(KeyError):
            return ""

        if (data):
                return data
        return ""

    def _GetPixelRepresentation(self):
        """
        Return pixel representation of the data sample. Each sample
        should have the same pixel representation. Common values are:
          - 0000H = unsigned integer.
          - 0001H = 2's complement.

        DICOM standard tag (0x0028, 0x0103) was used.
        """
        tag = gdcm.Tag(0x0028, 0x0103)
        sf = gdcm.StringFilter()
        sf.SetFile(self.gdcm_reader.GetFile())
        res = sf.ToStringPair(tag)
        if (res[1]):
            return int(res[1])
        return ""

    def _GetBitsAllocated(self):
        """
        Return integer containing the number of bits allocated for
        each pixel sample. Each sample should have the same number
        of bits allocated. Usually this value is 8, *16*, 32, 64.

        DICOM standard tag (0x0028, 0x0100) was used.
        """
        #tag = gdcm.Tag(0x0028, 0x0100)
        #sf = gdcm.StringFilter()
        #sf.SetFile(self.gdcm_reader.GetFile())
        #res = sf.ToStringPair(tag)
        try:
            data = self.data['0028']['0100']
        except(KeyError):
            return ""

        if (data):
            return int(data)
        return ""

    def GetNumberOfFrames(self):
        """
        Number of frames in a multi-frame image.

        DICOM standard tag (0x0028, 0x0008) was used.
        """
        try:
            data = self.data['0028']['0008']
        except KeyError:
            return 1
        return int(data)


    def GetPatientBirthDate(self):
        """
        Return string containing the patient's birth date using the
        format "dd/mm/yyyy".
        Return "" (empty string) if not set.

        DICOM standard tag (0x0010,0x0030) was used.
        """
        # TODO: internationalize data
        try:
            data = self.data['0010']['0030']
        except(KeyError):
            return ""

        if (data) and (data != 'None'):
            return self.__format_date(str(data))
        return ""

    def GetStudyID(self):
        """
        Return string containing the Study ID.
        Return "" if not set.

        DICOM standard tag (0x0020,0x0010) was used.
        """
        try:
            data = self.data['0020']['0010']
        except(KeyError):
            return ""

        if (data):
            return str(data)
        return ""
        
    def GetAcquisitionGantryTilt(self):
        """
        Return floating point containing nominal angle of
        tilt (in degrees) accordingly to the scanning gantry.
        If empty field, return 0.0.

        DICOM standard tag (0x0018,0x1120) was used.
        """
        try:
            data = self.data['0018']['1120']
        except(KeyError):
            return 0.0

        if (data):
            return float(str(data))
        return 0.0

    def GetPatientGender(self):
        """
        Return patient gender (string):
          - M: male
          - F: female
          - O: other
        If not defined, return "".

        DICOM standard tag (0x0010,0x0040) was used.
        """
        try:
            data = self.data['0010']['0040']
        except(KeyError):
            return ""

        if (data):
            name = data.strip()
            encoding = self.GetEncoding()
            try:
                # Returns a unicode decoded in the own dicom encoding
                return utils.decode(name, encoding, 'replace')
            except(UnicodeEncodeError):
                return name

        return ""

    def GetPatientAge(self):
        """
        Return patient's age (integer). In case there are alpha
        characters in this field, a string is returned.
        If not defined field, return "".

        DICOM standard tag (0x0010, 0x1010) was used.
        """
        try:
            data = self.data['0010']['1010']
        except(KeyError):
            return ""

        if (data):
            age = (data.split('Y')[0])
            try:
                return int(age)
            except ValueError:
                return age
        return ""

    def GetPatientName(self):
        """
        Return patient's full legal name (string).
        If not defined, return "".

        DICOM standard tag (0x0010,0x0010) was used.
        """
        try:
            data = self.data['0010']['0010']
        except(KeyError):
            return ""

        if (data):
            name = data.strip()
            encoding = self.GetEncoding()
            
            try:
                # Returns a unicode decoded in the own dicom encoding
                return utils.decode(name, encoding, 'replace')
            except(UnicodeEncodeError):
                return name

        return ""

    def GetPatientID(self):
        """
        Return primary hospital identification number (string)
        or patient's identification number (string).
        Return "" if not defined.

        DICOM standard tag (0x0010,0x0020) was used.
        """
        try:
            data = self.data['0010']['0020']
        except(KeyError):
            return ""

        if (data):
            encoding = self.GetEncoding()
            # Returns a unicode decoded in the own dicom encoding
            try:
                return utils.decode(data, encoding, 'replace')
            except(UnicodeEncodeError):
                return data
        return ""

    def GetImageThickness(self):
        """
        Return float value related to the nominal reconstructed
        slice thickness (expressed in mm).
        Return "" if not defined.

        DICOM standard tag (0x0018,0x0050) was used.
        """
        try:
            data = self.data['0018']['0050'].replace(",", ".")
        except(KeyError):
            return 0
        if (data):
            return float(data)
        return 0

    def GetImageConvolutionKernel(self):
        """
        Return string related to convolution kernel or algorithm
        used to reconstruct the data. This is very dependent on the
        model and the manufactor. Eg. "standard" kernel could be
        written on various ways (STD, STND, Stand, STANDARD).
        Return "" if not defined.

        DICOM standard tag (0x0018,0x1210) was used.
        """
        try:
            data = self.data['0018']['1210']
        except(KeyError):
            return ""

        if (data):
            return data
        return ""

    def GetEquipmentInstitutionName(self):
        """
        Return institution name (string) where the acquisition
        equipment is located.
        Return "" (empty string) if not defined.

        DICOM standard tag (0x0008,0x0080) was used.
        """
        try:
            data = self.data['0008']['0080']
        except(KeyError):
            return ""

        if (data):
            return data
        return ""

    def GetStationName(self):
        """
        Return user defined machine name (string) used to produce exam
        files.
        Return "" if not defined.

        DICOM standard tag (0x0008, 0x1010) was used.
        """
        try:
            data = self.data['0008']['1010']
        except(KeyError):
            return ""

        if (data):
            return data
        return ""

    def GetAcquisitionModality(self):
        """
        Return modality of acquisition:
          - CT: Computed Tomography
          - MR: Magnetic Ressonance
        Return "" if not defined.

        DICOM standard tag (0x0008,0x0060) was used.
        """
        try:
            data = self.data['0008']['0060']
        except(KeyError):
            return ""

        if (data):
            return data
        return ""

    def GetImageNumber(self):
        """
        Return slice number (integer).
        Return "" if not defined.

        DICOM standard tag (0x0020,0x0013) was used.
        """
        try:
            data = self.data['0020']['0013']
        except(KeyError):
            return 0

        if (data):
            return int(data)
        return 0

    def GetStudyDescription(self):
        """
        Return study description (string).
        Return "" if not defined.

        DICOM standard tag (0x0008,0x1030) was used.
        """
        try:
            data = self.data['0008']['1030']
            if (data):
                encoding = self.GetEncoding()
                return utils.decode(data, encoding, 'replace')
        except(KeyError):
            return ""

    def GetSeriesDescription(self):
        """
        Return a string with a description of the series.
        DICOM standard tag (0x0008, 0x103E) was used.
        """
        try:
            data = self.data['0008']['103E']
            if data == "None":
                return _("unnamed")
            if (data):
                return data
            else:
                return _("unnamed")
        except(KeyError):
            return _("unnamed")

    def GetImageTime(self):
        """
        Return the image time.
        DICOM standard tag (0x0008,0x0033) was used.
        """
        try:
            data = self.data['0008']['0033']
        except(KeyError):
            return ""

        if (data) and (data != 'None'):
            return  self.__format_time(data)
        return ""

    def GetAcquisitionTime(self):
        """
        Return the acquisition time.
        DICOM standard tag (0x0008,0x032) was used.
        """
        try:
            data = self.data['0008']['0032']
        except(KeyError):
            return ""

        if (data):
            return self.__format_time(data)
        return ""

    def GetManufacturerName(self):
        """
        Return Manufacturer of the equipment that produced 
        the composite instances.
        """
        try:
            data = self.data['0008']['0070']
        except(KeyError):
            return ""

        if (data):
            return data
        return ""

    def GetSerieNumber(self):
        """
        Return the serie number
        DICOM standard tag (0x0020, 0x0011) was used.
        """
        try:
            data = self.data['0020']['0011']
        except(KeyError):
            return ""
        
        if (data):
            return data
        return ""

    def GetEncoding(self):
        """
        Return the dicom encoding
        DICOM standard tag (0x0008, 0x0005) was used.
        """
        try:
            encoding_value = self.data['0008']['0005']
            return const.DICOM_ENCODING_TO_PYTHON[encoding_value]
        except(KeyError):
            return 'ISO_IR_100'

    def GetOrientationLabelByInVesalius(self):
        """
        Return orientation label calculated by InVesalius (GDCM).
        Note: This is not in any DICOM tag.
        """
        return self.data['invesalius']['orientation_label']

    def GetThumbnailPathByInVesalius(self):
        return self.data['invesalius']['thumbnail_path']

    def GetDICOMPathByInVesalius(self):
        return self.data['invesalius']['dicom_path']

    def GetImageSpacingXYZByInVesalius(self):
        return (self.GetImagePixelSpacingX(), self.GetImagePixelSpacingY(),\
                self.GetImageThickness())

    def GetZSpacingCalculedByInVesalius(self):
        return self.data['invesalius']['z_spacing']


























#def BuildDictionary(filename):
#    """
#    Given a DICOM filename, generate dictionary containing parsed
#    information.
#    """
#
#    info = {}
#
#    parser = Parser()
#    parser.SetFileName(filename)
#
#    # Next statement will fill up dictionary info, parsing the DICOM
#    # file, given keys in info_keys list. Example:
#    # info["AcquisitionDate"] = dicom.GetAcquisitionDate()
#    for key in INFO_KEYS:
#        info[key] = eval("parser.Get"+key+"()")
#
#    return info
#
#def LoadDictionary(filename):
#    """
#    Given a binary file (containing a dictionary), return dictionary
#    containing parsed DICOM information.
#    """
#    import pickle
#
#    fp = open(filename, "rb")
#    info = pickle.load(fp)
#    fp.close()
#    return info
#
#
#def DumpDictionary(filename, dictionary=info):
#    """
#    Given a filename and a dictionary (optional), write DICOM
#    information to file in binary form.
#    """
#    import pickle
#
#    fp = open(filename, "wb")
#    pickle.dump(info, fp)
#    fp.close()
#
#if __name__ == "__main__":
#
#    # Example of how to use Parser
#    fail_count = 0
#    total = 48
#
#    for i in range(1,total+1):
#        filename = "..//data//"+str(i)+".dcm"
#
#        parser = Parser()
#        if parser.SetFileName(filename):
#            print("p:", parser.GetPatientName())
#            print("l:", parser.GetImageLocation())
#            print("o:", parser.GetImagePatientOrientation())
#            print("t:", parser.GetImageThickness())
#            print("s:", parser.GetPixelSpacing())
#            print("x:", parser.GetDimensionX())
#            print("y:", parser.GetDimensionY())
#            print("z:", parser.GetDimensionZ())
#        else:
#            print("--------------------------------------------------")
#            total-=1
#            fail_count+=1
#
#    print("\nREPORT:")
#    print("failed: ", fail_count)
#    print("sucess: ", total)
#
#    # Example of how to use auxiliary functions
#    total = 38
#    for i in range(1,total+1):
#        if (i==8) or (i==9) or (i==13):
#            pass
#        else:
#            filename = "..//data//"+str(i)+".dcm"
#            info = BuildDictionary(filename)
#            #print info
#
#
#
#
#
#class Dicom(object):
#    def __init__(self):
#        pass
#
#    def SetParser(self, parser):
#        self.parser = parser
#
#        self.LoadImageInfo()
#        self.LoadPatientInfo()
#        self.LoadAcquisitionInfo()
#        #self.LoadStudyInfo()
#
#    def LoadImageInfo(self):
#        self.image = Image()
#        self.image.SetParser(self.parser)
#
#    def LoadPatientInfo(self):
#        self.patient = Patient()
#        self.patient.SetParser(self.parser)
#
#    def LoadAcquisitionInfo(self):
#        self.acquisition = Acquisition()
#        self.acquisition.SetParser(self.parser)
#
#
#
#
#
#class Patient(object):
#    def __init__(self):
#        pass
#
#    def SetParser(self, parser):
#        self.name = parser.GetPatientName()
#        self.id = parser.GetPatientID()
#        self.age = parser.GetPatientAge()
#        self.birthdate = parser.GetPatientBirthDate()
#        self.gender = parser.GetPatientGender()
#        self.physician = parser.GetPhysicianReferringName()
#
#
#class Acquisition(object):
#
#    def __init__(self):
#        pass
#
#    def SetParser(self, parser):
#        self.patient_orientation = parser.GetImagePatientOrientation()
#        self.tilt = parser.GetAcquisitionGantryTilt()
#        self.id_study = parser.GetStudyID()
#        self.modality = parser.GetAcquisitionModality()
#        self.study_description = parser.GetStudyDescription()
#        self.acquisition_date = parser.GetAcquisitionDate()
#        self.institution = parser.GetInstitutionName()
#        self.date = parser.GetAcquisitionDate()
#        self.accession_number = parser.GetAccessionNumber()
#        self.series_description = parser.GetSeriesDescription()
#        self.time = parser.GetAcquisitionTime()
#        self.protocol_name = parser.GetProtocolName()
#        self.serie_number = parser.GetSerieNumber()
#        self.sop_class_uid = parser.GetSOPClassUID()
#
#
#class Image(object):
#
#    def __init__(self):
#        pass
#
#    def SetParser(self, parser):
#        self.level = parser.GetImageWindowLevel()
#        self.window = parser.GetImageWindowWidth()
#
#        self.position = parser.GetImagePosition()
#        if not (self.position):
#            self.position = [1, 1, 1]
#
#        self.number = parser.GetImageNumber()
#        self.spacing = spacing = parser.GetPixelSpacing()
#        self.orientation_label = parser.GetImageOrientationLabel()
#        self.file = parser.filename
#        self.time = parser.GetImageTime()
#        self.type = parser.GetImageType()
#        self.size = (parser.GetDimensionX(), parser.GetDimensionY())
#        #self.imagedata = parser.GetImageData()
#        self.bits_allocad = parser._GetBitsAllocated()
#        self.thumbnail_path = parser.thumbnail_path
#
#        self.number_of_frames = parser.GetNumberOfFrames()
#
#        if (parser.GetImageThickness()):
#            try:
#                spacing.append(parser.GetImageThickness())
#            except(AttributeError):
#                spacing = [1, 1, 1]
#        else:
#            try:
#                spacing.append(1.5)
#            except(AttributeError):
#                spacing = [1, 1, 1]
