import json
import os
import re
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
REPO = re.compile(r'^https://github\.com/([\w.-]+)/([\w.-]+)/?$')

def get_json(url, headers=None):
    request = urllib.request.Request(url, headers={'User-Agent': 'RepoLens', **(headers or {})})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)

def inspect_repo(url, question):
    match = REPO.fullmatch(url.strip())
    if not match:
        raise ValueError('请输入公开 GitHub 仓库地址，例如 https://github.com/owner/repo')
    owner, repo = match.groups()
    api = f'https://api.github.com/repos/{owner}/{repo}'
    info = get_json(api)
    tree = get_json(api + '/git/trees/' + urllib.parse.quote(info['default_branch'], safe='') + '?recursive=1')
    files = [x for x in tree.get('tree', []) if x['type'] == 'blob' and x.get('size', 0) < 50000 and re.search(r'\.(py|js|ts|tsx|jsx|md|go|rs|java)$', x['path'], re.I)]
    words = set(re.findall(r'[\w]+', question.lower()))
    files.sort(key=lambda x: sum(w in x['path'].lower() for w in words), reverse=True)
    excerpts = []
    for f in files[:8]:
        data = get_json(api + '/contents/' + urllib.parse.quote(f['path']) + '?ref=' + urllib.parse.quote(info['default_branch'], safe=''))
        import base64
        content = base64.b64decode(data.get('content', '')).decode('utf-8', errors='replace')[:10000]
        excerpts.append({'path': f['path'], 'url': data.get('html_url'), 'content': content})
    return info, excerpts, tree.get('truncated', False)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = (ROOT / 'index.html').read_bytes()
        self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            info, excerpts, truncated = inspect_repo(data.get('url', ''), data.get('question', ''))
            result = {'repo': info['full_name'], 'description': info.get('description'), 'files': [{'path': f['path'], 'url': f['url']} for f in excerpts], 'truncated': truncated}
            key = os.environ.get('OPENAI_API_KEY')
            if key:
                prompt = '请根据以下代码回答问题，引用具体文件路径；证据不足时明确说明。\n问题：' + data.get('question', '') + '\n' + json.dumps(excerpts, ensure_ascii=False)
                req = urllib.request.Request('https://api.openai.com/v1/responses', data=json.dumps({'model': os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini'), 'input': prompt}).encode(), headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, method='POST')
                with urllib.request.urlopen(req, timeout=90) as response:
                    answer = json.load(response)
                result['answer'] = '\n'.join(part.get('text', '') for item in answer.get('output', []) for part in item.get('content', []) if part.get('type') == 'output_text')
            else:
                result['answer'] = '已完成仓库文件检索。设置 OPENAI_API_KEY 后可生成 AI 回答。'
            body = json.dumps(result, ensure_ascii=False).encode()
            self.send_response(200)
        except Exception as e:
            body = json.dumps({'error': str(e)}, ensure_ascii=False).encode(); self.send_response(400)
        self.send_header('Content-Type', 'application/json; charset=utf-8'); self.end_headers(); self.wfile.write(body)

if __name__ == '__main__':
    print('RepoLens: http://127.0.0.1:8000')
    HTTPServer(('127.0.0.1', 8000), Handler).serve_forever()

