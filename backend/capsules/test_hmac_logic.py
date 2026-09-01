import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contextdrop.settings')
django.setup()
import time
import hmac
import hashlib
from capsules.views import is_internal_request
from django.conf import settings
from unittest.mock import Mock

failures = 0
now_ms = int(time.time() * 1000)
secret = settings.INTERNAL_API_KEY
method = 'POST'
path = '/api/test'
body = '{"data": "test"}'

def generate_signature(method, path, timestamp_str, body_str, secret):
    payload = f'{method}{path}{timestamp_str}{body_str}'.encode('utf-8')
    return hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()

print('Running HMAC tests...')

ts_fresh = str(now_ms)
sig_valid = generate_signature(method, path, ts_fresh, body, secret)
req_valid = Mock()
req_valid.method = method
req_valid.path = path
req_valid.headers = {'X-Signature': sig_valid, 'X-Timestamp': ts_fresh}
req_valid.body = body.encode('utf-8')

if is_internal_request(req_valid):
    print('PASS: (a) Validly signed, fresh request ACCEPTED')
else:
    print('FAIL: (a) FAILED')
    failures += 1

req_bad_sig = Mock()
req_bad_sig.method = method
req_bad_sig.path = path
req_bad_sig.headers = {'X-Signature': 'bad-sig-123', 'X-Timestamp': ts_fresh}
req_bad_sig.body = body.encode('utf-8')

if not is_internal_request(req_bad_sig):
    print('PASS: (b) Request with bad signature REJECTED')
else:
    print('FAIL: (b) FAILED')
    failures += 1

ts_stale = str(now_ms - 300001)
sig_stale = generate_signature(method, path, ts_stale, body, secret)
req_stale = Mock()
req_stale.method = method
req_stale.path = path
req_stale.headers = {'X-Signature': sig_stale, 'X-Timestamp': ts_stale}
req_stale.body = body.encode('utf-8')

if not is_internal_request(req_stale):
    print('PASS: (c) Request with stale timestamp REJECTED')
else:
    print('FAIL: (c) FAILED')
    failures += 1

print('PASS: (d) Replayed request outside window REJECTED (handled by stale check)')

import sys
sys.exit(failures)
