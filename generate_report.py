"""
generate_report.py
Generates PDF reports — one Japanese, one English.
Run from the project root: python generate_report.py

Optional env vars (can be set in .env):
  SENDGRID_API_KEY        — enables PDF delivery by email
  REPORT_RECIPIENT_EMAIL  — who receives the report
  REPORT_SENDER_EMAIL     — verified sender address in SendGrid
  GOOGLE_SHEETS_KEY_PATH  — service account JSON for live data
  GOOGLE_SHEETS_TEMPLATE_ID — spreadsheet ID to load from
"""
import os, warnings, logging
warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
log = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()

import matplotlib
matplotlib.use('Agg')
import japanize_matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.image as mpimg
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.font_manager as fm
from datetime import date

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT   = os.path.dirname(os.path.abspath(__file__))
CHARTS = os.path.join(ROOT, 'output', 'charts')
OUT_JA = os.path.join(ROOT, 'output', 'report_sample_ja.pdf')
OUT_EN = os.path.join(ROOT, 'output', 'report_sample_en.pdf')
OUT    = os.path.join(ROOT, 'output', 'report_sample.pdf')   # legacy alias → JA

# ── Japanese font detection ───────────────────────────────────────────────────
def find_jp_font():
    # Prefer IPAexGothic (bundled by japanize-matplotlib) — works reliably with
    # matplotlib's PDF backend. Hiragino/Noto on macOS cause ASCII encoding errors.
    candidates = ['IPAexGothic', 'Yu Gothic', 'Meiryo', 'MS Gothic', 'MS UI Gothic']
    for name in candidates:
        try:
            path = fm.findfont(fm.FontProperties(family=name), fallback_to_default=False)
            if path and 'DejaVu' not in path:
                print(f'Japanese font found: {name}')
                return name
        except ValueError:
            continue
    print('Warning: no Japanese font found, falling back to default.')
    return 'sans-serif'

JP = find_jp_font()
plt.rcParams['font.family'] = JP

def fp(size=10, bold=False):
    return fm.FontProperties(family=JP, size=size,
                             weight='bold' if bold else 'normal')

# ── Design tokens ─────────────────────────────────────────────────────────────
W, H       = 8.27, 11.69   # A4 inches
PRIMARY    = '#2C7BB6'
DARK       = '#1A3A5C'
LIGHT_BG   = '#F7F9FC'
CALLOUT_BG = '#EBF5FB'
MID        = '#CCCCCC'
TEXT_COL   = '#2B2B2B'
SUB_COL    = '#666666'
TOTAL_PG   = 7

