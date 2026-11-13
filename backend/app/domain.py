"""Pure business rules; also exercised without third-party packages."""
from enum import StrEnum
import math

class State(StrEnum):
    NO_CAMERA = 'No Camera'
    READY = 'Camera Ready'
    REQUESTED = 'Capture Requested'
    WAITING = 'Waiting for Image'
    RECEIVED = 'Photo Received'
    REVIEWING = 'Reviewing'
    APPROVED = 'Approved'
    RETAKE = 'Retake Requested'
    ERROR = 'Capture Error'

TRANSITIONS = {
    State.READY: {State.REQUESTED}, State.NO_CAMERA: {State.REQUESTED},
    State.REQUESTED: {State.WAITING, State.ERROR},
    State.WAITING: {State.RECEIVED, State.ERROR, State.RETAKE},
    State.RECEIVED: {State.REVIEWING},
    State.REVIEWING: {State.APPROVED, State.RETAKE, State.ERROR},
    State.RETAKE: {State.REQUESTED}, State.ERROR: {State.RETAKE},
    State.APPROVED: set(),
}

def transition(current, target):
    if target not in TRANSITIONS.get(current, set()):
        raise ValueError(f'Cannot change {current} to {target}')
    return str(target)

def validate_fields(fields):
    keys = [f['key'] for f in fields]
    if len(keys) != len(set(keys)) or 'full_name' not in keys:
        raise ValueError('Fields need unique keys and full_name')
    for f in fields:
        if not f['key'].isidentifier() or f.get('type', 'text') not in ('text', 'date', 'select'):
            raise ValueError('Invalid field key or type')
        if f.get('type') == 'select' and not f.get('options'):
            raise ValueError('Dropdown needs options')

def validate_student(fields, data, draft=False):
    unknown = set(data) - {f['key'] for f in fields}
    if unknown:
        raise ValueError('Unknown fields: ' + ', '.join(sorted(unknown)))
    for f in fields:
        raw = data.get(f['key'], '')
        if not isinstance(raw, str):
            raise ValueError(f"{f['label']} must be text; check missing import columns")
        value = raw.strip()
        if not draft and f.get('required') and not value:
            raise ValueError(f"{f['label']} is required")
        if len(value) > 1000:
            raise ValueError('Field exceeds 1000 characters')
        if value and f.get('type') == 'select' and value not in f['options']:
            raise ValueError(f"Invalid selection for {f['label']}")
        if value and f.get('type') == 'date':
            from datetime import date
            date.fromisoformat(value)

def validate_mapping(mapping, fields):
    if not isinstance(mapping, dict) or not mapping or any(not isinstance(k,str) or not k.strip() or not isinstance(v,str) for k,v in mapping.items()):
        raise ValueError('Supply nonempty named object mappings')
    if 'photo' not in mapping.values():
        raise ValueError('Map a named photo frame to photo')
    if any(v not in set(fields) | {'photo'} for v in mapping.values()):
        raise ValueError('Mapping references an unknown student field')

def sheet_positions(width, height, card_w, card_h, margin, gap, bleed=0):
    values = [width, height, card_w, card_h, margin, gap, bleed]
    if not all(math.isfinite(x) for x in values) or min(width, height, card_w, card_h) <= 0 or min(margin, gap, bleed) < 0:
        raise ValueError('Invalid sheet dimensions')
    tile_w, tile_h = card_w + 2*bleed, card_h + 2*bleed
    cols = int((width-2*margin+gap)//(tile_w+gap))
    rows = int((height-2*margin+gap)//(tile_h+gap))
    if cols < 1 or rows < 1 or cols*rows > 1000:
        raise ValueError('Cards do not fit this sheet')
    return [(margin+c*(tile_w+gap)+bleed, margin+r*(tile_h+gap)+bleed) for r in range(rows) for c in range(cols)]
