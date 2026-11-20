#!/usr/bin/env python3
"""PostgREST's JWK set = auth.webgma.co.il's public RS256 keys (#275/13, doc:auth-integration §4). auth is the only issuer:
the local login and its HS256 secret were removed. Public keys only, so nothing secret here; the file is still 600.

Run by the `api` worker at each start (key rotation). If auth is unreachable it keeps the previous file; with no previous
file it writes an empty set, so PostgREST accepts no token at all (anonymous only) rather than a stale or foreign key.
"""
import json, os, urllib.request

OUT = os.path.expanduser(os.environ.get('PGRST_JWKS_FILE', '~/.pgrst-jwks.json'))
try:
    with urllib.request.urlopen('https://auth.webgma.co.il/.well-known/jwks.json', timeout=10) as r:
        keys = [k for k in json.load(r)['keys'] if k.get('kty') == 'RSA']
except Exception as e:
    if os.path.exists(OUT):
        print('pgrst-jwks: auth JWKS fetch failed (%s), keeping %s' % (type(e).__name__, OUT)); raise SystemExit(0)
    print('pgrst-jwks: auth JWKS fetch failed (%s), writing an empty key set' % type(e).__name__); keys = []
tmp = OUT + '.tmp'
with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as f:
    json.dump({'keys': keys}, f)
os.replace(tmp, OUT)
print('pgrst-jwks: wrote %s (%d auth RS256 keys)' % (OUT, len(keys)))