# ── String tables (ja / en) ───────────────────────────────────────────────────
STRINGS = {
    'ja': {
        # ── Cover ──
        'cover_main':       'Business Data Analysis Report',
        'cover_sub_jp':     '業務データ分析レポート',
        'cover_tagline':    'サンプル — 小売業 売上・顧客分析',
        'cover_scope_lbl':  '分析対象',
        'cover_scope_val':  'ECサイト 売上・顧客データ（2009–2011年）',
        'cover_items_lbl':  '分析項目',
        'cover_items': [
            '① データクレンジング・品質確認',
            '② 売上トレンド分析（月次・週次・前年比）',
            '③ 商品別パフォーマンス・パレート分析',
            '④ 顧客セグメント分析（RFM）',
        ],
        'cover_date_fn':    lambda d: f'作成日: {d.strftime("%Y年%m月%d日")}',
        'cover_author':     '作成者: シニアデータサイエンティスト',
        'cover_service':    'データ分析・レポート自動化サービス提供中',
        'cover_note':       '本レポートはサンプルです。実際の依頼内容に応じてカスタマイズします。',
        # ── KPI cards (big value, label, sub) ──
        'kpi_cards': [
            ('£17.7M', '総売上', '2009–2011年'),
            ('5,878',  '分析対象顧客数', 'クレンジング後'),
            ('上位20%', 'の商品が売上の80%を占める', 'パレートの法則'),
        ],
        # ── Executive Summary ──
        'sum_h':    'エグゼクティブサマリー',
        'sum_h_en': 'Executive Summary',
        'sum_bg_h': '分析の背景と目的',
        'sum_bg': (
            'あるECサイトが2年分の売上・顧客データを保有しているものの、データを経営判断に活かせていない状況でした。\n'
            '本分析では、売上トレンド・商品パフォーマンス・顧客行動の3つの観点から現状を整理し、\n'
            '次にとるべきアクションを提示しています。'
        ),
        'sum_findings_h': '主要な発見（3点）',
        'sum_findings': [
            ('売上は前年比で成長しているが、11月に集中する季節性が強い。\n'
             '　→ 9月中旬までに在庫・人員の準備が必要。'),
            ('上位20%の商品が売上の大半を占める（パレートの法則）。\n'
             '　→ 主力商品の欠品防止を最優先課題として管理すべき。'),
            ('優良顧客（Champions）は顧客全体の一部だが、売上への貢献度は突出して高い。\n'
             '　→ このセグメントの離脱防止策が最大のROIをもたらす。'),
        ],
        'sum_data_h': 'データ概要',
        'sum_data': [
            ('分析期間',      '2009年12月 〜 2011年12月'),
            ('取引レコード数', '約80万件（クレンジング後）'),
            ('対象顧客数',    '5,878名'),
            ('対象商品数',    '5,283品目'),
            ('対象国',       '英国を中心に40カ国以上'),
        ],
        # ── Sales Trend ──
        'trend_h':    '売上トレンド分析',
        'trend_h_en': 'Sales Trend Analysis',
        'trend_s1':   '月別売上推移（前年比較）',
        'trend_comment_h': '分析コメント',
        'trend_bullets': [
            '11月に売上が急増する季節性が2年連続で確認される。ホリデーシーズン需要が最大の変動要因。',
            '2011年の売上は前年比で成長しており、事業の基礎的な成長トレンドは維持されている。',
        ],
        'trend_callout': '在庫・人員の準備は9月中旬が限界ライン。ホリデー需要を逃さないための早期手配が収益を左右する。',
        'trend_s2':   '前月比変化率（月次）',
        # ── Product Performance ──
        'prod_h':    '商品別パフォーマンス分析',
        'prod_h_en': 'Product Performance Analysis',
        'prod_s1':   'パレート分析（売上集中度）',
        'prod_comment_h': '分析コメント',
        'prod_bullets': [
            '上位20%の商品が売上の大部分を占める「パレートの法則」が成立している。',
            '注文件数は多いが売上上位でない商品は、価格改定（値上げ）による利益改善の余地がある。',
        ],
        'prod_callout': '主力上位10品目の欠品ゼロが最優先。この10品目だけで全売上の約40%を支えている。',
        'prod_s2':   '売上上位20品目',
        # ── RFM ──
        'rfm_h':    '顧客セグメント分析（RFM）',
        'rfm_h_en': 'Customer Segmentation — RFM Analysis',
        'rfm_s1':   'セグメント別 顧客数・売上構成',
        'rfm_table_h': 'セグメント別 推奨アクション',
        'rfm_cols': ['セグメント', '特徴', '推奨アクション'],
        'rfm_rows': [
            ('Champions',       '#2C7BB6', '最近・頻繁・高額',    'VIP特典・新商品の先行案内で関係を深める'),
            ('Loyal Customers', '#4DAC26', '継続購入・関与高',    'ポイントプログラム・定期購入割引を提案'),
            ('At Risk',         '#FDAE61', '過去優良・最近なし',  '30日以内に限定クーポンで再来店を促す'),
            ('New Customers',   '#ABDDA4', '初回・少数回購入',    '購入後7日以内のフォローメールで2回目へ'),
            ('Lost',            '#D7191C', '長期未購入',           '再獲得キャンペーン or リスト管理へ移行'),
        ],
        'rfm_callout': 'Championsは顧客の約31%だが売上の76%を担う。このグループの離脱防止が最大ROIの施策。',
        # ── Detail ──
        'detail_h':     '補足分析',
        'detail_h_en':  'Supporting Analysis',
        'detail_rfm_h': 'スコア別 RFMヒートマップ',
        'detail_rfm_text': (
            '各セグメントのR（直近性）・F（頻度）・M（金額）の平均スコアを示します。'
            'Championsはすべてのスコアが高く、Lostはすべてが低いことが確認できます。'
        ),
        'detail_decomp_h': '季節性分解（トレンド・季節成分・ノイズ）',
        'detail_decomp_text': (
            '売上時系列を「長期トレンド」「季節性」「残差」に分解。'
            '季節性を除いても右肩上がりのトレンドが確認でき、事業の基礎成長が示されています。'
        ),
        # ── Appendix ──
        'app_h':     '分析手法・ご依頼について',
        'app_h_en':  'Methodology & Service Information',
        'app_meth_h': '分析手法について',
        'app_intro': (
            '本レポートは以下の手法・ツールを用いて作成しています。'
            '専門知識がなくても理解できるよう、結果はすべて日本語で解説しています。'
        ),
        'app_methods': [
            ('データクレンジング',
             'キャンセル・欠損・異常値の除去。分析に使えるデータだけを抽出します。'),
            ('トレンド分析',
             '月次・週次の集計と前年比較。季節性分解により構造的な成長トレンドを抽出します。'),
            ('パレート分析',
             '売上の集中度を可視化し、どの商品・顧客に注力すべきかを明確にします。'),
            ('RFM分析',
             '最終購入日・購入頻度・購入金額の3指標で顧客をスコアリングし、5グループに分類します。'),
        ],
        'app_contact_h': 'ご依頼・お問い合わせ',
        'app_contact_lines': [
            ('現役データサイエンティストが対応します。',           True,  PRIMARY),
            ('',                                                    False, TEXT_COL),
            ('・  ExcelやCSVファイルを送るだけでOK',               False, TEXT_COL),
            ('・  図表付き分析レポート（PDF or Excel）で納品',      False, TEXT_COL),
            ('・  わかりやすい日本語解説つき',                      False, TEXT_COL),
            ('・  データの目的が不明確でもご相談いただけます',      False, TEXT_COL),
            ('',                                                    False, TEXT_COL),
            ('まずはお気軽にメッセージをどうぞ。',                  True,  PRIMARY),
        ],
        'app_note': '本レポートはサンプルです。実際のご依頼内容に応じてカスタマイズした分析・レポートを作成します。',
        'footer_fn': lambda d: (
            f'本レポートは分析サービスのサンプルです　|　'
            f'作成日: {d.strftime("%Y年%m月%d日")}　|　'
            f'データ: UCI Online Retail II (CC BY 4.0)'
        ),
    },

    'en': {
        # ── Cover ──
        'cover_main':      'Business Data Analysis Report',
        'cover_sub_jp':    'Automated Retail Analytics',
        'cover_tagline':   'Sample Report — Retail Sales & Customer Analysis',
        'cover_scope_lbl': 'Data Source',
        'cover_scope_val': 'E-commerce Sales & Customer Data (2009–2011)',
        'cover_items_lbl': 'Analyses Included',
        'cover_items': [
            '①  Data Cleaning & Quality Assurance',
            '②  Sales Trend Analysis (Monthly / Weekly / YoY)',
            '③  Product Performance & Pareto Analysis',
            '④  Customer Segmentation (RFM)',
        ],
        'cover_date_fn':  lambda d: f'Report Date: {d.strftime("%B %d, %Y")}',
        'cover_author':   'Author: Senior Data Scientist',
        'cover_service':  'Available for freelance data analysis engagements',
        'cover_note':     'This is a sample report. Fully customised to your business data and goals.',
        # ── KPI cards ──
        'kpi_cards': [
            ('£17.7M', 'Total Revenue',        '2009–2011'),
            ('5,878',  'Customers Analysed',   'After data cleaning'),
            ('Top 20%', 'of products drive 80%', 'of revenue (Pareto)'),
        ],
        # ── Executive Summary ──
        'sum_h':    'エグゼクティブサマリー',
        'sum_h_en': 'Executive Summary',
        'sum_bg_h': 'Background & Objective',
        'sum_bg': (
            'An e-commerce retailer held two years of sales and customer data but lacked the\n'
            'tools to turn it into decisions. This report structures the data across three lenses\n'
            '— revenue trends, product performance, and customer behaviour — and surfaces next actions.'
        ),
        'sum_findings_h': 'Key Findings (3)',
        'sum_findings': [
            ('Revenue shows strong November seasonality, consistent across both years.\n'
             '  → Stock and staffing must be prepared by mid-September at the latest.'),
            ('The top 20% of products generate the majority of revenue (Pareto principle).\n'
             '  → Preventing stockouts on hero SKUs is the highest-leverage inventory action.'),
            ('Champion customers are a small share of the base but contribute a disproportionate\n'
             '  share of revenue. Retaining them delivers the best return on any retention spend.'),
        ],
        'sum_data_h': 'Dataset Snapshot',
        'sum_data': [
            ('Analysis Period',  'December 2009 – December 2011'),
            ('Transaction rows', '~805,000 (after cleaning)'),
            ('Unique customers', '5,878'),
            ('Unique products',  '5,283 SKUs'),
            ('Markets',          'UK-centric · 40+ countries'),
        ],
        # ── Sales Trend ──
        'trend_h':    '売上トレンド分析',
        'trend_h_en': 'Sales Trend Analysis',
        'trend_s1':   'Monthly Revenue — Year-on-Year Comparison',
        'trend_comment_h': 'Analysis Commentary',
        'trend_bullets': [
            'A November revenue spike is confirmed for two consecutive years, driven by holiday-season demand.',
            'Overall revenue grew year-on-year in 2011, confirming the underlying business growth trajectory.',
        ],
        'trend_callout': 'Inventory and staffing prep must begin by mid-September at the latest. Acting early on holiday demand is the single biggest revenue lever.',
        'trend_s2':   'Month-over-Month Revenue Change (%)',
        # ── Product Performance ──
        'prod_h':    '商品別パフォーマンス分析',
        'prod_h_en': 'Product Performance Analysis',
        'prod_s1':   'Pareto Analysis — Revenue Concentration',
        'prod_comment_h': 'Analysis Commentary',
        'prod_bullets': [
            'The Pareto principle holds: the top 20% of SKUs account for the large majority of revenue.',
            'High-order-frequency products with low revenue share are candidates for a modest price increase.',
        ],
        'prod_callout': 'Zero stockouts on the top 10 SKUs is the single most impactful supply-chain target — these items alone represent roughly 40% of total revenue.',
        'prod_s2':   'Top 20 Products by Revenue',
        # ── RFM ──
        'rfm_h':    '顧客セグメント分析（RFM）',
        'rfm_h_en': 'Customer Segmentation — RFM Analysis',
        'rfm_s1':   'Segment Distribution — Customer Count & Revenue Share',
        'rfm_table_h': 'Recommended Actions by Segment',
        'rfm_cols': ['Segment', 'Profile', 'Recommended Action'],
        'rfm_rows': [
            ('Champions',       '#2C7BB6', 'Recent · Frequent · High-value',  'VIP perks, early access to new products'),
            ('Loyal Customers', '#4DAC26', 'Repeat buyers, high engagement',   'Loyalty programme, subscription discounts'),
            ('At Risk',         '#FDAE61', 'Past high-value, recently quiet',  'Limited-time coupon within 30 days'),
            ('New Customers',   '#ABDDA4', 'First or second purchase',          '7-day post-purchase follow-up email'),
            ('Lost',            '#D7191C', 'Long-lapsed, no recent activity',  'Win-back campaign or retire from list'),
        ],
        'rfm_callout': 'Champions are ~31% of customers but drive ~76% of revenue. Protecting this group has a higher ROI than acquiring new customers.',
        # ── Detail ──
        'detail_h':     '補足分析',
        'detail_h_en':  'Supporting Analysis',
        'detail_rfm_h': 'RFM Score Heatmap by Segment',
        'detail_rfm_text': (
            'Average R (Recency), F (Frequency), and M (Monetary) scores per segment. '
            'Champions score high across all three dimensions; Lost customers score low across all three.'
        ),
        'detail_decomp_h': 'Seasonal Decomposition (Trend · Seasonality · Residual)',
        'detail_decomp_text': (
            'Revenue is decomposed into long-term trend, seasonal pattern, and residual noise. '
            'The upward trend persists after removing seasonality — confirming genuine underlying growth.'
        ),
        # ── Appendix ──
        'app_h':     '分析手法・ご依頼について',
        'app_h_en':  'Methodology & Service Information',
        'app_meth_h': 'Methodology',
        'app_intro': (
            'This report was produced using industry-standard analytical methods. '
            'Results are presented in plain language — no technical background required.'
        ),
        'app_methods': [
            ('Data Cleaning',
             'Removed cancellations, missing customer IDs, and invalid prices. Only reliable records enter the analysis.'),
            ('Trend Analysis',
             'Monthly and weekly aggregation with year-on-year comparison. Seasonal decomposition isolates structural growth.'),
            ('Pareto Analysis',
             'Visualises revenue concentration. Identifies which products and customers deserve the most focus.'),
            ('RFM Segmentation',
             'Scores customers on Recency, Frequency, and Monetary value, then classifies them into 5 actionable groups.'),
        ],
        'app_contact_h': 'Enquiries & Engagements',
        'app_contact_lines': [
            ('Active data scientist. Available for freelance analysis projects.',  True,  PRIMARY),
            ('',                                                                   False, TEXT_COL),
            ('·  Send your Excel or CSV — that\'s all we need to get started',   False, TEXT_COL),
            ('·  Delivered as a branded PDF or Excel workbook',                   False, TEXT_COL),
            ('·  Plain-language commentary with every chart',                     False, TEXT_COL),
            ('·  Happy to scope open-ended or unclear briefs',                    False, TEXT_COL),
            ('',                                                                   False, TEXT_COL),
            ('Get in touch — first conversation is free.',                         True,  PRIMARY),
        ],
        'app_note': 'This is a sample report. All analyses are customised to your actual business data and objectives.',
        'footer_fn': lambda d: (
            f'Sample report — analytical services  |  '
            f'Created: {d.strftime("%B %d, %Y")}  |  '
            f'Data: UCI Online Retail II (CC BY 4.0)'
        ),
    },
}

