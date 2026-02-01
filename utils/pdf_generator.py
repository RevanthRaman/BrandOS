
import io
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT

class PDFGenerator:
    def __init__(self):
        self.buffer = io.BytesIO()
        self.doc = SimpleDocTemplate(self.buffer, pagesize=LETTER, topMargin=0.5*inch, bottomMargin=0.5*inch)
        self.styles = getSampleStyleSheet()
        self.elements = []
        
        # Custom Styles
        self.styles.add(ParagraphStyle(name='TitleCenter', parent=self.styles['Heading1'], alignment=TA_CENTER, spaceAfter=20, fontSize=24, textColor=colors.HexColor('#4f46e5')))
        self.styles.add(ParagraphStyle(name='SectionHeader', parent=self.styles['Heading2'], spaceBefore=15, spaceAfter=10, fontSize=16, textColor=colors.HexColor('#1f2937'), borderWidth=0, borderColor=colors.HexColor('#e5e7eb')))
        self.styles.add(ParagraphStyle(name='SubSection', parent=self.styles['Heading3'], spaceBefore=10, spaceAfter=5, fontSize=12, textColor=colors.HexColor('#374151')))
        self.styles.add(ParagraphStyle(name='NormalText', parent=self.styles['Normal'], fontSize=10, leading=14, spaceAfter=6))
        self.styles.add(ParagraphStyle(name='RiskHigh', parent=self.styles['Normal'], fontSize=10, textColor=colors.red))
        self.styles.add(ParagraphStyle(name='Success', parent=self.styles['Normal'], fontSize=10, textColor=colors.green))
        
    def add_title(self, text):
        self.elements.append(Paragraph(text, self.styles['TitleCenter']))
        self.elements.append(Spacer(1, 0.2*inch))

    def add_section_header(self, text):
        self.elements.append(Paragraph(text, self.styles['SectionHeader']))
        self.elements.append(Spacer(1, 0.1*inch))
        
    def add_paragraph(self, text, style='NormalText'):
        # Robust Markdown to XML conversion
        import re
        
        # 1. Escape existing XML/HTML chars that aren't our intended tags
        # Note: We assume the input 'text' might already contain intentional <i> or <b> tags from the caller.
        # But for raw content, we should be careful. 
        # Since the caller in generate_aeo_report wraps the whole thing in <i>, we should respect that.
        
        # 2. Convert **Bold** to <b>Bold</b>
        # We use a non-greedy regex to match pairs.
        # If a pair is broken (due to truncation), it won't be matched and will remain as ** (safe).
        formatted_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        
        # Handle bullet points
        if text.strip().startswith('- '):
            formatted_text = '&bull; ' + formatted_text[2:]
            
        try:
            self.elements.append(Paragraph(formatted_text, self.styles[style]))
        except ValueError:
            # Fallback for complex XML parsing errors: strip tags and render plain
            clean_text = re.sub(r'<[^>]+>', '', text)
            self.elements.append(Paragraph(clean_text, self.styles[style]))

    def add_table(self, data, col_widths=None):
        if not data:
            return
            
        # Style the table
        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#111827')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        self.elements.append(t)
        self.elements.append(Spacer(1, 0.2*inch))

    def add_page_break(self):
        self.elements.append(PageBreak())

    def build(self):
        self.doc.build(self.elements)
        self.buffer.seek(0)
        return self.buffer

