"""Parse my_runs.html (SKOB results archive page) into a list of race dicts."""
import re, sys, json, html

def parse(path):
    t = open(path, encoding="utf-8").read()
    body = t[t.find("<tbody"):t.find("</tbody>")]
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S):
        tds = []
        for a, c in re.findall(r"<td([^>]*)>(.*?)</td>", row, re.S):
            m = re.search(r'data-value="([^"]*)"', a)
            tds.append((m.group(1) if m else "", c))
        if len(tds) < 8:
            continue
        txt = lambda s: re.sub(r"\s+", " ", html.unescape(html.unescape(re.sub(r"<[^>]+>", " ", s)))).strip()
        cell = tds[1][1]
        link = re.search(r'href="([^"]+)"', cell)
        name = txt(re.sub(r'<span class="(badge|evdetail)[^"]*".*?</span>', "", cell, flags=re.S))
        flag = re.search(r'class="badge vlajka"[^>]*title="([^"]+)"', cell)
        det = re.search(r'class="evdetail">(.*?)</span>', cell, re.S)
        out.append(dict(
            date=tds[0][0], name=name, link=link.group(1) if link else "",
            country=flag.group(1) if flag else "", detail=txt(det.group(1)) if det else "",
            runner=txt(tds[2][1]), category=txt(tds[3][1]), place=txt(tds[4][1]),
            time_s=int(tds[5][0]) if tds[5][0].isdigit() else None,
            source=txt(tds[8][1]) if len(tds) > 8 else ""))
    return out

if __name__ == "__main__":
    json.dump(parse(sys.argv[1]), sys.stdout, ensure_ascii=False, indent=1)
