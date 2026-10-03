"""分野・出典の管理表を再生成する。カードの本文は各 txt に保持。"""
import json
from pathlib import Path
D=Path(__file__).resolve().parent.parent/'data/wordbook'
rows=[
('exam','試験制度','試験制度','第0部/ch0.html','2026年度秋の試験種目と評価対象を整理します。','試験種目の区別は学習計画の前提。','評価対象と解答の形式を理解する。','試験全体の運用に関する補足を確認する。'),
('reading','文章理解','知能分野','第1部/ch1-1.html','主張・根拠・論理関係と英文の読み方。','要旨と根拠の範囲を読み取る土台。','選択肢の言い換えや英文の構造を判定する。','細かな修辞や推論の落とし穴を補強する。'),
('logic','判断推理','知能分野','第1部/ch2-1.html','命題・集合・対応・順序・図形を条件から整理します。','条件の向きと矛盾の扱いが解法の土台。','対応表・順序・集合の標準的な整理法を定着する。','対称性や立体の扱いを補強する。'),
('math','数的推理','知能分野','第1部/ch3-1.html','割合・速さ・整数・確率・図形を式に直すための用語。','式を立てる前提となる量と単位の区別。','典型的な計算の仕組みと適用条件を定着する。','複合問題で使う発展的な見方を補強する。'),
('data','資料解釈','知能分野','第1部/ch4-1.html','表・グラフ・比率・統計を読み違えないための用語。','分母・基準・集計方法の確認が比較の土台。','変化率と代表値を適切に使い分ける。','調査や集計に伴う推論の限界を補強する。'),
('puremath','数学知識','自然科学','第1部/ch3-3.html','数的推理とは別に、関数・三角比・ベクトル・微積分の知識を整理します。','関数の条件と三角比の基本関係を先に定着する。','公式の適用条件と変形の仕組みを定着する。','極限など、数学的な見方を補強する。'),
('physics','物理','自然科学','第2部/ch5-1.html','力学・熱・波・電磁気の原理と成立条件。','力と運動・波の基本量が他の原理の土台。','2023・2025年度の力学・波に対応する論点と標準原理。','電磁気・光学などへ応用範囲を広げる。'),
('chemistry','化学','自然科学','第2部/ch5-2.html','物質・結合・反応・溶液・有機物を整理します。','原子・結合・物質量を先に定着する。','2023・2025年度の酸塩基・材料・溶液に対応する論点。','平衡・高分子・反応の理解を補強する。'),
('biology','生物','自然科学','第2部/ch5-3.html','細胞・遺伝・代謝・免疫・生態の用語。','細胞と遺伝情報の流れは各論の土台。','2023・2025年度の免疫・遺伝・細胞・感覚に対応する論点。','植物・生態・進化の知識を補強する。'),
('earth','地学','自然科学','第2部/ch5-4.html','地震・岩石・大気・海洋・天体をつなげます。','地球内部・天体の運動・大気の基本を定着する。','2023年度の火山、2025年度の惑星に対応する論点。','地史・気象・宇宙の理解を補強する。'),
('japan','日本史','人文科学','第2部/ch6-1.html','古代から現代まで、制度・事件・文化の時代を対応させます。','時代区分と政治制度の変化を先に定着する。','2023年度の中世制度、2025年度の宗教・文化に対応する論点。','周辺の社会・外交の流れを補強する。'),
('world','世界史','人文科学','第2部/ch6-2.html','地域・王朝・革命・国際秩序を時系列で整理します。','古代文明と近代への転換点を先に定着する。','2023年度の冷戦終結、2025年度の中世・交易に対応する論点。','地域間の関連と外交史を補強する。'),
('geography','地理','人文科学','第2部/ch6-3.html','地図・気候・農業・都市・人口分布を読みます。','地図と気候の読み方を先に定着する。','2023年度の都市、2025年度の地図に対応する論点。','産業立地と地域の比較を補強する。'),
('thought','思想','人文科学','第2部/ch6-4.html','思想家・主張・著作と、似た立場の違い。','認識・倫理・政治思想の主要な対立を定着する。','2023年度の日本思想、2025年度の現代思想に対応する論点。','周辺の思想家と主張の関係を補強する。'),
('arts','文学芸術','人文科学','第2部/ch6-5.html','作者・作品・様式・文化の時代を対応させます。','文学史・美術史の時代の流れを定着する。','2025年度の文学・日本文化に対応する作者と作品。','他地域・他分野の代表作品を補強する。'),
('politics','政治','社会科学','第2部/ch7-1.html','統治機構・選挙・民主政治・国際機関の用語。','立法・行政・司法と代表制の関係が土台。','2023・2025年度の統治・民主政治に対応する制度。','比較政治・国際協力の仕組みを補強する。'),
('law','法律','社会科学','第2部/ch7-3.html','憲法の人権・統治・財政・自治を条文から整理します。','人権保障と法の効力の基本を先に定着する。','2023・2025年度の憲法分野に対応する要件と例外。','条文間の関連や手続の違いを補強する。'),
('economics','経済','社会科学','第2部/ch7-2.html','市場・国民所得・金融・財政・国際経済の用語。','需要供給と名目・実質の違いが理解の土台。','2023〜2025年度の市場・GDP・金融に対応する論点。','市場の失敗・財政・貿易の仕組みを補強する。'),
('society','社会','社会科学','第2部/ch7-4.html','社会保障・労働・人口・社会学の概念と指標。','社会保障の分類と人口・労働指標を定着する。','2025年度の社会保障などに対応する制度の違い。','社会学の分析概念と格差の見方を補強する。'),
('info','情報','時事・情報','第2部/ch8-4.html','情報の表現・計算・安全性とデータ利用の基礎概念。','情報の単位と安全性の区別を先に定着する。','2023・2025年度の情報分野に対応する論点。','データ利用と計算の理解を補強する。'),
('environment','環境・国際協力','時事・情報','第2部/ch8-3.html','環境目標・気候対策・資源循環・国際協力の基礎。','目標の意味と対策の種類を先に定着する。','気候変動や資源・生物多様性の標準概念を定着する。','資源循環と被害の生じ方を補強する。')]
manifest=[dict(key=k,name=n,category=c,chapter=ch,intro=i,reasons=dict(A=a,B=b,C=x)) for k,n,c,ch,i,a,b,x in rows]
(D/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
sources={}
for year,part,qnums,pdf in [(2023,'II',[6,7,8,9,10,11,12,14,17,18,21,22,23,25,26,28,30],'000010519'),(2025,'II',[7,8,9,10,11,12,13,14,15,16,17,18,19,20,22,23,26,28,30],'000013933'),(2024,'II',[26],'000002973')]:
 for q in qnums:
  page=q+2 if year==2024 or (year==2025 and q>=8) else q+1
  sources[f'{year}{part}{q}']=dict(title=f'{year}年度・Ⅱ部 問{q}',url=f'https://www.jinji.go.jp/content/{pdf}.pdf#page={page}',checked='2026-10-04',scope='原本の論点。誤答選択肢も含むため定義の出典とは区別。')
sources['2025I11']=dict(title='2025年度・Ⅰ部 問11',url='https://www.jinji.go.jp/content/000016198.pdf#page=19',checked='2026-10-04')
sources['2025I23']=dict(title='2025年度・Ⅰ部 問23（資料部分）',url='https://www.jinji.go.jp/content/000016198.pdf#page=31',checked='2026-10-04')
primary=[('exam2026','人事院・2026年度秋受験案内','https://www.jinji.go.jp/content/900036094.pdf'),('constitution','日本国憲法（衆議院掲載）','https://www.shugiin.go.jp/Internet/itdb_annai.nsf/html/statics/shiryo/dl-constitution.htm'),('boj','日本銀行・金融政策の概要','https://www.boj.or.jp/mopo/outline/'),('welfare','厚生労働省・社会保障とは何か','https://www.mhlw.go.jp/stf/newpage_21479.html'),('labour','総務省統計局・労働力調査Q&A','https://www.stat.go.jp/data/roudou/qa-1.html'),('birth','厚生労働省・統計の比率と用語','https://www.mhlw.go.jp/toukei/kaisetu/index-hw.html'),('sdgs','外務省・SDGsとは','https://www.mofa.go.jp/mofaj/gaiko/oda/sdgs/about/index.html')]
for key,title,url in primary: sources[key]=dict(title=title,url=url,checked='2026-10-04')
primary2=[
('uncharter','国連広報センター・国連憲章23〜27条','https://www.unic.or.jp/info/un/charter/text_japanese/'),
('unveto','国連広報センター・拒否権の解説','https://www.unic.or.jp/files/print_archive/pdf/basic_knowledge/basic_knowledge_5.pdf'),
('courts','裁判所・違憲審査権（3ページ）','https://www.courts.go.jp/vc-files/courts/file2/20916002.pdf#page=3'),
('pension','厚生労働省・公的年金制度の財政方式','https://www.mhlw.go.jp/stf/nenkin_shikumi_004.html'),
('funded','厚生労働省・賦課方式と積立方式','https://www.mhlw.go.jp/nenkinkenshou/manga/05.html'),
('assistance','厚生労働省・生活保護制度','https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/hukushi_kaigo/seikatsuhogo/seikatuhogo/index.html'),
('snaintro','内閣府・GDPと三面等価の解説（2024年）','https://www.esri.cao.go.jp/jp/esri/esr/esr_report/esr_045/esr_045_l.pdf#page=2'),
('sna','内閣府・国民経済計算の用語解説（2021年版）','https://www.esri.cao.go.jp/jp/sna/data/data_list/kakuhou/files/2021/sankou/pdf/term.pdf'),
('realgdp','内閣府・名目値と実質値の違い','https://www.esri.cao.go.jp/jp/sna/otoiawase/faq/qa1.html'),
('cpi','総務省統計局・消費者物価指数Q&A','https://www.stat.go.jp/data/cpi/4-1.html'),
('population','総務省統計局・統計用語辞典','https://www.stat.go.jp/naruhodo/13_yougo/sa-gyo.html'),
('popchange','総務省統計局・人口推計の用語','https://www.stat.go.jp/data/jinsui/7.html'),
('paris','環境省・2019年版白書（協定の趣旨）','https://www.env.go.jp/policy/hakusyo/r01/html/hj19010202.html'),
('ndc','環境省・日本のNDC','https://www.env.go.jp/earth/earth/ondanka/ndc.html'),
('climate','環境省・カーボンニュートラルとは','https://ondankataisaku.env.go.jp/carbon_neutral/about/'),
('adaptation','環境省・緩和と適応','https://ondankataisaku.env.go.jp/carbon_neutral/topics/20240725-topic-59.html'),
('jma','気象庁・震度とマグニチュード','https://www.jma.go.jp/jma/kishou/know/faq/faq27.html')]
primary2.extend([
('mext3','文部科学省・情報Ⅰ研修教材 第3章','https://www.mext.go.jp/content/20200722-mxt_jogai02-100013300_005.pdf'),
('primarybalance','財務省・基礎的財政収支とは','https://www.mof.go.jp/faq/budget/01ad.htm'),
('circular','環境省・循環経済とは','https://policies.env.go.jp/recycle/circular_economy/about/index.html'),
('reuse','環境省・使用済製品等のリユース','https://www.env.go.jp/recycle/circul/reuse/'),
('biodiversity','環境省・生物多様性とはなにか','https://www.env.go.jp/guide/info/ecojin/oecmsites/20230719.html'),
('ecoservices','環境省・海洋生物多様性保全戦略 第3章','https://www.env.go.jp/nature/biodic/kaiyo-hozen/guideline/05-1.html'),
('naturepositive','環境省・ネイチャーポジティブ','https://policies.env.go.jp/nature/nature-positive/index.html'),
('abs','環境省・遺伝資源のアクセスと利益配分','https://policies.env.go.jp/nature/biodiversity/abs/')])
for key,title,url in primary2: sources[key]=dict(title=title,url=url,checked='2026-10-04')
(D/'sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