def generate_aeo_report(brand_name, aeo_results, comp_stats, intent_stats, strategy=None, brand_index=None, defense_results=None, defense_strategy=None):
    pdf = PDFGenerator()
    
    # Title
    pdf.add_title(f"AEO Analysis Report: {brand_name}")
    
    # 1. Executive Summary & Metrics (Discovery)
    pdf.add_section_header("SECTION I: Market Discovery (Non-Branded)")
    pdf.add_paragraph(f"<i>Analysis of how AI models respond to non-branded category queries (e.g., 'Best SMS API').</i>")
    pdf.elements.append(Spacer(1, 0.1*inch))
    
    # Calculate Overall metrics
    total_queries = 0
    total_mentions = 0
    model_breakdown = []
    
    for model, data in aeo_results.items():
        if data["status"] == "active":
            m_queries = 0
            m_mentions = 0
            for item in data["data"]:
                if item["status"] == "success":
                    m_queries += 1
                    if item["analysis"]["mentioned"]:
                        m_mentions += 1
                        total_mentions += 1
                    total_queries += 1
            
            score = (m_mentions / m_queries * 100) if m_queries > 0 else 0
            model_breakdown.append([model, f"{score:.1f}%"])

    overall_vis = (total_mentions / total_queries * 100) if total_queries > 0 else 0
    
    pdf.add_paragraph(f"<b>Overall Visibility Score:</b> {overall_vis:.1f}%")
    pdf.add_paragraph(f"Based on {total_queries} simulated AI searches.")
    
    pdf.add_paragraph("<b>Visibility by AI Model:</b>")
    pdf.add_table([["Model", "Visibility Score"]] + model_breakdown, col_widths=[200, 100])
    
    # 2. Intent Gap Analysis
    pdf.add_section_header("2. Intent Gap Analysis")
    if intent_stats:
        pdf.add_paragraph("Visibility breakdown by user intent stage:")
        intent_data = [["Intent", "Share of Voice", "Status"]]
        for intention, stats in intent_stats.items():
            sov = stats.get('sov', 0)
            status = "Strong" if sov > 70 else "Weak" if sov < 30 else "Moderate"
            intent_data.append([intention, f"{sov}%", status])
        pdf.add_table(intent_data, col_widths=[150, 100, 100])
    
    # 3. Market Share Leaderboard
    pdf.add_section_header("3. AEO Market Share Leaderboard")
    leaderboard = comp_stats.get("leaderboard", [])
    if leaderboard:
        # Columns: Rank, Brand, SoV, Info, Comm, Trans, Risk
        lb_header = ["Rank", "Brand", "Dominance", "Info", "Comm", "Trans", "Risk"]
        lb_data = [lb_header]
        
        for idx, row in enumerate(leaderboard[:10]): # Top 10
            lb_data.append([
                f"#{idx+1}",
                row['name'],
                f"{row['share_of_voice']}%",
                f"{row.get('info_score', 0)}%",
                f"{row.get('comm_score', 0)}%",
                f"{row.get('trans_score', 0)}%",
                f"{row.get('risk_score', 0)}%"
            ])
            
        pdf.add_table(lb_data, col_widths=[40, 100, 70, 50, 50, 50, 50])
        pdf.add_paragraph("<i>Note: 'Dominance' is weighted share of voice. 'Risk' is visibility in negative queries (lower is better).</i>")
    else:
        pdf.add_paragraph("No competitor data available.")

    # 4. Strategic Playbook (Discovery)
    if strategy:
        pdf.add_page_break()
        pdf.add_section_header("4. Strategic Playbook (Discovery)")
        pdf.add_paragraph(f"<b>Core Strategy:</b> {strategy.get('headline_strategy', 'N/A')}")
        pdf.add_paragraph(strategy.get('executive_summary', ''))
        
        pdf.add_paragraph("<b>Top Recommended Actions:</b>")
        for action in strategy.get("top_3_actions", []):
            pdf.add_paragraph(f"- <b>{action.get('title')}</b>: {action.get('description')} (Impact: {action.get('impact')})")
            
        if strategy.get('content_pivot'):
             pdf.add_paragraph(f"<b>Content Pivot:</b> {strategy.get('content_pivot')}")

    # --- SECTION II: BRAND DEFENSE ---
    if defense_results:
        pdf.add_page_break()
        pdf.add_section_header("SECTION II: Brand Defense Audit (Branded)")
        pdf.add_paragraph(f"<i>Analysis of how AI models respond to branded queries (e.g., '{brand_name} reviews', '{brand_name} pricing').</i>")
        pdf.elements.append(Spacer(1, 0.1*inch))
        
        # Defense Metrics
        moat_score = defense_results.get("moat_score", 0)
        moat_status = "Secure" if moat_score > 80 else "Vulnerable"
        
        pdf.add_paragraph(f"<b>Defensive Moat Score:</b> {moat_score}% ({moat_status})")
        pdf.add_paragraph(f"<i>Percentage of branded searches where NO competitors were suggested.</i>")
        
        # Narrative
        narrative = defense_results.get("narrative_descriptors", [])
        if narrative:
            pdf.add_paragraph(f"<b>Key Narrative Associations:</b> {', '.join(narrative[:5])}")
            
        # Competitor Leakage
        leakage = defense_results.get("leakage_counts", {})
        if leakage:
            pdf.add_section_header("Competitor Leakage Detection")
            pdf.add_paragraph("The following competitors appear in your branded searches (stealing high-intent traffic):")
            leak_data = [["Competitor", "Appearances"]]
            for k, v in leakage.items():
                leak_data.append([k, str(v)])
            pdf.add_table(leak_data, col_widths=[200, 100])
        else:
             pdf.add_paragraph("<b>✅ No Competitor Leakage Detected.</b> Your brand moat is secure.")
             
        # Defense Strategy
        if defense_strategy:
            pdf.add_section_header("Defense Playbook")
            pdf.add_paragraph(f"<b>Strategy:</b> {defense_strategy.get('headline_strategy', 'N/A')}")
            pdf.add_paragraph(defense_strategy.get('executive_summary', ''))
            
            pdf.add_paragraph("<b>Tactical Fixes:</b>")
            for action in defense_strategy.get("tactics", []):
                pdf.add_paragraph(f"- <b>{action.get('title')}</b>: {action.get('description')} (Impact: {action.get('impact')})")
    
    # 5. Citation Battlefield (Back to Global Appendix)
    pdf.add_page_break()
    pdf.add_section_header("Appendix A: Citation Battlefield")
    
    # Opps
    opps = comp_stats.get("opportunity_urls", [])[:5]
    if opps:
        pdf.add_paragraph("<b>Missing Citations (Opportunity Gaps):</b>")
        opp_data = [["Domain", "Frequency"]]
        for gap in opps:
             opp_data.append([gap['domain'], str(gap['leader_count'])])
        pdf.add_table(opp_data, col_widths=[300, 80])
        
    # Strengths
    strengths = comp_stats.get("strength_urls", [])[:5]
    if strengths:
        pdf.add_paragraph("<b>Current Strong Citations:</b>")
        str_data = [["Domain", "Frequency"]]
        for s in strengths:
             str_data.append([s['domain'], str(s['count'])])
        pdf.add_table(str_data, col_widths=[300, 80])

    # 6. Deep Dive (Audit)
    pdf.add_section_header("Appendix B: Deep Dive Query Analysis")
    
    # Group by Intent
    found_intents = set()
    for m in aeo_results.values():
         if m["status"] == "active":
            for item in m["data"]:
                found_intents.add(item.get("intent", "General"))
    
    for intent in sorted(list(found_intents)):
        pdf.add_paragraph(f"<b>Intent: {intent}</b>", style='SubSection')
        
        for model, res in aeo_results.items():
            if res["status"] == "active":
                intent_items = [x for x in res["data"] if x.get("intent") == intent]
                if intent_items:
                    for item in intent_items:
                        if item["status"] == "success":
                            an = item["analysis"]
                            rank_display = f"#{an['rank']}" if str(an['rank']).isdigit() else an['rank']
                            pdf.add_paragraph(f"&bull; <b>{item['keyword']}</b> ({model}): Rank {rank_display} | {an['sentiment']}")
                            pdf.add_paragraph(f"<i>Snippet: \"{an['snippet'][:200]}...\"</i>")
                            pdf.elements.append(Spacer(1, 0.05*inch))

    return pdf.build()

