from io import BytesIO
from datetime import datetime, timezone
from typing import List, Dict, Any

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Canvas that performs a two-pass rendering to add 'Page X of Y' and header."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))
        
        # Header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 750, "TESSERACT LAW ENFORCEMENT INTELLIGENCE PLATFORM — OFFICIAL CASE REPORT")
            self.setFont("Helvetica", 8)
            self.drawRightString(612 - 54, 750, f"Page {self._pageNumber} of {page_count}")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 742, 612 - 54, 742)
        
        # Footer (all pages)
        self.setFont("Helvetica-Bold", 7)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(54, 36, "CONFIDENTIAL — STRICTLY FOR AUTHORIZED LAW ENFORCEMENT & JUDICIAL REVIEW ONLY")
        self.setFont("Helvetica", 7)
        self.drawRightString(612 - 54, 36, f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} | Page {self._pageNumber} of {page_count}")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 46, 612 - 54, 46)
        
        self.restoreState()


def build_investigation_pdf(
    case_data: Dict[str, Any],
    evidence_list: List[Dict[str, Any]],
    entities_list: List[Dict[str, Any]],
    relations_list: List[Dict[str, Any]],
    timeline_events: List[Dict[str, Any]],
    intel_findings: List[Dict[str, Any]],
    flagged_items: List[Dict[str, Any]],
    audit_summary: List[Dict[str, Any]],
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0284C7"),
        spaceAfter=12
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#334155")
    )

    body_bold = ParagraphStyle(
        'DocBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor("#0F172A")
    )

    meta_label = ParagraphStyle(
        'MetaLabel',
        parent=body_style,
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748B")
    )

    meta_val = ParagraphStyle(
        'MetaVal',
        parent=body_style,
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0F172A")
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=body_style,
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    table_cell = ParagraphStyle(
        'TableCell',
        parent=body_style,
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#1E293B")
    )

    table_cell_mono = ParagraphStyle(
        'TableCellMono',
        parent=body_style,
        fontName='Courier',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#0F172A")
    )

    badge_amber = ParagraphStyle(
        'BadgeAmber',
        parent=body_style,
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#B45309")
    )

    notice_style = ParagraphStyle(
        'NoticeStyle',
        parent=body_style,
        fontName='Helvetica-Oblique',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#475569")
    )

    story = []

    # Title Header Block
    story.append(Paragraph(f"TESSERACT INVESTIGATION REPORT: {case_data.get('case_number', 'CASE-000')}", title_style))
    story.append(Paragraph(f"{case_data.get('title', 'Case Investigation')} &bull; Formal Case Dossier", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284C7"), spaceAfter=10))

    # Case Metadata Grid
    meta_table_data = [
        [
            Paragraph("Case Number", meta_label),
            Paragraph(f"<b>{case_data.get('case_number', '-')}</b>", meta_val),
            Paragraph("Status / Priority", meta_label),
            Paragraph(f"{case_data.get('status', 'ACTIVE')} / {case_data.get('priority', 'HIGH')}", meta_val),
        ],
        [
            Paragraph("Lead Investigator", meta_label),
            Paragraph(case_data.get('lead_investigator', '-'), meta_val),
            Paragraph("Created Date", meta_label),
            Paragraph(str(case_data.get('created_at', '-'))[:19], meta_val),
        ],
        [
            Paragraph("Assigned Team", meta_label),
            Paragraph(case_data.get('assigned', '-'), meta_val),
            Paragraph("Report Date", meta_label),
            Paragraph(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), meta_val),
        ],
    ]
    meta_table = Table(meta_table_data, colWidths=[90, 160, 90, 164])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#F1F5F9")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # Executive Summary Box
    story.append(Paragraph("1. Executive Summary", h2_style))
    summary_text = case_data.get('summary') or "Investigation into suspected network activities based on correlated documentary and digital evidence."
    summary_box_data = [[
        Paragraph(summary_text, body_style)
    ]]
    summary_table = Table(summary_box_data, colWidths=[504])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0F9FF")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#BAE6FD")),
        ('LINELEFT', (0, 0), (0, 0), 3.5, colors.HexColor("#0284C7")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)
    
    # Neutral Disclaimer Notice
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<b>Investigative Notice:</b> All entities, linkages, and timestamps contained in this document reflect evidence-supported observations and review markers. They do not constitute judicial determinations of guilt or criminal liability.",
        notice_style
    ))
    story.append(Spacer(1, 10))

    # Evidence Inventory & Cryptographic Ledger
    story.append(Paragraph(f"2. Evidence Overview & Integrity Ledger ({len(evidence_list)} Items)", h2_style))
    if evidence_list:
        ev_data = [[
            Paragraph("Evidence ID", table_header),
            Paragraph("Filename / Document", table_header),
            Paragraph("Type / Method", table_header),
            Paragraph("Ledger Hash (SHA-256)", table_header),
            Paragraph("Integrity Status", table_header),
        ]]
        for ev in evidence_list:
            sha = ev.get('sha256') or 'Not Registered'
            sha_short = f"{sha[:16]}...{sha[-8:]}" if len(sha) > 24 else sha
            ev_data.append([
                Paragraph(ev.get('evidence_id', '-'), table_cell_mono),
                Paragraph(ev.get('filename', '-'), table_cell),
                Paragraph(f"{ev.get('document_type', 'DOC')} &bull; {ev.get('method', 'Ingestion')}", table_cell),
                Paragraph(sha_short, table_cell_mono),
                Paragraph(f"<b>{ev.get('integrity_status', 'VERIFIED')}</b>", table_cell),
            ])
        ev_table = Table(ev_data, colWidths=[80, 130, 95, 125, 74])
        ev_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(ev_table)
    else:
        story.append(Paragraph("No evidence documents currently recorded in this case file.", body_style))
    story.append(Spacer(1, 10))

    # Investigator Review Flags
    story.append(Paragraph(f"3. Investigator Review Markers & Flags ({len(flagged_items)} Total)", h2_style))
    if flagged_items:
        flag_data = [[
            Paragraph("Resource", table_header),
            Paragraph("Flagged Item Label", table_header),
            Paragraph("Investigator", table_header),
            Paragraph("Reason / Review Note", table_header),
            Paragraph("Status", table_header),
        ]]
        for fl in flagged_items:
            flag_data.append([
                Paragraph(fl.get('resource_type', 'ITEM'), table_cell),
                Paragraph(f"<b>{fl.get('resource_label', '-')}</b>", table_cell),
                Paragraph(fl.get('flagged_by', '-'), table_cell),
                Paragraph(fl.get('reason', '-'), table_cell),
                Paragraph(fl.get('status', 'ACTIVE'), badge_amber if fl.get('status') == 'ACTIVE' else table_cell),
            ])
        flag_table = Table(flag_data, colWidths=[70, 110, 85, 175, 64])
        flag_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#B45309")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#FFFBEB"), colors.white]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#FDE68A")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#FEF3C7")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(flag_table)
    else:
        story.append(Paragraph("No active investigator flags recorded. All evidence items remain in standard review status.", body_style))
    story.append(Spacer(1, 10))

    # Canonical Entities Summary
    story.append(Paragraph(f"4. Extracted Canonical Entities ({len(entities_list)} Items)", h2_style))
    if entities_list:
        ent_data = [[
            Paragraph("Entity Category", table_header),
            Paragraph("Canonical Name / Identifier", table_header),
            Paragraph("Mentions", table_header),
            Paragraph("Evidence Provenance Count", table_header),
        ]]
        for ent in entities_list:
            ent_data.append([
                Paragraph(ent.get('entity_type', '-'), table_cell),
                Paragraph(f"<b>{ent.get('canonical_name', '-')}</b>", table_cell),
                Paragraph(str(ent.get('mention_count', 1)), table_cell),
                Paragraph(str(ent.get('evidence_count', 1)), table_cell),
            ])
        ent_table = Table(ent_data, colWidths=[110, 220, 70, 104])
        ent_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F766E")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0FDFA")]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CCFBF1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(ent_table)
    story.append(Spacer(1, 10))

    # Important Relationships / Network Summary
    if relations_list:
        story.append(Paragraph(f"5. Observed Linkages & Relationships ({len(relations_list)} Links)", h2_style))
        rel_data = [[
            Paragraph("Source Entity", table_header),
            Paragraph("Observed Relationship", table_header),
            Paragraph("Target Entity", table_header),
            Paragraph("Confidence", table_header),
        ]]
        for r in relations_list[:25]:  # capped for readability
            rel_data.append([
                Paragraph(r.get('source', '-'), table_cell),
                Paragraph(f"<b>{r.get('type', '-')}</b>", table_cell),
                Paragraph(r.get('target', '-'), table_cell),
                Paragraph(f"{Math_round_str(r.get('confidence', 0.95))}%", table_cell),
            ])
        rel_table = Table(rel_data, colWidths=[160, 130, 160, 54])
        rel_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4338CA")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF2FF")]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#C7D2FE")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(rel_table)
        story.append(Spacer(1, 10))

    # Investigation Timeline
    if timeline_events:
        story.append(Paragraph(f"6. Investigation Chronology & Timeline ({len(timeline_events)} Events)", h2_style))
        tl_data = [[
            Paragraph("Date / Time", table_header),
            Paragraph("Event Type", table_header),
            Paragraph("Observed Details & Location", table_header),
            Paragraph("Participants", table_header),
        ]]
        for ev in timeline_events:
            dt_str = ev.get('timestamp') or ev.get('date') or '-'
            tl_data.append([
                Paragraph(dt_str[:16].replace('T', ' '), table_cell_mono),
                Paragraph(f"<b>{ev.get('type', 'EVENT')}</b>", table_cell),
                Paragraph(ev.get('description') or ev.get('location') or '-', table_cell),
                Paragraph(ev.get('participants') or '-', table_cell),
            ])
        tl_table = Table(tl_data, colWidths=[95, 105, 174, 130])
        tl_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#065F46")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#ECFDF5")]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#A7F3D0")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(tl_table)
        story.append(Spacer(1, 10))

    # Intelligence Findings & Statistical Anomalies
    if intel_findings:
        story.append(Paragraph(f"7. Statistical Intelligence & Detected Anomalies ({len(intel_findings)} Findings)", h2_style))
        intel_data = [[
            Paragraph("Finding ID / Category", table_header),
            Paragraph("Observed Behavioral / Network Pattern", table_header),
            Paragraph("Corroborating Evidence", table_header),
        ]]
        for idx, f in enumerate(intel_findings, start=1):
            intel_data.append([
                Paragraph(f.get('title') or f"Pattern #{idx}", table_cell),
                Paragraph(f.get('explanation', '-'), table_cell),
                Paragraph(", ".join(f.get('evidenceIds', [])) or "Cross-Case Data", table_cell_mono),
            ])
        intel_table = Table(intel_data, colWidths=[110, 274, 120])
        intel_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#831843")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#FDF2F8")]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#FBCFE8")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(intel_table)
        story.append(Spacer(1, 10))

    # Audit & Accountability Summary
    if audit_summary:
        story.append(Paragraph("8. Chain of Custody & Audit Summary", h2_style))
        audit_data = [[
            Paragraph("Timestamp", table_header),
            Paragraph("Investigator / Actor", table_header),
            Paragraph("Action", table_header),
            Paragraph("Resource", table_header),
            Paragraph("Result", table_header),
        ]]
        for au in audit_summary[:10]:
            audit_data.append([
                Paragraph(str(au.get('timestamp', '-'))[:19].replace('T', ' '), table_cell_mono),
                Paragraph(au.get('actor', '-'), table_cell),
                Paragraph(au.get('action', '-'), table_cell),
                Paragraph(au.get('resource', '-'), table_cell),
                Paragraph(au.get('result', 'SUCCESS'), table_cell),
            ])
        audit_table = Table(audit_data, colWidths=[95, 95, 120, 130, 64])
        audit_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#334155")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(audit_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()


def Math_round_str(val) -> str:
    try:
        return str(round(float(val) * 100))
    except Exception:
        return "95"
