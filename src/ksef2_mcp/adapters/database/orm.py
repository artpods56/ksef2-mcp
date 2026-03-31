from sqlalchemy import Column, DateTime, MetaData, Table, Text

metadata = MetaData()

session_states = Table(
    "session_states",
    metadata,
    Column("uuid", Text, primary_key=True),
    Column("state_json", Text, nullable=False),
    Column("date_created", DateTime, nullable=False),
    Column("date_closed", DateTime, nullable=True),
)

invoices = Table(
    "invoices",
    metadata,
    Column("invoice_id", Text, primary_key=True),
    Column("status", Text, nullable=False),
    Column("invoice_xml", Text, nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
    Column("latest_submission_id", Text, nullable=True),
)

submissions = Table(
    "submissions",
    metadata,
    Column("submission_id", Text, primary_key=True),
    Column("invoice_id", Text, nullable=False),
    Column("invoice_reference_number", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
    Column("session_state_json", Text, nullable=True),
    Column("finalized_at", DateTime, nullable=True),
    Column("ksef_number", Text, nullable=True),
    Column("message", Text, nullable=True),
    Column("details_json", Text, nullable=True),
)


def start_mappers() -> None:
    return None
