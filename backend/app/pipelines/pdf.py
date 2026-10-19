"""Styled PDF output (reportlab): reading material from markdown, and quiz paper."""
import re
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (HRFlowable, Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from ..config import OUTPUTS

INDIGO, DARK, ORANGE, GREEN = "#4F46E5", "#1E1B4B", "#F97316", "#10B981"
SOFT, TEXT, MUTED = "#EEF2FF", "#1F2937", "#6B7280"
PAGE_W = A4[0] - 4 * cm

_REPL = {"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": " - ", "−": "-", "→": "->",
         "←": "<-", "✓": "", "✔": "", " ": " ", " ": " ", " ": " ", "•": "*"}


def clean(t: str) -> str:
    """Helvetica only covers Latin-1/WinAnsi: map or drop anything else."""
    for a, b in _REPL.items():
        t = t.replace(a, b)
    return t.encode("cp1252", "ignore").decode("cp1252")


def inline(t: str) -> str:
    t = escape(clean(t))
    t = re.sub(r"==(.+?)==", r'<font backColor="#FEF08A">\1</font>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    t = re.sub(r"`(.+?)`", r'<font name="Courier" color="#B45309">\1</font>', t)
    return t


def S(name, **kw):
    base = dict(fontName="Helvetica", fontSize=11, leading=16.5, textColor=colors.HexColor(TEXT))
    base.update(kw)
    return ParagraphStyle(name, **base)


ST = {
    "body": S("body", spaceAfter=6),
    "h2": S("h2", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.HexColor(INDIGO),
            spaceBefore=16, spaceAfter=2, keepWithNext=1),
    "h3": S("h3", fontName="Helvetica-Bold", fontSize=13.5, leading=18, textColor=colors.HexColor(DARK),
            spaceBefore=10, spaceAfter=4, keepWithNext=1),
    "bullet": S("bullet", leftIndent=20, bulletIndent=7, spaceAfter=3, bulletFontName="Helvetica-Bold",
                bulletColor=colors.HexColor(ORANGE)),
    "callout": S("callout", fontSize=11, leading=16, textColor=colors.HexColor(DARK)),
    "caption": S("caption", fontName="Helvetica-Oblique", fontSize=9, textColor=colors.HexColor(MUTED), alignment=TA_CENTER),
    "banner_t": S("bt", fontName="Helvetica-Bold", fontSize=26, leading=32, textColor=colors.white),
    "banner_s": S("bs", fontSize=12, leading=16, textColor=colors.HexColor("#C7D2FE")),
}


def banner(title: str, subtitle: str = "", color: str = DARK, accent: str = ORANGE):
    rows = [[Paragraph(inline(title), ST["banner_t"])]]
    if subtitle:
        rows.append([Paragraph(inline(subtitle), ST["banner_s"])])
    rows.append([""])
    t = Table(rows, colWidths=[PAGE_W], rowHeights=[None] * (len(rows) - 1) + [6])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -2), colors.HexColor(color)),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor(accent)),
        ("LEFTPADDING", (0, 0), (-1, -1), 18), ("RIGHTPADDING", (0, 0), (-1, -1), 18),
        ("TOPPADDING", (0, 0), (-1, 0), 20), ("BOTTOMPADDING", (0, -2), (-1, -2), 18),
        ("TOPPADDING", (0, -1), (-1, -1), 0), ("BOTTOMPADDING", (0, -1), (-1, -1), 0),
    ]))
    return t


def callout(text: str, color: str = ORANGE, bg: str = "#FFF7ED"):
    t = Table([[Paragraph(inline(text), ST["callout"])]], colWidths=[PAGE_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)),
        ("LINEBEFORE", (0, 0), (0, -1), 4, colors.HexColor(color)),
        ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return [Spacer(1, 4), t, Spacer(1, 8)]


