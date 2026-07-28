class ValidationError(Exception):
    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.message = message
        self.field = field


def _is_empty(value) -> bool:
    return value is None or value == ''


def parse_float(value, field: str, default: float = 0.0) -> float:
    if _is_empty(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f'{field} must be a number', field) from exc


def parse_int(value, field: str, default: int = 0) -> int:
    if _is_empty(value):
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f'{field} must be an integer', field) from exc


def parse_bool(value, field: str, default: bool = False) -> bool:
    """Parse boolean values consistently; bool('false') must not become True."""
    if value is None or value == '':
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {'true', '1', 'yes', 'on'}:
            return True
        if normalized in {'false', '0', 'no', 'off'}:
            return False
    raise ValidationError(f'{field} must be a boolean', field)


def parse_limit(value, default: int, max_limit: int) -> int:
    if value is None:
        return default
    try:
        limit = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError('limit must be an integer', 'limit') from exc
    if limit < 1:
        raise ValidationError('limit must be >= 1', 'limit')
    return min(limit, max_limit)


def normalize_telemetry_body(body: dict) -> dict:
    if body.get('alerts') is not None and not isinstance(body.get('alerts'), dict):
        raise ValidationError('alerts must be an object', 'alerts')

    voice_cmd = body.get('lastVoiceCmd')
    if voice_cmd is not None and not isinstance(voice_cmd, str):
        raise ValidationError('lastVoiceCmd must be a string', 'lastVoiceCmd')

    return {
        'distanceCm': parse_float(body.get('distanceCm'), 'distanceCm'),
        'temperature': parse_float(body.get('temperature'), 'temperature'),
        'humidity': parse_float(body.get('humidity'), 'humidity'),
        'smokeRaw': parse_int(body.get('smokeRaw'), 'smokeRaw'),
        'fan': parse_bool(body.get('fan'), 'fan', False),
        'alarm': parse_bool(body.get('alarm'), 'alarm', False),
        'windowOpen': parse_bool(body.get('windowOpen'), 'windowOpen', False),
        'autoMode': parse_bool(body.get('autoMode'), 'autoMode', True),
        'safetyActive': parse_bool(body.get('safetyActive'), 'safetyActive', True),
        'lastVoiceCmd': voice_cmd or '',
        'wifiRssi': parse_int(body.get('wifiRssi'), 'wifiRssi'),
        'alerts': body.get('alerts') or {},
    }
