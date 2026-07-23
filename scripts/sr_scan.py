import os, re, json, datetime

today = '2026-07-23'
base = '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统'
results = []
total_md = 0
has_review_date = 0

for root, dirs, files in os.walk(base):
    for f in files:
        if not f.endswith('.md'):
            continue
        total_md += 1
        fp = os.path.join(root, f)
        try:
            with open(fp, 'r', encoding='utf-8') as fh:
                content = fh.read(2048)
            if not content.startswith('---'):
                continue
            end = content.find('---', 3)
            if end == -1:
                continue
            fm = content[3:end]
            m = re.search(r'review_date:\s*["\']?(\d{4}-\d{2}-\d{2})["\']?', fm)
            if not m:
                continue
            has_review_date += 1
            rd = m.group(1)
            title_m = re.search(r'title:\s*["\']?(.+?)["\']?\s*\n', fm)
            title = title_m.group(1).strip() if title_m else f.replace('.md','')
            rel_path = os.path.relpath(fp, base)

            if rd <= today:
                days_overdue = (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(rd)).days
                results.append({
                    'title': title,
                    'path': rel_path,
                    'review_date': rd,
                    'days_overdue': days_overdue,
                    'is_today': rd == today
                })
        except Exception as e:
            pass

results.sort(key=lambda x: (-x['days_overdue'], x['review_date']))

overdue_count = sum(1 for r in results if not r['is_today'])
today_count = sum(1 for r in results if r['is_today'])

output = {
    'date': today,
    'total_md_files': total_md,
    'has_review_date': has_review_date,
    'pending_count': len(results),
    'overdue_count': overdue_count,
    'today_count': today_count,
    'pending_notes': results
}

out_path = f'/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/04-巩固/今日待复习笔记-{today}.json'
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"total_md={total_md}")
print(f"has_review_date={has_review_date}")
print(f"pending={len(results)}")
print(f"overdue={overdue_count}")
print(f"today_due={today_count}")
print(f"output={out_path}")

for r in results:
    status = f"逾期 {r['days_overdue']} 天" if not r['is_today'] else "今日到期"
    print(f"  - {r['title']} | {status} | review_date={r['review_date']}")
