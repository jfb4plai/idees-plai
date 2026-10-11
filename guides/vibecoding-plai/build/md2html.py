"""Convertit le guide vibecoding (sous-ensemble Markdown) en page HTML PLAI."""
import html, re, sys

src, tpl, out = sys.argv[1:4]
lines = open(src, encoding='utf-8').read().split('\n')

def slug(t):
    t = re.sub(r'[^\w\s-]', '', t.lower())
    return re.sub(r'\s+', '-', t.strip())[:48]

def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<![\w*])\*([^*]+)\*(?![\w*])', r'<em>\1</em>', t)
    def lien(m):
        txt, url = m.group(1), m.group(2)
        ext = url.startswith('http')
        attrs = ' rel="noopener noreferrer"' if ext else ''
        return f'<a href="{url}"{attrs}>{txt}</a>'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lien, t)

body, toc = [], []
i, n_pre = 0, 0
title = subtitle = ''
while i < len(lines):
    l = lines[i]
    if l.startswith('# '):
        title = l[2:].strip(); i += 1; continue
    if l.startswith('**') and not title == '' and not subtitle and l.endswith('**') and not body:
        subtitle = l.strip('*'); i += 1; continue
    if l.startswith('```'):
        j = i + 1; buf = []
        while not lines[j].startswith('```'):
            buf.append(lines[j]); j += 1
        n_pre += 1
        pid = f'p{n_pre}'
        body.append(
            f'<div class="prompt"><pre id="{pid}" tabindex="0">{html.escape(chr(10).join(buf), quote=False)}</pre>'
            f'<div class="prompt-actions"><button type="button" class="btn" data-copier="{pid}">Copier</button>'
            f'<p class="statut" role="status" aria-live="polite"></p></div></div>')
        i = j + 1; continue
    if l.startswith('> [!'):
        kind = 'warning' if 'WARNING' in l else 'note'
        buf = []; i += 1
        while i < len(lines) and lines[i].startswith('>'):
            buf.append(lines[i][1:].strip()); i += 1
        items = [b for b in buf if b]
        lis = [b[2:] for b in items if b.startswith('- ')]
        txt = [b for b in items if not b.startswith('- ')]
        inner = ''.join(f'<p>{inline(t)}</p>' for t in txt)
        if lis: inner += '<ul>' + ''.join(f'<li>{inline(t)}</li>' for t in lis) + '</ul>'
        body.append(f'<aside class="callout {kind}">{inner}</aside>'); continue
    if l.startswith('## '):
        t = l[3:].strip(); s = slug(t); toc.append((s, t))
        body.append(f'</section>\n<section aria-labelledby="{s}"><h2 id="{s}">{inline(t)}</h2>'); i += 1; continue
    if l.startswith('### '):
        body.append(f'<h3>{inline(l[4:].strip())}</h3>'); i += 1; continue
    if l.strip() == '---':
        i += 1; continue
    if l.startswith('|'):
        rows = []
        while i < len(lines) and lines[i].startswith('|'):
            rows.append([c.strip() for c in lines[i].strip('|').split('|')]); i += 1
        h, data = rows[0], rows[2:]
        t = '<table><thead><tr>' + ''.join(f'<th scope="col">{inline(c)}</th>' for c in h) + '</tr></thead><tbody>'
        t += ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>' for r in data)
        body.append(t + '</tbody></table>'); continue
    m = re.match(r'^(\s*)(- |\d+\. )', l)
    if m:
        tag = 'ol' if m.group(2)[0].isdigit() else 'ul'
        items = []
        while i < len(lines) and re.match(r'^(- |\d+\. )', lines[i]):
            items.append(re.sub(r'^(- |\d+\. )', '', lines[i])); i += 1
        body.append(f'<{tag}>' + ''.join(f'<li>{inline(x)}</li>' for x in items) + f'</{tag}>'); continue
    if l.strip():
        buf = [l.strip()]; i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#|```|>|\||- |\d+\. |---)', lines[i]):
            buf.append(lines[i].strip()); i += 1
        body.append('<p>' + '<br>'.join(inline(b) for b in buf) + '</p>'); continue
    i += 1

contenu = '\n'.join(body)
contenu = contenu.replace('</section>\n', '', 1)  # première section : pas de fermeture
# La dernière section (crédits) part en pied de page.
contenu, sep, credits = contenu.rpartition('<p>Cette page est une adaptation')
credits = '<p>Cette page est une adaptation' + credits
sommaire = '\n'.join(f'<li><a href="#{s}">{inline(t)}</a></li>' for s, t in toc)
page = open(tpl, encoding='utf-8').read()
page = (page.replace('{{TITRE}}', html.escape(title)).replace('{{SOUSTITRE}}', html.escape(subtitle))
            .replace('{{SOMMAIRE}}', sommaire).replace('{{CONTENU}}', contenu + '</section>')
            .replace('{{CREDITS}}', credits))
open(out, 'w', encoding='utf-8').write(page)
print('prompts:', n_pre, 'sections:', len(toc))
