"""Read-only WMS release checks. Supply an existing staff token via WMS_ACCEPTANCE_BEARER."""

import argparse
import json
import os
import re
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener


ROUTES = (
    ('picking route', '/picking/{task_id}/route-plan', {'stops': list, 'unmapped': list}),
    ('package contents', '/dn/{dn_id}/package-contents', {'items': list, 'packages': list}),
    ('pending putaway', '/inventory/pending-putaway/sources', {'items': list, 'total': int}),
    ('transfer orders', '/transfer/orders', {'items': list, 'total': int}),
    ('customer returns', '/asn/returns', {'items': list, 'total': int}),
)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base_url', help='HTTPS API base URL')
    parser.add_argument('commit', help='Expected Backend Git commit')
    parser.add_argument('--schema-only', action='store_true', help='Check the build and public GET definitions')
    parser.add_argument('--warehouse', type=int, help='Warehouse for an existing picking task and DN')
    parser.add_argument('--picking', type=int, help='Existing picking task ID')
    parser.add_argument('--dn', type=int, help='Existing DN ID')
    parser.add_argument('--ca-file', help='CA certificate for a private acceptance server')
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    url = urlsplit(base)
    if url.scheme != 'https' or not url.hostname or url.username is not None or url.query or url.fragment:
        parser.error('Provide an HTTPS base URL without credentials, query, or fragment')
    if not re.fullmatch('[0-9a-f]{7,40}', args.commit):
        parser.error('Expected commit must be a lowercase Git SHA of 7 to 40 characters')
    token = os.environ.get('WMS_ACCEPTANCE_BEARER')
    if not args.schema_only and (not token or not all(n and n > 0 for n in (args.warehouse, args.picking, args.dn))):
        parser.error('Business checks require WMS_ACCEPTANCE_BEARER and positive --warehouse, --picking, --dn')
    opener = build_opener(NoRedirect(), HTTPSHandler(context=ssl.create_default_context(cafile=args.ca_file)))

    def get(path, headers=None):
        request = Request(base + path, headers={'Accept': 'application/json', **(headers or {})})
        with opener.open(request, timeout=30) as response:
            return json.load(response)

    health = get('/health')
    actual = health.get('commit', '') if isinstance(health, dict) else ''
    correct = bool(isinstance(actual, str) and re.fullmatch('[0-9a-f]{7,40}', actual)
                   and (args.commit.startswith(actual) or actual.startswith(args.commit))
                   and health.get('status') == 'ok')
    print('Backend commit', actual if re.fullmatch('[0-9a-f]{7,40}', str(actual)) else 'unknown',
          'PASS' if correct else 'FAIL')
    schema = get('/warehouse/swagger.json')
    paths = schema.get('paths', {}) if isinstance(schema, dict) else {}
    for label, path, _ in ROUTES:
        present = 'get' in paths.get(path, {})
        correct &= present
        print('Schema GET', label, 'PASS' if present else 'FAIL')
    if args.schema_only or not correct:
        return 0 if correct else 1

    headers = {'Authorization': 'Bearer ' + token, 'X-Warehouse-ID': str(args.warehouse)}
    for label, path, fields in ROUTES:
        target = path.format(task_id=args.picking, dn_id=args.dn)
        if 'total' in fields:
            target += '?page=1&per_page=1'
        result = get('/warehouse' + target, headers)
        matched = isinstance(result, dict) and all(type(result.get(k)) is t for k, t in fields.items())
        if label == 'picking route':
            matched = matched and result.get('warehouse_id') == args.warehouse and result.get('task_id') == args.picking
        print('Authenticated GET', label, 'PASS' if matched else 'FAIL')
        correct &= matched
    return 0 if correct else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except HTTPError as error:
        sys.exit(f'GET failed with HTTP {error.code}')
    except (URLError, TimeoutError, OSError, ValueError) as error:
        sys.exit(f'GET failed ({type(error).__name__})')