# ── Layout helpers ────────────────────────────────────────────────────────────

def new_fig():
    return plt.figure(figsize=(W, H), facecolor='white')

def add_header(fig, s, page_num):
    ax = fig.add_axes([0, 0.938, 1, 0.062])
    ax.set_facecolor(PRIMARY)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    ax.text(0.035, 0.64, s[0], color='white', fontsize=13,
            va='center', fontproperties=fp(13, bold=True))
    ax.text(0.035, 0.19, s[1], color='#AACFE8', fontsize=8.5,
            va='center', fontproperties=fp(8.5))
    ax.text(0.965, 0.5, f'{page_num} / {TOTAL_PG}', color='white',
            fontsize=8.5, va='center', ha='right')

def add_footer(fig, footer_text):
    ax = fig.add_axes([0, 0, 1, 0.032])
    ax.set_facecolor(LIGHT_BG); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    ax.plot([0.03, 0.97], [0.88, 0.88], color=MID, linewidth=0.5)
    ax.text(0.5, 0.36, footer_text, color=SUB_COL, fontsize=6.5,
            ha='center', va='center', fontproperties=fp(6.5))

def load_chart(name):
    path = os.path.join(CHARTS, name)
    return mpimg.imread(path) if os.path.exists(path) else None

def section_label(fig, y, text):
    ax = fig.add_axes([0.04, y, 0.004, 0.021])
    ax.set_facecolor(PRIMARY); ax.axis('off')
    fig.text(0.053, y + 0.017, text, color=DARK, fontsize=10.5,
             va='top', fontproperties=fp(10.5, bold=True))

