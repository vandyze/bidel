#!/bin/bash

API="https://bideli.ir/api"
SLUG="$1"

# get token
TOKEN=$(curl -s -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"YOUR_EMAIL","password":"YOUR_PASSWORD"}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

# download current
curl -s "$API/khanesh/$SLUG" > /tmp/kh_current.json

# re-run conversion and update tags
DOCX="$2"
TAGS="$3"

CONTENT=$(python3 - << PYEOF
import sys, re
from docx import Document
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
            inner += f'<em>{t}</em>' if is_bold else t
        if inner.strip():
            html.append(f'<p>{inner}</p>')
print(''.join(html))
PYEOF
)

TAGS_JSON=$(python3 -c "
import json, re
tags = re.split(r'[,،]', '$TAGS') if '$TAGS' else []
tags = [t.strip() for t in tags if t.strip()]
print(json.dumps(tags, ensure_ascii=False))
")

PAYLOAD=$(python3 -c "
import json, sys
current = json.load(open('/tmp/kh_current.json'))
current['content'] = sys.stdin.read()
current['tags'] = $TAGS_JSON
print(json.dumps(current, ensure_ascii=False))
" <<< "$CONTENT")

RESPONSE=$(curl -s -X PUT "$API/khanesh/$SLUG" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "$PAYLOAD")

echo "Response: $RESPONSE"
