#!/usr/bin/env python3
"""独自講義例の条件を再計算・全候補列挙する。本文の全面的事実確認ではない。"""
from fractions import Fraction as F
from itertools import combinations, permutations, product
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
checks = 0


def check(label, actual, expected):
    global checks
    if actual != expected:
        raise AssertionError(f"{label}: {actual!r} != {expected!r}")
    checks += 1


class TableReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        if tag in ('td', 'th'):
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(''.join(self.cell).strip())
            self.cell = None
        if tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def logic():
    imply = lambda a, b: not a or b
    table = TableReader()
    table.feed((ROOT / '第1部/ch2-1.html').read_text())
    displayed = [r for r in table.rows if len(r) == 5 and r[0] in ('真', '偽')]
    expected = []
    for a, b in product((True, False), repeat=2):
        values = (a, b, imply(a, b), imply(b, a), imply(not b, not a))
        expected.append(['真' if v else '偽' for v in values])
        check('De Morgan AND', not (a and b), not a or not b)
        check('De Morgan OR', not (a or b), not a and not b)
    check('本文の含意・逆・対偶表', displayed, expected)
    # 二要素の集合モデル：P⊆Q、Q∩R=∅、S∩P≠∅。
    models = []
    for bits in product((False, True), repeat=8):
        p, q, r, s = (set(i for i, v in enumerate(bits[k:k+2]) if v)
                      for k in range(0, 8, 2))
        if p <= q and not q & r and s & p:
            models.append((p, q, r, s))
    check('存在命題の結論', all(s - r for p, q, r, s in models), True)
    check('全称へ強める反例の存在', any(s & r for p, q, r, s in models), True)
    duties = ['受付', '記録', '説明', '会計']
    solutions = [v for v in permutations(duties)
                 if v[0] not in ('受付', '会計') and v[1] == '説明'
                 and v[2] != '受付' and v[3] != '会計']
    check('四人の担当の一意性', solutions, [('記録', '説明', '会計', '受付')])
    weekdays = [v for v in permutations(('月', '火', '水'))
                if v[0] != '月' and imply(v[1] == '月', v[2] == '水')]
    check('曜日の全候補', set(weekdays), {('火','月','水'),('火','水','月'),('水','火','月')})
    positions = []
    for row in permutations('ABCDE'):
        pos = {v: i for i, v in enumerate(row)}
        if pos['B'] - pos['A'] == 2 and pos['C'] < pos['A'] and pos['B'] < pos['D']:
            positions.append(''.join(row))
    check('五人の位置の一意性', positions, ['CAEBD'])
    partial = [''.join(row) for row in permutations('ABCD')
               if row.index('A') < row.index('B') and row.index('C') < row.index('D')]
    check('部分順序の全候補', partial, ['ABCD','ACBD','ACDB','CABD','CADB','CDAB'])
    check('正直者と嘘つきの一意性',
          [(a, b) for a, b in product((False, True), repeat=2)
           if a == (not b) and b == (a != b)], [(False, True)])
    # 偽貨の位置を九つ全て試し、実際の二回計量で特定できるか確認。
    for fake in range(9):
        weights = [2 if i == fake else 1 for i in range(9)]
        left, right = sum(weights[:3]), sum(weights[3:6])
        group = list(range(0,3) if left > right else range(3,6) if left < right else range(6,9))
        x, y, z = group
        chosen = x if weights[x] > weights[y] else y if weights[x] < weights[y] else z
        check(f'偽貨位置{fake+1}', chosen, fake)
    for state in product((0, 1), repeat=5):
        for i, j in combinations(range(5), 2):
            changed = list(state)
            changed[i] ^= 1
            changed[j] ^= 1
            check('二枚反転の偶奇不変', sum(changed) % 2, sum(state) % 2)
    # 三集合の互いに素な領域：Aのみ/Bのみ/Cのみ/ABのみ/BCのみ/CAのみ/ABC/外。
    regions = (13, 9, 6, 6, 3, 4, 2, 7)
    a, b, c, ab, bc, ca, abc, outside = regions
    check('三集合の各集計値',
          (a+ab+ca+abc,b+ab+bc+abc,c+bc+ca+abc,ab+abc,bc+abc,ca+abc,abc,sum(regions)),
          (25,20,15,8,5,6,2,50))
    check('三集合の和集合', sum(regions[:-1]), 43)