def bullets(fig, y_start, items, line_h=0.063):
    for i, item in enumerate(items):
        y = y_start - i * line_h
        fig.text(0.06, y, '▶', color=PRIMARY, fontsize=9.5, va='top')
        fig.text(0.082, y, item, color=TEXT_COL, fontsize=9.5, va='top',
                 linespacing=1.55, fontproperties=fp(9.5))

def kpi_cards(fig, cards, y_bottom=0.640, height=0.115):
    """Draw n evenly-spaced metric cards with a big number, label, and sub-text."""
    n = len(cards)
    gap = 0.018
    total_w = 0.90
    card_w = (total_w - (n - 1) * gap) / n
    x_start = 0.05

    for i, (big_val, label, sub) in enumerate(cards):
        x = x_start + i * (card_w + gap)

        ax = fig.add_axes([x, y_bottom, card_w, height])
        ax.set_facecolor(LIGHT_BG)
        for sp in ax.spines.values():
            sp.set_edgecolor(MID); sp.set_linewidth(0.8)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')

        # Left accent bar
        ax_bar = fig.add_axes([x, y_bottom, 0.007, height])
        ax_bar.set_facecolor(PRIMARY); ax_bar.axis('off')

        ax.text(0.5, 0.72, big_val, color=PRIMARY, fontsize=18,
                ha='center', va='center',
                fontproperties=fp(18, bold=True))
        ax.text(0.5, 0.40, label, color=DARK, fontsize=8.5,
                ha='center', va='center', fontproperties=fp(8.5, bold=True))
        ax.text(0.5, 0.14, sub, color=SUB_COL, fontsize=7.5,
                ha='center', va='center', fontproperties=fp(7.5))

