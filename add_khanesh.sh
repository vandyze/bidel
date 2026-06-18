#!/bin/bash

# ── config ──────────────────────────────────────────────
API="https://bideli.ir/api"
TOKEN=$(curl -s -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"s@g.com\",\"password\":\"123456\"}" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token') or d.get('token',''))")
echo "==> Got token"

# ── args ────────────────────────────────────────────────
DOCX="$1"
SLUG="$2"
TITLE="$3"
TERJEE="$4"
INSTRUCTOR="$5"
ROLE="$6"
TAGS="$7"   # comma separated: هوش,غفلت,تقلید

if [ -z "$DOCX" ] || [ -z "$SLUG" ] || [ -z "$TITLE" ] || [ -z "$TERJEE" ]; then
  echo "Usage: ./add_khanesh.sh <file.docx> <slug> <title> <terjee_number> [instructor] [role] [tag1,tag2]"
  echo "Example: ./add_khanesh.sh report.docx hoosh-band-18 'هوش و غفلت' 18 'شروین وکیلی' 'پژوهشگر' 'هوش,غفلت'"
  exit 1
fi

# ── convert docx → html ─────────────────────────────────
echo "==> Converting $DOCX to HTML..."
CONTENT=$(python3 - << PYEOF
import sys
try:
    from docx import Document
except ImportError:
    print("ERROR: python-docx not installed.", file=sys.stderr)
    sys.exit(1)

doc = Document("$DOCX")
html = []
for para in doc.paragraphs:
    text = para.text.strip()
    if not text:
        continue
    style = ''
    try:
        style = para.style.name.lower() if para.style and para.style.name else ''
    except:
        style = ''
    if 'heading 1' in style:
        html.append(f'<h2>{text}</h2>')
    elif 'heading 2' in style or 'heading 3' in style:
        html.append(f'<h3>{text}</h3>')
    else:
        inner = ''
        for run in para.runs:
            t = run.text
            if not t:
                continue
            try:
                is_bold = run.bold
            except:
                is_bold = False
            if is_bold:
                inner += f'<em>{t}</em>'
            else:
                inner += t
        if inner.strip():
            html.append(f'<p>{inner}</p>')

print(''.join(html))
PYEOF
)

if [ -z "$CONTENT" ]; then
  echo "ERROR: conversion failed — check if python-docx is installed and file exists"
  exit 1
fi

# ── build tags array ────────────────────────────────────
TAGS_JSON=$(python3 -c "
tags = '$TAGS'.split(',') if '$TAGS' else []
tags = [t.strip() for t in tags if t.strip()]
import json; print(json.dumps(tags, ensure_ascii=False))
")

# ── build payload ───────────────────────────────────────
PAYLOAD=$(python3 -c "
import json, sys
payload = {
    'title': '$TITLE',
    'slug': '$SLUG',
    'content': sys.stdin.read(),
    'terjee_number': $TERJEE,
    'instructor': '$INSTRUCTOR',
    'role': '$ROLE',
    'tags': $TAGS_JSON,
    'published_at': '$(date -u +%Y-%m-%dT%H:%M:%S)'
}
print(json.dumps(payload, ensure_ascii=False))
" <<< "$CONTENT")

# ── call api ────────────────────────────────────────────
echo "==> Sending to API..."
RESPONSE=$(curl -s -v -X POST "$API/khanesh" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "$PAYLOAD")
echo "==> Raw response: $RESPONSE"

# ── check result ────────────────────────────────────────
if echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print('✓ OK — slug:', d.get('slug','?'))" 2>/dev/null; then
  echo "==> Done!"
else
  echo "==> ERROR — check response above"
  exit 1
fi