def arithmetic():
    # 速さ：位置の一致、全距離・全時間へ戻して照合。
    check('向かい合う400m', (3*50+5*50, F(400,3+5)), (400,F(50)))
    check('追い付き位置', (80*10, 200+60*10), (800,800))
    check('時差出発', (4*F(3,2),6*1), (F(6),6))
    check('流水の二条件', (10+2,10-2), (12,8))
    check('通過距離', (15*20,15*8), (300,120))
    check('等距離平均', F(12)/(F(6,3)+F(6,6)), F(4))
    check('休憩込み距離・時間', (80*5+60*5,5+3+5), (700,13))
    # 濃度は溶質保存、損益は実売価と原価で再代入。
    check('損益の二条件', (1100*F(4,5), F(880-800,800)), (F(880),F(1,10)))
    check('混合8/20→12', F(300*8+150*20,300+150), F(12))
    check('混合10/20', F(200*10+100*20,300), F(40,3))
    check('比例配分', (F(80,120),F(120,150),80+120+150), (F(2,3),F(4,5),350))
    check('蒸発と取り出し', (F(20,150),F(15,150)), (F(2,15),F(1,10)))
    check('二回交換後の溶質と濃度', (20*F(3,4)**2,F(20,200)*F(3,4)**2), (F(45,4),F(9,160)))
    check('割合の逆算', 100*F(6,5)*F(3,4), F(90))
    # 全事象の列挙による確率。玉は個体を区別し一様抽出する。
    dice = list(product(range(1,7),repeat=2))
    check('和7', F(sum(a+b == 7 for a,b in dice),len(dice)), F(1,6))
    check('少なくとも一回6', F(sum(6 in row for row in dice),36), F(11,36))
    condition = [(a,b) for a,b in dice if a == 6]
    check('一個目6の条件付き', F(sum(a+b >= 8 for a,b in condition),len(condition)), F(5,6))
    for amount, minimum, answer in [(2,2,F(3,10)),(3,2,F(7,10))]:
        samples = list(combinations(range(5),amount))
        check('戻さない玉抽出', F(sum(sum(v < 3 for v in row) >= minimum for row in samples),len(samples)),answer)
    check('戻す玉抽出', F(3,5)**2,F(9,25))
    check('重複文字の並べ方', len(set(permutations('AABC'))),12)
    check('組合せと順列', (len(list(combinations(range(5),2))),len(list(permutations(range(5),2)))), (10,20))
    check('サイコロ期待値', F(sum(range(1,7)),6),F(7,2))
    check('直角三角形', (6**2+8**2,F(6*8,2),F(24*2,10)), (100,F(24),F(24,5)))
    check('扇形のπ係数', (F(2*6*120,360),F(6**2*120,360)),(F(4),F(12)))
    check('円柱と円錐のπ係数', (3**2*4,F(3**2*4,3)), (36,F(12)))
    check('長方形と中心三角形', (8*6,F(8*3,2)),(48,F(12)))
    check('立方体', (2**3,6*2**2,4**3,6*4**2), (8,24,64,96))
    check('仕事の段階合計', F(1,6)*4+F(1,3)*1,F(1))
    check('仕事共同二時間', 2*(F(1,6)+F(1,3)),F(1))
    check('追加者得点', 65*6-60*5,90)
    check('二種類の家具', (4+6,4*4+2*6),(10,28))
    check('連続整数', 23+24+25,72)
    check('余りの全候補', [n for n in range(1,31) if n%3==1 and n%5==2],[7,22])
    check('給排水', (F(1,6)-F(1,10))*15,F(1))
    check('売上の表', (F(45,150),F(150,20),F(150-100,100),F(45-40,40)),(F(3,10),F(15,2),F(1,2),F(1,8)))
    check('人数を重みとする比率', F(8+45,10+90),F(53,100))
    check('割合の割合', F(4,10)*F(25,100),F(1,10))
    check('比率の交差積', (31*100,44*70),(3100,3080))
    check('構成比から実数', (200*F(3,10),250*F(28,100),240*F(375,1000)),(F(60),F(70),F(90)))
    check('連続増減', 100*F(6,5)*F(9,10),F(108))
    check('加重成長率', F(9,10)*F(1,10)+F(1,10)*F(1,5),F(11,100))
    check('一定年成長率', F(11,10)**2,F(121,100))
    check('新構成比', F(1,5)*F(11,10)/F(5,4),F(22,125))
    check('25%減から回復', 1/F(3,4)-1,F(1,3))
    check('指数の逆算', (50*F(120,100),100*F(110,100),F(132,120)-1),(F(60),F(110),F(1,10)))
    check('集団構成の逆転', (F(10*50+90*80,100),F(90*55+10*85,100)),(F(77),F(58)))
    check('四捨五入の全整数候補', [n for n in range(201) if F(295,10)<=F(n*100,200)<F(305,10)],[59,60])
    check('二集合', (18+15-6,18+15-2*6,40-(18+15-6)),(27,21,13))
    check('符号化', (format(3,'05b'),format(6,'05b'),int('00101',2)),('00011','00110',5))
    check('100日後と100日目', (100%7,99%7),(2,1))


