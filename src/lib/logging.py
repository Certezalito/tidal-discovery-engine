import logging


def _safe_value(value):
    text = str(value)
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    return text.strip()


def _serialize_fields(fields):
    if not fields:
        return ""

    ordered = []
    for key in sorted(fields.keys()):
        ordered.append(f"{key}={_safe_value(fields[key])}")
    return "|" + "|".join(ordered)


def log_cli_warning(code, message, **fields):
    payload = f"TDE_WARN|code={code}{_serialize_fields(fields)}|message={_safe_value(message)}"
    logging.warning(payload)


def log_cli_error(code, message, **fields):
    payload = f"TDE_ERROR|code={code}{_serialize_fields(fields)}|message={_safe_value(message)}"
    logging.error(payload)


def bounded_name_preview(names, max_items=5, max_name_length=80):
    preview = []
    for raw_name in names[:max_items]:
        safe = _safe_value(raw_name)
        if len(safe) > max_name_length:
            safe = safe[: max_name_length - 3] + "..."
        preview.append(safe)
    return preview


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("project.log"),
            logging.StreamHandler()
        ]
    )