def image_block(path: str, caption: str):
    try:
        w, h = PILImage.open(path).size
    except Exception:
        return []
    scale = min(12 * cm / w, 7.5 * cm / h)
    img = Table([[Image(path, w * scale, h * scale)]])
    img.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor(INDIGO)),
                             ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    block = [Spacer(1, 6), img]
    if caption:
        block += [Spacer(1, 3), Paragraph(inline(caption), ST["caption"])]
    return [KeepTogether(block + [Spacer(1, 8)])]


def _footer(title: str):
    def draw(c, doc):
        c.saveState()
        c.setStrokeColor(colors.HexColor("#E5E7EB"))
        c.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
        c.setFont("Helvetica", 8.5)
        c.setFillColor(colors.HexColor(MUTED))
        c.drawString(2 * cm, 1.0 * cm, clean(title)[:80])
        c.drawRightString(A4[0] - 2 * cm, 1.0 * cm, f"Page {doc.page}")
        c.restoreState()
    return draw


def _build(flow, fname: str, title: str) -> str:
    doc = SimpleDocTemplate(str(OUTPUTS / fname), pagesize=A4, title=clean(title), leftMargin=2 * cm,
                            rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=2.2 * cm)
    f = _footer(title)
    doc.build(flow, onFirstPage=f, onLaterPages=f)
    return fname


def markdown_to_pdf(md: str, fname: str, subtitle: str = "") -> str:
    """# title (banner), ## section, ### sub, - bullets, 1. numbered, > callout, ![caption](path), ==highlight==."""
    flow, title = [], fname
    for raw in md.splitlines():
        line = raw.rstrip()
        s = line.strip()
        if not s:
            continue
        if s.startswith("# "):
            title = s[2:]
            flow += [banner(title, subtitle), Spacer(1, 10)]
        elif s.startswith("## "):
            h = Table([[Paragraph(inline(s[3:]), ST["h2"])]], colWidths=[PAGE_W])
            h.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 2, colors.HexColor(ORANGE)),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                                   ("TOPPADDING", (0, 0), (-1, -1), 0)]))
            h.keepWithNext = True
            flow += [h, Spacer(1, 6)]
        elif s.startswith("### "):
            flow.append(Paragraph(inline(s[4:]), ST["h3"]))
        elif s.startswith(">"):
            flow += callout(s.lstrip("> ").strip())
        elif m := re.match(r"!\[(.*?)\]\((.+?)\)", s):
            if Path(m.group(2)).exists():
                flow += image_block(m.group(2), m.group(1))
        elif re.match(r"^[-*] ", s):
            flow.append(Paragraph(inline(s[2:]), ST["bullet"], bulletText="•"))
        elif m := re.match(r"^(\d+)[.)] (.*)", s):
            flow.append(Paragraph(inline(m.group(2)), ST["bullet"], bulletText=m.group(1) + "."))
        elif set(s) <= {"-", "*", "_"}:
            continue
        else:
            flow.append(Paragraph(inline(s), ST["body"]))
    return _build(flow, fname, title)


# ---------------------------------------------------------------- quiz paper
SECTIONS = {"mcq": ("Section A", "Multiple Choice Questions", INDIGO, "Choose the correct option."),
            "short": ("Section B", "Short Answer Questions", ORANGE, "Answer in 2-3 sentences."),
            "long": ("Section C", "Long Answer Questions", GREEN, "Answer in detail.")}


