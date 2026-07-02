from datetime import datetime, timezone
from app import db


class Album(db.Model):
    """
    A named collection of DICOM files.

    An Album doesn't store files directly — it stores references to them
    through the AlbumFile join table. One file can belong to many albums,
    and one album can contain many files. That's a many-to-many relationship.
    """

    __tablename__ = "albums"

    # Primary key
    id = db.Column(db.Integer, primary_key=True)

    # Album data
    name = db.Column(db.String(255), nullable=False)
    # The researcher-given name. e.g. "Chest CTs 2023" or "Brain MRIs Q1"
    # Not unique — a researcher can create two albums with the same name
    # (maybe they want a v1 and v2). That's valid.

    description = db.Column(db.Text, nullable=True)
    # Optional free-text notes about the album.
    # e.g. "All chest CT scans from the 2023 lung study, post-contrast only"

    # Timestamps
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    # onupdate fires automatically whenever this row is UPDATE-d.
    # So renaming an album or adding files updates this timestamp
    # without you having to write that logic in the route handler.

    # Relationships
    album_files = db.relationship(
        "AlbumFile",
        back_populates="album",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    # cascade="all, delete-orphan":
    #   Deleting an Album also deletes all its AlbumFile join rows.
    #   The DICOMFile rows themselves are NOT deleted — only the links.
    #   A file that was in this album still exists in the database and
    #   can still be part of other albums.
    #
    # lazy="dynamic":
    #   album.album_files returns a query object, not a pre-loaded list.
    #   This matters when an album has thousands of files — you don't
    #   want SQLAlchemy loading all of them into memory just because
    #   you loaded the album. You load them only when you actually
    #   call .all() or paginate.

    share_tokens = db.relationship(
        "ShareToken",
        back_populates="album",
        cascade="all, delete-orphan",
    )
    # Deleting an album also deletes all its share tokens.
    # Any existing share links for this album immediately stop working.

    # Helpers
    def file_count(self):
        """Returns the number of files in this album."""
        return self.album_files.count()
        # .count() works because lazy="dynamic" gives us a query object.
        # This runs SELECT COUNT(*) — much cheaper than loading all rows.

    def to_dict(self, include_file_count=True):
        """Serialise to a plain dict for JSON responses."""
        data = {
            "id":          self.id,
            "name":        self.name,
            "description": self.description,
            "created_at":  self.created_at.isoformat() if self.created_at else None,
            "updated_at":  self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_file_count:
            data["file_count"] = self.file_count()
        return data

    def __repr__(self):
        return f"<Album id={self.id} name={self.name!r}>"