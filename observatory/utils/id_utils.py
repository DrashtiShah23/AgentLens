import uuid


def generate_uuid() -> str:
    return str(uuid.uuid4())


def generate_run_id(prefix: str = "run") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"