def _section_bar(kind: str, marks: int):
    label, name, color, hint = SECTIONS[kind]
    t = Table([[Paragraph(f'<font color="white"><b>{label}</b>  |  {name}</font>', S("sb", fontSize=12.5)),
                Paragraph(f'<font color="white"><b>{marks} marks</b></font>', S("sm", fontSize=11, alignment=TA_RIGHT))]],
              colWidths=[PAGE_W - 3 * cm, 3 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(color)),
                           ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                           ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return [Spacer(1, 10), t, Spacer(1, 3),
            Paragraph(f"<i>{hint}</i>", S("hint", fontSize=9.5, textColor=colors.HexColor(MUTED))), Spacer(1, 6)]


def _question(num: int, q, color: str):
    head = Table([[Paragraph(f'<font color="{color}"><b>Q{num}.</b></font>', S("qn", fontSize=12)),
                   Paragraph(f"<b>{inline(q.question)}</b>", S("qt", fontSize=11.5, leading=16)),
                   Paragraph(f'<font color="{ORANGE}"><b>[{q.marks}]</b></font>', S("qm", fontSize=11, alignment=TA_RIGHT))]],
                 colWidths=[1.2 * cm, PAGE_W - 3 * cm, 1.8 * cm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    block = [head, Spacer(1, 4)]
    if q.type == "mcq" and q.options:
        cells = [Paragraph(f'<font color="{INDIGO}"><b>{l}.</b></font>  {inline(o)}', S("op", fontSize=10.5, leading=15))
                 for l, o in zip("ABCD", q.options)]
        cells += [""] * (len(cells) % 2)
        rows = [[""] + cells[i:i + 2] for i in range(0, len(cells), 2)]
        t = Table(rows, colWidths=[1.2 * cm, (PAGE_W - 1.2 * cm) / 2, (PAGE_W - 1.2 * cm) / 2])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        block.append(t)
    else:
        n = 2 if q.type == "short" else 6
        t = Table([[""]] * n, colWidths=[PAGE_W - 1.2 * cm - 4], rowHeights=[0.75 * cm] * n)
        t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1"))]))
        outer = Table([["", t]], colWidths=[1.2 * cm, PAGE_W - 1.2 * cm])
        outer.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
        block += [outer]
    block.append(Spacer(1, 12))
    return block


def quiz_to_pdf(paper, class_name: str, fname: str) -> str:
    order = {"mcq": 0, "short": 1, "long": 2}
    qs = sorted(paper.questions, key=lambda q: order[q.type])
    total = sum(q.marks for q in qs)
    flow = [banner(paper.title, f"Class: {class_name}   |   Total Marks: {total}   |   Questions: {len(qs)}"),
            Spacer(1, 10)]
    info = Table([[Paragraph("<b>Name:</b> ______________________", S("i")),
                   Paragraph("<b>Roll No:</b> ________", S("i")),
                   Paragraph("<b>Date:</b> ________", S("i"))]], colWidths=[PAGE_W * .46, PAGE_W * .27, PAGE_W * .27])
    info.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(SOFT)),
                              ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                              ("LEFTPADDING", (0, 0), (-1, -1), 12), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    flow += [info, Spacer(1, 4)]
    flow += callout("**Instructions:** Attempt all questions. Write neatly. Marks are shown in [ ] at the right of each question.",
                    INDIGO, SOFT)
    num = 0
    for kind in ("mcq", "short", "long"):
        group = [q for q in qs if q.type == kind]
        if not group:
            continue
        bar = _section_bar(kind, sum(q.marks for q in group))
        for k, q in enumerate(group):
            num += 1
            qb = _question(num, q, SECTIONS[kind][2])
            flow.append(KeepTogether(bar + qb if k == 0 else qb))
    # answer key
    flow += [PageBreak(), banner("Answer Key", f"Teacher copy  |  {paper.title}", color="#064E3B", accent="#34D399"), Spacer(1, 12)]
    rows = [[Paragraph(f'<font color="white"><b>{h}</b></font>', S("th", fontSize=10)) for h in ("Q", "Type", "Answer", "Marks")]]
    names = {"mcq": "MCQ", "short": "Short", "long": "Long"}
    for i, q in enumerate(qs, 1):
        rows.append([Paragraph(f"<b>{i}</b>", S("td")), Paragraph(names[q.type], S("td")),
                     Paragraph(f'<font color="#047857"><b>{inline(q.answer)}</b></font>', S("td", fontSize=10, leading=14)),
                     Paragraph(str(q.marks), S("td"))])
    t = Table(rows, colWidths=[1.2 * cm, 2 * cm, PAGE_W - 5.2 * cm, 2 * cm], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065F46")),
                           ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ECFDF5")]),
                           ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1FAE5")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    flow.append(t)
    return _build(flow, fname, paper.title)