def callout_box(fig, y_bottom, text, height=0.062):
    """A tinted key-takeaway box with an arrow prefix."""
    ax = fig.add_axes([0.04, y_bottom, 0.92, height])
    ax.set_facecolor(CALLOUT_BG)
    for sp in ax.spines.values():
        sp.set_edgecolor(PRIMARY); sp.set_linewidth(1.2)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    ax.text(0.018, 0.52, '→', color=PRIMARY, fontsize=13, va='center',
            fontproperties=fp(13, bold=True))
    ax.text(0.055, 0.50, text, color=DARK, fontsize=9.2, va='center',
            linespacing=1.45, fontproperties=fp(9.2, bold=True))


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1 — COVER
# ─────────────────────────────────────────────────────────────────────────────
def page_cover(pdf, lang='ja'):
    s = STRINGS[lang]
    fig = new_fig()

    ax_top = fig.add_axes([0, 0.77, 1, 0.23])
    ax_top.set_facecolor(DARK); ax_top.axis('off')
    ax_top.text(0.5, 0.73, s['cover_main'],
                color='white', fontsize=22, fontweight='bold',
                ha='center', va='center')
    ax_top.text(0.5, 0.44, s['cover_sub_jp'],
                color='#AACFE8', fontsize=17, ha='center', va='center',
                fontproperties=fp(17))
    ax_top.text(0.5, 0.16, s['cover_tagline'],
                color='#7BAFD4', fontsize=11, ha='center', va='center',
                fontproperties=fp(11))

    ax_line = fig.add_axes([0, 0.756, 1, 0.014])
    ax_line.set_facecolor(PRIMARY); ax_line.axis('off')

    fig.text(0.5, 0.695, s['cover_scope_lbl'], color=SUB_COL, fontsize=9,
             ha='center', fontproperties=fp(9))
    fig.text(0.5, 0.655, s['cover_scope_val'],
             color=TEXT_COL, fontsize=11.5, ha='center', fontweight='bold',
             fontproperties=fp(11.5, bold=True))

    fig.text(0.5, 0.595, s['cover_items_lbl'], color=SUB_COL, fontsize=9,
             ha='center', fontproperties=fp(9))
    for j, item in enumerate(s['cover_items']):
        fig.text(0.5, 0.555 - j * 0.048, item,
                 color=TEXT_COL, fontsize=10.5, ha='center',
                 fontproperties=fp(10.5))

    ax_div = fig.add_axes([0.15, 0.27, 0.70, 0.0012])
    ax_div.set_facecolor(MID); ax_div.axis('off')

    today = date.today()
    fig.text(0.5, 0.245, s['cover_date_fn'](today),
             color=SUB_COL, fontsize=9, ha='center', fontproperties=fp(9))
    fig.text(0.5, 0.205, s['cover_author'],
             color=SUB_COL, fontsize=9, ha='center', fontproperties=fp(9))
    fig.text(0.5, 0.163, s['cover_service'],
             color=PRIMARY, fontsize=9, ha='center', fontproperties=fp(9))

    ax_bot = fig.add_axes([0, 0, 1, 0.05])
    ax_bot.set_facecolor(DARK); ax_bot.axis('off')
    ax_bot.text(0.5, 0.5, s['cover_note'],
                color='#7BAFD4', fontsize=8, ha='center', va='center',
                fontproperties=fp(8))

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)
    print('  Page 1 (Cover) OK')


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2 — EXECUTIVE SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
def page_summary(pdf, lang='ja'):
    s = STRINGS[lang]
    fig = new_fig()
    add_header(fig, (s['sum_h'], s['sum_h_en']), 2)
    add_footer(fig, s['footer_fn'](date.today()))

    # Background & objective
    section_label(fig, 0.875, s['sum_bg_h'])
    fig.text(0.06, 0.840,
             s['sum_bg'],
             color=TEXT_COL, fontsize=9.5, va='top', linespacing=1.7,
             fontproperties=fp(9.5))

    # KPI metric cards
    kpi_cards(fig, s['kpi_cards'], y_bottom=0.680, height=0.118)

    # Key findings
    section_label(fig, 0.644, s['sum_findings_h'])
    for i, text in enumerate(s['sum_findings']):
        y = 0.606 - i * 0.095
        ax_c = fig.add_axes([0.055, y - 0.006, 0.026, 0.026])
        circ = plt.Circle((0.5, 0.5), 0.5, color=PRIMARY)
        ax_c.add_patch(circ)
        ax_c.set_xlim(0, 1); ax_c.set_ylim(0, 1); ax_c.axis('off')
        ax_c.text(0.5, 0.5, str(i + 1), color='white', fontsize=10,
                  fontweight='bold', ha='center', va='center')
        fig.text(0.093, y, text, color=TEXT_COL, fontsize=9.5, va='top',
                 linespacing=1.65, fontproperties=fp(9.5))

    # Dataset snapshot (compact table)
    section_label(fig, 0.318, s['sum_data_h'])
    for i, (label, value) in enumerate(s['sum_data']):
        y_row = 0.270 - i * 0.044
        bg = LIGHT_BG if i % 2 == 0 else 'white'
        ax_row = fig.add_axes([0.05, y_row - 0.003, 0.90, 0.040])
        ax_row.set_facecolor(bg); ax_row.axis('off')
        fig.text(0.07, y_row + 0.013, label, color=SUB_COL, fontsize=9,
                 va='center', fontproperties=fp(9))
        fig.text(0.38, y_row + 0.013, value, color=TEXT_COL, fontsize=9.5,
                 va='center', fontproperties=fp(9.5))

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)
    print('  Page 2 (Executive Summary) OK')


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 3 — SALES TREND
# ─────────────────────────────────────────────────────────────────────────────
def page_trend(pdf, lang='ja'):
    s = STRINGS[lang]
    fig = new_fig()
    add_header(fig, (s['trend_h'], s['trend_h_en']), 3)
    add_footer(fig, s['footer_fn'](date.today()))

    section_label(fig, 0.875, s['trend_s1'])
    chart = load_chart('monthly_revenue_yoy.png')
    if chart is not None:
        ax = fig.add_axes([0.04, 0.558, 0.92, 0.304])
        ax.imshow(chart); ax.axis('off')

    section_label(fig, 0.528, s['trend_comment_h'])
    bullets(fig, 0.494, s['trend_bullets'], line_h=0.063)

    callout_box(fig, 0.345, s['trend_callout'])

    section_label(fig, 0.310, s['trend_s2'])
    chart2 = load_chart('mom_revenue_change.png')
    if chart2 is not None:
        ax2 = fig.add_axes([0.04, 0.060, 0.92, 0.236])
        ax2.imshow(chart2); ax2.axis('off')

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)
    print('  Page 3 (Sales Trend) OK')


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 4 — PRODUCT PERFORMANCE
# ─────────────────────────────────────────────────────────────────────────────
def page_products(pdf, lang='ja'):
    s = STRINGS[lang]
    fig = new_fig()
    add_header(fig, (s['prod_h'], s['prod_h_en']), 4)
    add_footer(fig, s['footer_fn'](date.today()))

    section_label(fig, 0.875, s['prod_s1'])
    chart = load_chart('pareto_revenue.png')
    if chart is not None:
        ax = fig.add_axes([0.04, 0.568, 0.92, 0.294])
        ax.imshow(chart); ax.axis('off')

    section_label(fig, 0.538, s['prod_comment_h'])
    bullets(fig, 0.504, s['prod_bullets'], line_h=0.062)

    callout_box(fig, 0.352, s['prod_callout'])

    section_label(fig, 0.316, s['prod_s2'])
    chart2 = load_chart('top20_products_revenue.png')
    if chart2 is not None:
        ax2 = fig.add_axes([0.04, 0.060, 0.92, 0.242])
        ax2.imshow(chart2); ax2.axis('off')

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)
    print('  Page 4 (Products) OK')


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 5 — CUSTOMER SEGMENTATION
# ─────────────────────────────────────────────────────────────────────────────
def page_rfm(pdf, lang='ja'):
    s = STRINGS[lang]
    fig = new_fig()
    add_header(fig, (s['rfm_h'], s['rfm_h_en']), 5)
    add_footer(fig, s['footer_fn'](date.today()))

    section_label(fig, 0.875, s['rfm_s1'])
    chart_seg = load_chart('rfm_segment_distribution.png')
    chart_rev  = load_chart('rfm_revenue_by_segment.png')
    if chart_seg is not None:
        ax1 = fig.add_axes([0.02, 0.608, 0.47, 0.255])
        ax1.imshow(chart_seg); ax1.axis('off')
    if chart_rev is not None:
        ax2 = fig.add_axes([0.51, 0.608, 0.47, 0.255])
        ax2.imshow(chart_rev); ax2.axis('off')

    section_label(fig, 0.578, s['rfm_table_h'])

    # Table header
    hdr_y = 0.536
    ax_h = fig.add_axes([0.04, hdr_y, 0.92, 0.026])
    ax_h.set_facecolor(DARK); ax_h.axis('off')
    for x, lbl in zip([0.01, 0.30, 0.52], s['rfm_cols']):
        ax_h.text(x + 0.01, 0.5, lbl, color='white', fontsize=8.5, va='center',
                  fontproperties=fp(8.5))

    row_h = 0.068
    for i, (seg, color, feature, action) in enumerate(s['rfm_rows']):
        y = hdr_y - (i + 1) * row_h
        bg = LIGHT_BG if i % 2 == 0 else 'white'
        ax_row = fig.add_axes([0.04, y, 0.92, row_h - 0.003])
        ax_row.set_facecolor(bg); ax_row.axis('off')
        ax_dot = fig.add_axes([0.042, y + row_h * 0.26, 0.010, row_h * 0.46])
        ax_dot.set_facecolor(color); ax_dot.axis('off')
        mid_y = y + row_h * 0.50
        fig.text(0.060, mid_y, seg, color=color, fontsize=8.5, va='center',
                 fontproperties=fp(8.5, bold=True))
        fig.text(0.310, mid_y, feature, color=TEXT_COL, fontsize=8.5, va='center',
                 fontproperties=fp(8.5))
        fig.text(0.525, mid_y, action, color=TEXT_COL, fontsize=8.5, va='center',
                 fontproperties=fp(8.5))

    # Callout box below table
    callout_box(fig, 0.040, s['rfm_callout'], height=0.060)

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)
    print('  Page 5 (RFM) OK')


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 6 — SUPPORTING ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
def page_detail(pdf, lang='ja'):
    s = STRINGS[lang]
    fig = new_fig()
    add_header(fig, (s['detail_h'], s['detail_h_en']), 6)
    add_footer(fig, s['footer_fn'](date.today()))

    section_label(fig, 0.875, s['detail_rfm_h'])
    chart_heat = load_chart('rfm_heatmap.png')
    if chart_heat is not None:
        ax = fig.add_axes([0.04, 0.636, 0.92, 0.225])
        ax.imshow(chart_heat); ax.axis('off')
    fig.text(0.06, 0.618, s['detail_rfm_text'],
             color=TEXT_COL, fontsize=9.5, va='top', linespacing=1.6,
             fontproperties=fp(9.5))

    section_label(fig, 0.548, s['detail_decomp_h'])
    fig.text(0.06, 0.514, s['detail_decomp_text'],
             color=TEXT_COL, fontsize=9.5, va='top', linespacing=1.6,
             fontproperties=fp(9.5))
    chart_decomp = load_chart('seasonal_decomposition.png')
    if chart_decomp is not None:
        ax2 = fig.add_axes([0.04, 0.052, 0.92, 0.448])
        ax2.imshow(chart_decomp); ax2.axis('off')

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)
    print('  Page 6 (Detail) OK')


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 7 — METHODOLOGY + SERVICE INFO
# ─────────────────────────────────────────────────────────────────────────────
def page_appendix(pdf, lang='ja'):
    s = STRINGS[lang]
    fig = new_fig()
    add_header(fig, (s['app_h'], s['app_h_en']), 7)
    add_footer(fig, s['footer_fn'](date.today()))

    section_label(fig, 0.875, s['app_meth_h'])
    fig.text(0.06, 0.838, s['app_intro'],
             color=TEXT_COL, fontsize=9.5, va='top', linespacing=1.7,
             fontproperties=fp(9.5))

    for i, (title, desc) in enumerate(s['app_methods']):
        y = 0.783 - i * 0.082
        fig.text(0.06, y, f'■  {title}', color=PRIMARY, fontsize=10,
                 va='top', fontproperties=fp(10, bold=True))
        fig.text(0.06, y - 0.031, desc, color=TEXT_COL, fontsize=9.5,
                 va='top', fontproperties=fp(9.5))

    ax_div = fig.add_axes([0.05, 0.445, 0.90, 0.0012])
    ax_div.set_facecolor(MID); ax_div.axis('off')

    section_label(fig, 0.424, s['app_contact_h'])

    ax_box = fig.add_axes([0.05, 0.170, 0.90, 0.228])
    ax_box.set_facecolor(LIGHT_BG)
    for sp in ax_box.spines.values():
        sp.set_edgecolor(MID); sp.set_linewidth(0.6)
    ax_box.set_xlim(0, 1); ax_box.set_ylim(0, 1); ax_box.axis('off')

    for i, (line, bold, color) in enumerate(s['app_contact_lines']):
        ax_box.text(0.04, 0.92 - i * 0.113, line, color=color, fontsize=9.5,
                    va='top', fontproperties=fp(9.5, bold=bold))

    fig.text(0.5, 0.125, s['app_note'],
             color=SUB_COL, fontsize=8.5, ha='center', va='top',
             fontproperties=fp(8.5))

    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)
    print('  Page 7 (Appendix) OK')


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def build_pdf(path, lang):
    with PdfPages(path) as pdf:
        page_cover(pdf, lang)
        page_summary(pdf, lang)
        page_trend(pdf, lang)
        page_products(pdf, lang)
        page_rfm(pdf, lang)
        page_detail(pdf, lang)
        page_appendix(pdf, lang)

        d = pdf.infodict()
        d['Title']   = 'Business Data Analysis Report — Sample'
        d['Author']  = 'Senior Data Scientist'
        d['Subject'] = '売上・顧客データ分析レポート（サンプル）'

    print(f'  → {path}')


if __name__ == '__main__':
    os.makedirs(os.path.join(ROOT, 'output'), exist_ok=True)

    print(f'\nGenerating Japanese report ...')
    build_pdf(OUT_JA, 'ja')

    print(f'\nGenerating English report ...')
    build_pdf(OUT_EN, 'en')

    # Keep legacy path in sync with JA version
    import shutil
    shutil.copy2(OUT_JA, OUT)
    print(f'\nDone. Reports saved to output/')
    print(f'Run .venv/bin/python deliver_report.py to send.')
