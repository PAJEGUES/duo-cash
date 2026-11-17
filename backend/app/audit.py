"""Log estruturado de eventos de segurança.

Regra: só identificadores (user_id, workspace_id, invite_id...). Nunca tokens,
e-mails, valores ou descrições de gastos.
"""

import json
import logging

from flask import has_request_context, request

log = logging.getLogger("duocash.security")


def audit(event: str, **fields) -> None:
    record = {"event": event}
    if has_request_context():
        record["ip"] = request.remote_addr
    record.update({k: str(v) if v is not None else None for k, v in fields.items()})
    log.info(json.dumps(record, ensure_ascii=False))