def science_economy_information():
    check('合力と加速度', (10-4,F(10-4,2)),(6,F(3)))
    check('落下エネルギー', (2*10*5,F(2*10**2,2)),(100,F(100)))
    check('並列回路', (F(6,3)+F(6,6),1/(F(1,3)+F(1,6)),6*(F(6,3)+F(6,6))), (F(3),F(2),F(18)))
    check('混合の熱収支', 100*(80-50),100*(50-20))
    check('反応の元素保存', (2*2,1*2),(2*2,2*1))
    check('近似質量保存', 2*2+1*32,2*18)
    check('不足反応物', (3-2*1,2*1),(1,2))
    check('モル濃度', F(1,2)/2,F(1,4))
    check('気体の比例', 2*F(600,300),F(4))
    check('メンデル配偶子の組合せ', sorted(a+b for a,b in product('Aa',repeat=2)),['AA','Aa','aA','aa'])
    check('均衡価格への代入', (100-2*20,20+2*20),(60,60))
    check('乗数モデルの代入', (20+F(4,5)*500+30+50,20+F(4,5)*550+30+60),(F(500),F(550)))
    check('名目から実質', F(210)/F(105,100),F(200))
    check('実質賃金倍率', F(105,100)/F(103,100)-1,F(2,103))
    check('高齢化率', (F(30,100),F(30,80)),(F(3,10),F(3,8)))
    check('異なる基準の排出量', (125*F(4,10),1-F(50,100)),(F(50),F(1,2)))
    check('失業率', F(5,100),F(1,20))
    check('画像データ量', (100*100*24,F(100*100*24,8)),(240000,F(30000)))
    check('送信単位変換', F(1000000*8,2000000),F(4))
    check('二進数', int('1101',2),13)
    check('5ビット', (2**5,2**5-1),(32,31))
    check('反復の途中値', [sum(range(1,n+1)) for n in range(5)],[0,1,3,6,10])
    table = TableReader()
    table.feed((ROOT / '第2部/ch8-4.html').read_text())
    displayed = [r for r in table.rows if len(r)==5 and r[0] in ('0','1')]
    check('本文のAND/OR/XOR表',displayed,
          [[str(a),str(b),str(a&b),str(a|b),str(a^b)] for a,b in product((0,1),repeat=2)])
    values = [1,1,1,1,11]
    check('平均と中央値', (F(sum(values),len(values)),sorted(values)[len(values)//2]),(F(3),1))


if __name__ == '__main__':
    logic()
    arithmetic()
    science_economy_information()
    print(f'PASS: {checks}件の条件代入・全候補・計量分岐・本文真理値表の検証')
    print('対象：独自講義例。公式正答番号、制度の現行性、解説全文の真偽は対象外。')
