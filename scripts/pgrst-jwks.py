#!/usr/bin/env python3
"""Build PostgREST's JWK set: our own HS256 secret + auth.webgma.co.il's public RS256 keys (#275/13, doc:auth-integration §4).

Run by the `api` worker at each start, after it sourced .env: reads PGRST_JWT_SECRET from the ENVIRONMENT (never argv),
writes ~/.pgrst-jwks.json (mode 600) and prints only the key count. The worker then points PGRST_JWT_SECRET at
@~/.pgrst-jwks.json. If auth is unreachable it keeps the previous file's auth keys (or serves our own key alone).
"""
import base64, json, os, sys, urllib.request

OUT = os.path.expanduser(os.environ.get('PGRST_JWKS_FILE', '~/.pgrst-jwks.json'))
secret = os.environ.get('PGRST_JWT_SECRET', '')
if not secret or secret.startswith('@'):
    sys.exit('pgrst-jwks: PGRST_JWT_SECRET (the raw HS256 secret) not in the environment')
own = {'kty': 'oct', 'alg': 'HS256', 'k': base64.urlsafe_b64encode(secret.encode()).rstrip(b'=').decode()}

auth = None
try:
    with urllib.request.urlopen('https://auth.webgma.co.il/.well-known/jwks.json', timeout=10) as r:
        auth = [k for k in json.load(r)['keys'] if k.get('kty') == 'RSA']
except Exception as e:
    print('pgrst-jwks: auth JWKS fetch failed (%s), keeping the previous auth keys' % type(e).__name__)
    try:
        with open(OUT) as f:
            auth = [k for k in json.load(f)['keys'] if k.get('kty') == 'RSA']
    except Exception:
        auth = []

tmp = OUT + '.tmp'
fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, 'w') as f:
    json.dump({'keys': [own] + auth}, f)
os.chmod(tmp, 0o600)
os.replace(tmp, OUT)
print('pgrst-jwks: wrote %s (1 own HS256 + %d auth RS256 keys)' % (OUT, len(auth)))
