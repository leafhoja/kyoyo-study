"""解説の正答番号・問題番号・ページ表記の回帰検証。解説本文の真偽は検証しない。

以下の正答表は2026-10-03に原本PDFの紙面画像と全件照合した転記。
2023: 23II部.pdf p32 https://www.jinji.go.jp/content/000010519.pdf
2024: 24II部.pdf p35 https://www.jinji.go.jp/content/000002973.pdf
2025: 25II部.pdf p33 https://www.jinji.go.jp/content/000013933.pdf
各ページにⅠ部・Ⅱ部の両方の正答表が掲載されている。
固定表との一致は原本の再取得や解法の検算を意味しない。
"""
from pathlib import Path
import re
root=Path(__file__).resolve().parent.parent / '過去問/解説'
keys={
'2023年度_Ⅰ部':[1,2,1,3,3,5,4,3,2,4,5,1,3,5,4,4,3,5,1,2,4,2,5,4],
'2023年度_Ⅱ部':[5,1,3,2,2,1,3,1,3,2,4,5,4,4,1,3,3,4,1,1,4,4,3,2,2,5,5,2,3,5],
'2024年度_Ⅰ部':[1,3,4,2,3,4,4,4,1,4,2,5,2,1,1,2,3,3,5,5,3,5,3,2],
'2024年度_Ⅱ部':[4,5,2,2,4,3,3,2,4,4,1,2,5,3,4,5,2,1,3,5,1,1,1,5,3,4,3,1,5,2],
'2025年度_Ⅰ部':[4,5,5,1,4,5,1,2,2,3,1,2,3,3,1,3,3,5,2,4,2,4,4,5],
'2025年度_Ⅱ部':[4,5,3,1,4,2,1,1,2,3,3,5,1,4,3,4,3,4,2,2,5,5,3,1,5,2,1,2,5,4]}
errors=[]
for stem,key in keys.items():
 s=(root/(stem+'.md')).read_text()
 blocks=re.split(r'^## 問(\d+)[^\n]*\n',s,flags=re.M)
 nums=[];actual=[]
 for i in range(1,len(blocks),2):
  n=int(blocks[i]);nums.append(n); b=blocks[i+1]
  m=re.search(r'(?:公式)?正答[：:]\s*([1-5])',b)
  if not m:errors.append(f'{stem}問{n} missing answer');continue
  a=int(m.group(1));actual.append(a)
  if n>len(key) or a!=key[n-1]:errors.append(f'{stem}問{n}: {a} != {key[n-1]}')
  if not re.search(r'PDF(?:の)?\s*[0-9０-９]+',b[:200]):errors.append(f'{stem}問{n} missing page')
 if nums!=list(range(1,len(key)+1)):errors.append(f'{stem} numbering {nums}')
 print(stem,len(nums),'問', '正答一致' if actual==key else '要確認')
for e in errors:print('ERROR',e)
if errors:raise SystemExit(1)
print('PASS: 162問の番号・転記済み正答表との一致・PDFページ表記（解説本文は対象外）')
