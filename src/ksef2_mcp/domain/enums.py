from enum import StrEnum


class InvoiceStatus(StrEnum):
    UPLOADED = "uploaded"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class SubmissionStatus(StrEnum):
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
