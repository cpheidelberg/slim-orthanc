import numpy as np

import pydicom as dcm
from pydicom.dataset import Dataset
from pydicom.sequence import Sequence
from pydicom.valuerep import PersonName
import highdicom as hd
from highdicom.sr import (
    CodeContentItem,
    CodedConcept,
    Comprehensive3DSR,
    ContainerContentItem,
    ImageContentItem,
    NumContentItem,
    PnameContentItem,
    RelationshipTypeValues,
    Scoord3DContentItem,
    TextContentItem,
    UIDRefContentItem
)
from dicomweb_client.api import DICOMwebClient


class DicomSR:
    """Create a DICOM SR file with annotations from a WSI DICOM image."""
    def __init__(self, prediction, polylines, dicomPath=None, dicomFile=None):
        if dicomPath:
            print("File")
            self.dicomPath = dicomPath
            self.dicomFile = dcm.dcmread(dicomPath)
        elif dicomFile:
            print("File")
            self.dicomFile = dicomFile
        else:
            raise ValueError("Either dicomPath or dicomFile must be provided.")

        print(f"Height: {self.dicomFile.ImagedVolumeHeight}")
        print(f"Width: {self.dicomFile.ImagedVolumeWidth}")
        print(f"Depth: {self.dicomFile.ImagedVolumeDepth}")

        self.prediction = prediction
        self.polylines = polylines


    def get_library_item(self):
        """Create single library item"""

        image_item = ImageContentItem(
            name=CodedConcept(value='260753009',
                scheme_designator='SCT',
                meaning='Source',
            ),
            referenced_sop_class_uid = self.dicomFile.SOPClassUID,
            referenced_sop_instance_uid = self.dicomFile.SOPInstanceUID,
            relationship_type=RelationshipTypeValues.CONTAINS,
        )
        image_item.ContentSequence = []

        code_item = CodeContentItem(
            name=CodedConcept(value='121139',
                                scheme_designator='DCM',
                                meaning="Modality"),
            value=CodedConcept(value='SM',
                                scheme_designator='DCM',
                                meaning="Slide Microscopy"),
            relationship_type=RelationshipTypeValues.HAS_ACQ_CONTEXT,
        )
        image_item.ContentSequence.append(code_item)

        uid_item = UIDRefContentItem(
            name=CodedConcept(value='112227',
                                scheme_designator='DCM',
                                meaning="Frame of Reference UID"),
            value=self.dicomFile.FrameOfReferenceUID,
            relationship_type=RelationshipTypeValues.HAS_ACQ_CONTEXT,
        )
        image_item.ContentSequence.append(uid_item)

        row_item = NumContentItem(
            name=CodedConcept(value='110910',
                                scheme_designator='DCM',
                                meaning="Pixel Data Rows"),
            value=self.prediction,
            unit=CodedConcept(
                value='{pixels}',
                scheme_designator='UCUM',
                meaning='Pixels'
            ),
            relationship_type=RelationshipTypeValues.HAS_ACQ_CONTEXT,
        )
        image_item.ContentSequence.append(row_item)

        column_item = NumContentItem(
            name=CodedConcept(value='110911',
                                scheme_designator='DCM',
                                meaning="Pixel Data Columns"),
            value=self.prediction,
            unit=CodedConcept(
                value='{pixels}',
                scheme_designator='UCUM',
                meaning='Pixels'
            ),
            relationship_type=RelationshipTypeValues.HAS_ACQ_CONTEXT,
        )
        image_item.ContentSequence.append(column_item)

        return image_item


    def get_library_container(self):
        """Container for the library item"""
        library_item = ContainerContentItem(
            name=CodedConcept(value='126200',
                scheme_designator='DCM',
                meaning='Image Library Group',
            ),
            relationship_type=RelationshipTypeValues.CONTAINS,
        )
        library_item.ContentSequence = []

        # iterate over all instance UIDs
        library_item.ContentSequence.append(self.get_library_item())

        return library_item
        

    def get_polyline_item(self, polyline):
        """Detailed sequence items required for single annotation sequence."""

        text_item = TextContentItem(
            name=CodedConcept(
                value='112039',
                scheme_designator='DCM',
                meaning="Tracking Identifier"
            ),
            value="Index annotation region",
            relationship_type=RelationshipTypeValues.HAS_OBS_CONTEXT
        )
        
        uid_item = UIDRefContentItem(
            name=CodedConcept(value='112040',
                                scheme_designator='DCM',
                                meaning="Tracking Unique Identifier"),
            value=hd.UID(),
            relationship_type=RelationshipTypeValues.HAS_OBS_CONTEXT,
        )  

        code_item = CodeContentItem(
            name=CodedConcept(value='276214006',
                                scheme_designator='SCT',
                                meaning="Finding category"),
            value=CodedConcept(value='49755003',
                                scheme_designator='SCT',
                                meaning="Morphologic abnormality"),
            relationship_type=RelationshipTypeValues.CONTAINS,
        )
        
        code2_item = CodeContentItem(
            name=CodedConcept(value='121071',
                                scheme_designator='DCM',
                                meaning="Finding"),
            value=CodedConcept(value='14269005',
                                scheme_designator='SCT',
                                meaning="Embryonal rhabdomyosarcoma"),
            relationship_type=RelationshipTypeValues.CONTAINS,
        )

        scoord_item = Scoord3DContentItem(
            name=CodedConcept(value='111030', 
                                scheme_designator='DCM',
                                meaning="Image Region"),
            graphic_type="POLYGON",
            graphic_data=polyline,
            frame_of_reference_uid=self.dicomFile.FrameOfReferenceUID,
            relationship_type=RelationshipTypeValues.CONTAINS,
        )
        

        return text_item, uid_item, code_item, code2_item, scoord_item


    def get_finding_container(self):
        """Structure various annotations as tuple of items"""
        image_items = []
        for polyline in self.polylines:
            print(polyline)
            label = "Tissue"
            polyline_sequence = self.get_polyline_item(polyline)

            finding_container = ContainerContentItem(
                name=CodedConcept(value='125007', 
                                scheme_designator='DCM',
                                meaning="Measurement Group"),
                relationship_type=RelationshipTypeValues.CONTAINS,
            )
            finding_container.ContentTemplateSequence = [Dataset()]
            finding_container.ContentTemplateSequence[0].MappingResource = "DCMR"
            finding_container.ContentTemplateSequence[0].TemplateIdentifier = "1410"
            finding_container.ContentSequence = polyline_sequence

            image_items.append(finding_container)
        if len(self.polylines) == 0:
            image_items.append(self.get_empty_container(label))

        return image_items


    def create_file(self):
        
        # Create a primary container for the SR
        root_item = ContainerContentItem(
            name=CodedConcept(
                value='126000',
                scheme_designator='DCM',
                meaning='Imaging Measurement Report'
            )
        )
        root_item.ContentTemplateSequence = [Dataset()]
        root_item.ContentTemplateSequence[0].MappingResource = "DCMR"
        root_item.ContentTemplateSequence[0].TemplateIdentifier = "1500"
        root_item.ContentSequence = []

        language_item = CodeContentItem(
            name=CodedConcept(
                value='121049',
                scheme_designator='DCM',
                meaning="Language of Content Item and Descendants"
            ),
            value=CodedConcept(
                value='en-US',
                scheme_designator='RFC5646',
                meaning="English (United States)"
            ),
            relationship_type=RelationshipTypeValues.HAS_CONCEPT_MOD
        )
        root_item.ContentSequence.append(language_item)

        observer_type_item = CodeContentItem(
            name=CodedConcept(
                value='121005',
                scheme_designator='DCM',
                meaning="Person"
            ),
            value=CodedConcept(
                value='121006',
                scheme_designator='DCM',
                meaning="Person"
            ),
            relationship_type=RelationshipTypeValues.HAS_OBS_CONTEXT
        )
        root_item.ContentSequence.append(observer_type_item)

        observer_name_item = PnameContentItem(
            name=CodedConcept(
                value='121008',
                scheme_designator='DCM',
                meaning="Person Observer Name"
            ),
            value=PersonName.from_named_components(
                family_name="Weis",
                given_name="C.-A.",
                name_prefix="Dr.",
            ),
            relationship_type=RelationshipTypeValues.HAS_OBS_CONTEXT
        )
        root_item.ContentSequence.append(observer_name_item)

        subject_item = CodeContentItem(
            name=CodedConcept(
                value='121024',
                scheme_designator='DCM',
                meaning="Subject Class"
            ),
            value=CodedConcept(
                value='121027',
                scheme_designator='DCM',
                meaning="Specimen"
            ),
            relationship_type=RelationshipTypeValues.HAS_OBS_CONTEXT
        )
        root_item.ContentSequence.append(subject_item)

        uid_item = UIDRefContentItem(
            name=CodedConcept(
                value='121039',
                scheme_designator='DCM',
                meaning="Specimen UID"
            ),
            value=self.dicomFile.SpecimenUID,
            relationship_type=RelationshipTypeValues.HAS_OBS_CONTEXT
        )
        root_item.ContentSequence.append(uid_item)

        specimen_identifier_item = TextContentItem(
            name=CodedConcept(
                value='121041',
                scheme_designator='DCM',
                meaning="Specimen Identifier"
            ),
            value="PARFTU-0BGCLU_2",
            relationship_type=RelationshipTypeValues.HAS_OBS_CONTEXT
        )
        root_item.ContentSequence.append(specimen_identifier_item)

        specimen_container_item = TextContentItem(
            name=CodedConcept(
                value='111700',
                scheme_designator='DCM',
                meaning="Specimen Container Identifier"
            ),
            value="PARFTU-0BGCLU_2",
            relationship_type=RelationshipTypeValues.HAS_OBS_CONTEXT
        )
        root_item.ContentSequence.append(specimen_container_item)                   

        procedure_item = CodeContentItem(
            name=CodedConcept(value='121058',
                scheme_designator='DCM',
                meaning='Procedure reported',
            ),
            value=CodedConcept(value='104157003',
                scheme_designator='SCT',
                meaning='Light microscopy',
            ),
            relationship_type=RelationshipTypeValues.HAS_CONCEPT_MOD,
        )
        root_item.ContentSequence.append(procedure_item)

        library_item = ContainerContentItem(
            name=CodedConcept(value='111028',
                scheme_designator='DCM',
                meaning='Image Library',
            ),
            relationship_type=RelationshipTypeValues.CONTAINS,
        )
        library_item.ContentSequence = [self.get_library_container()]
        root_item.ContentSequence.append(library_item)

        image_measure_item = ContainerContentItem(
            name=CodedConcept(value='126010',
                scheme_designator='DCM',
                meaning='Imaging Measurements',
            ),
            relationship_type=RelationshipTypeValues.CONTAINS,
        )
        image_measure_item.ContentSequence = self.get_finding_container()

        root_item.ContentSequence.append(image_measure_item)
        content_sequence = Sequence()
        content_sequence.append(root_item)

        # create DICOM SR file
        self.sr = Comprehensive3DSR(
            evidence=[self.dicomFile],
            content=root_item,
            series_instance_uid=hd.UID(),
            series_number=1,
            instance_number=1,
            sop_instance_uid=hd.UID(),
            manufacturer="Uni Heidelberg",
            verifying_observer_name="C. Blattgerste",
        )

        diagnosis_code = Dataset()
        diagnosis_code.CodeValue = '302847003'
        diagnosis_code.CodingSchemeDesignator = 'SCT'
        diagnosis_code.CodeMeaning = 'Test Sarkom'
        self.sr.AdmittingDiagnosesDescription = 'Test Sarkom' # geht nicht
        self.sr.AdmittingDiagnosesCodeSequence = Sequence([diagnosis_code])

        # Save the DICOM Dataset
        return self.sr


if __name__ == "__main__":
    # Pfad zum DICOM-Bild
    inPath = "original.dcm"
    outPath = "structured_report.dcm"

    # TODO: Download WSI via DICOM web, currently work on local file

    prediction = 5
    polylines = np.array([
            [5.0, 5.0, 0], 
            [5.0, 10.7, 0], 
            [20.5, 10.8, 0], 
            [20.3, 5.6, 0],
            [5.0, 5.0, 0], 
    ]),

    dicomSR = DicomSR(dicomPath=inPath, prediction=prediction, polylines=polylines)
    sr_file = dicomSR.create_file()

    sr_file.save_as(outPath)
    print(f"SR-Dokument wurde als {outPath} gespeichert.")

    # -----------------------------------------------------------------------------
    # Upload the annotation using dicomweb_client
    # -----------------------------------------------------------------------------
    dicomweb_url = "http://localhost:8042/dicom-web"
    client = DICOMwebClient(dicomweb_url)
    client.store_instances([sr_file])

    print("Annotation SR file created and uploaded successfully.")

    # sr_dataset.save_as("structured_report.dcm")
    # print(f"SR-Dokument wurde als 'structured_report.dcm' gespeichert.")



