from datetime import datetime, timezone
from app import db

class DICOMFile(db.model):
    """
    one row per indexed .dcm file 
    populated by the indexer service(services/indexer.py). 
    quality_score and is_anomaly are weitten later by the IsolationForest quality 
    detector (ml/quality.py)
    """

    __tablename__ = "dicom_files"

    #primary key 
    id = db.Coloumn(db.Integer, primary_key = True)

    #File location 
    filepath = db.Column(db.Text, nullable = False)

    #Absolute path on disk. not unique because the same physical file 
    #could theoretically be re-indexed from a different amount point, but 
    #sop_instance_uid below IS unique and is the real duplicate key 

    #DICOM metadata tags (extracted by pydicom, stored as plain text)

    patient_id = db.Column(db.String(64), nullable = True)
    modality = db.Column(db.String(16), nullable = True) #ct, mr, cr, dx ...
    study_date = db.Column(db.String(16), nullable = True) #YYYYMMDD from DICOM tag
    body_part = db.Column(db.String(64), nullable = True) #chest , brain etc
    manufacturer = db.Column(db.String(128), nullable = True), #used as a clustering feature
    sop_instance_uid = db.Column(db.String(128), nullable = True, unique = True)

    #SopInstanceUID is the globally unique identifier for a single DICOM image. 
    #the UNIQUE constraint here is the deduplication mechanism 
    #if the same file is scanned twice, the second insert raises an IntegrityError 
    #and the indexer skips it cleanly instead of creating a duplicate row 

    #ML OUTPUTS (written by quality.py, NULL until that step runs)

    quality_score = db.Column(db.Float, nullable = True)
    #IsolationForest anamoly score, more negative = more anomalous. 
    #range is roughly -0.5(very anomalous) to +0.5(very normal)

    is_anomaly = db.Column(db.Boolean, nullable = True, default = False)
    #true when quality_score fails below the contamination threshold 

    #HOUSEKEEPING 
    indexed_at = db.Column(db.DateTime(timezone= True), nullable = False, default = lambda: datetime.now(timezone.utc))

    #relationships 
    album_files = db.relationship("AlbumFile", back_populates = "dicom_file", cascade="all, delete-orphan",
    #cascades if a DICOMFILE row is deleted, it's AlbumFile join rows ate also deleted
    #the actual file on disk is not touched. 
    )

    #HELPERS

    def to_dict(self): 
        """Serialise to a plain dict for JSON responses,"""
        return{
            "id": self.id,
            "filepath" : self.filepath,
            "patient_id" : self.patient_id,
            "modality" : self.modality,
            "study_date": self.study_date,
            "body_part" : self.body_part,
            "manufacturer": self.manufacturer,
            "sop_instance_uid": self.sop_instance_uid,
            "quality_score": self.quality_score, 
            "is_anamoly" : self.is_anomaly,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None
        }
    def __repr__(self):
        return f"<DICOMFile id={self.id} modality={self.modality} uid={self.sop_instance_uid}>"