def generate_asset_report(asset_type, content, metadata, brand_name):
    pdf = PDFGenerator()
    
    # Title
    pdf.add_title(f"Marketing Asset: {asset_type}")
    
    # Metadata Table
    pdf.add_section_header("Asset Context")
    meta_data = [
        ["Brand", brand_name],
        ["Theme/Topic", metadata.get("theme", "N/A")],
        ["Goal", metadata.get("goal", "N/A")],
        ["Target Audience", metadata.get("persona", "General")]
    ]
    if metadata.get("campaign"):
        meta_data.append(["Campaign", metadata.get("campaign")])
        
    pdf.add_table(meta_data, col_widths=[120, 350])
    
    # Content
    pdf.add_section_header("Content Draft")
    
    # Process the markdown content nicely
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            pdf.elements.append(Spacer(1, 0.05*inch))
            continue
            
        if line.startswith('# '):
            pdf.elements.append(Paragraph(line[2:], pdf.styles['Heading1']))
        elif line.startswith('## '):
             pdf.elements.append(Paragraph(line[3:], pdf.styles['Heading2']))
        elif line.startswith('### '):
             pdf.elements.append(Paragraph(line[4:], pdf.styles['Heading3']))
        elif line.startswith('- '):
             pdf.add_paragraph(line) # Handled in add_paragraph
        else:
             pdf.add_paragraph(line)
             
    # Footer / Notes
    pdf.add_page_break()
    pdf.add_section_header("Deployment Notes")
    pdf.add_paragraph("This content is generated by the Brand Marketing AI. Please review for factual accuracy before publishing.")
    pdf.add_paragraph("<b>SEO & AEO Strategy:</b> This content has been optimized for both traditional search and AI answer engines.")
    
    return pdf.build()
