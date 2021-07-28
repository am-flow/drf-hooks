from django.dispatch import Signal


hook_event = Signal(providing_args=['action', 'instance'])
raw_hook_event = Signal(providing_args=['event_name', 'payload', 'user'])
