#!/usr/bin/env python3
"""
_r2_backup.py — Upload/download files to Cloudflare R2 using direct API (bypasses wrangler bugs).

Usage:
    python _r2_backup.py upload <local_file> <r2_path>
    python _r2_backup.py download <r2_path> <local_file>
    python _r2_backup.py --batch <manifest.json>

Requires: CLOUDFLARE_API_TOKEN environment variable (or ~/.cloudflare/api-token file)

This is the CANONICAL R2 access tool. Use it when wrangler fails on Windows
(known async assertion bug in wrangler 4.98.0).
"""
import os, sys, json, hashlib, urllib.request, urllib.error

BUCKET = 'qnfo'

def get_api_token():
    """Get Cloudflare API token from environment or file."""
    token = os.environ.get('CLOUDFLARE_API_TOKEN', '')
    if token:
        return token
    token_file = os.path.join(os.path.expanduser('~'), '.cloudflare', 'api-token')
    if os.path.exists(token_file):
        with open(token_file) as f:
            return f.read().strip()
    return None

def get_account_id(token):
    """Get Cloudflare account ID from API."""
    req = urllib.request.Request(
        'https://api.cloudflare.com/client/v4/accounts',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        accounts = data.get('result', [])
        if accounts:
            return accounts[0]['id']
    except Exception as e:
        print(f"  ERROR getting account ID: {e}")
    return None

def upload_to_r2(token, account_id, r2_path, local_path):
    """Upload a file to R2 using direct Cloudflare API."""
    with open(local_path, 'rb') as f:
        content = f.read()
    
    sha256 = hashlib.sha256(content).hexdigest()
    url = f'https://api.cloudflare.com/client/v4/accounts/{account_id}/r2/buckets/{BUCKET}/objects/{r2_path}'
    
    req = urllib.request.Request(
        url, data=content, method='PUT',
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/octet-stream',
            'X-Amz-Content-Sha256': sha256,
        }
    )
    
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        if result.get('success'):
            return True, f"Uploaded {len(content)} bytes"
        else:
            return False, str(result.get('errors', ['Unknown error'])[0])
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, str(e)

def download_from_r2(token, account_id, r2_path, local_path):
    """Download a file from R2 using direct Cloudflare API."""
    url = f'https://api.cloudflare.com/client/v4/accounts/{account_id}/r2/buckets/{BUCKET}/objects/{r2_path}'
    
    req = urllib.request.Request(
        url, method='GET',
        headers={'Authorization': f'Bearer {token}'}
    )
    
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        content = resp.read()
        with open(local_path, 'wb') as f:
            f.write(content)
        return True, f"Downloaded {len(content)} bytes"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, str(e)

def main():
    token = get_api_token()
    if not token:
        print("ERROR: No Cloudflare API token found.")
        print("Set: setx CLOUDFLARE_API_TOKEN \"your-token\"")
        print("Or create: ~/.cloudflare/api-token")
        sys.exit(1)
    
    account_id = get_account_id(token)
    if not account_id:
        print("ERROR: Cannot get Cloudflare account ID from API.")
        sys.exit(1)
    
    print(f"Account: {account_id}")
    
    # Parse command
    if '--batch' in sys.argv:
        idx = sys.argv.index('--batch')
        manifest_file = sys.argv[idx + 1]
        with open(manifest_file) as f:
            manifest = json.load(f)
        files = [(item['local'], item['remote'], item.get('action', 'upload')) 
                 for item in manifest.get('files', [])]
    elif len(sys.argv) >= 4:
        action = sys.argv[1]  # 'upload' or 'download'
        if action == 'upload':
            files = [(sys.argv[2], sys.argv[3], 'upload')]
        elif action == 'download':
            files = [(sys.argv[3], sys.argv[2], 'download')]
        else:
            print("Usage: python _r2_backup.py upload|download <file> <path>")
            print("       python _r2_backup.py --batch manifest.json")
            sys.exit(1)
    else:
        print("Usage: python _r2_backup.py upload <local_file> <r2_path>")
        print("       python _r2_backup.py download <r2_path> <local_file>")
        print("       python _r2_backup.py --batch manifest.json")
        sys.exit(1)
    
    results = []
    for local, remote, action in files:
        print(f"{action.upper()}: {local} <-> {BUCKET}/{remote} ... ", end='', flush=True)
        if action == 'upload':
            ok, msg = upload_to_r2(token, account_id, remote, local)
        else:
            ok, msg = download_from_r2(token, account_id, remote, local)
        print(f"{'OK' if ok else 'FAIL'}: {msg}")
        results.append({'local': local, 'remote': remote, 'action': action, 'ok': ok, 'msg': msg})
    
    ok_count = sum(1 for r in results if r['ok'])
    print(f"\n{ok_count}/{len(results)} operations successful")
    sys.exit(0 if ok_count == len(results) else 1)

if __name__ == '__main__':
    main()
