import os
from typing import Optional
from jinja2 import Environment, FileSystemLoader
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from datetime import datetime
import io

class FormatService:
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        self.jinja_env = Environment(loader=FileSystemLoader(self.template_dir))
        
    def generate_pdf(
        self,
        title: str,
        content: str,
        footer: Optional[str] = "ECOWAS Summit 2026 Official Document"
    ) -> bytes:
        """
        Generates a branded PDF from text/markdown content.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1 # Center
        )
        
        body_style = styles['BodyText']
        
        elements = []
        
        # Add Header (Placeholder for logo)
        elements.append(Paragraph("<b>ECOWAS Economic Integration & Investment Summit 2026</b>", title_style))
        elements.append(Spacer(1, 12))
        
        # Add Document Title
        elements.append(Paragraph(f"<u>{title}</u>", styles['Heading2']))
        elements.append(Paragraph(f"Date Generated: {datetime.now().strftime('%Y-%m-%d')}", styles['Italic']))
        elements.append(Spacer(1, 24))
        
        # Add Content (Splitting by lines for simplicity, ideally use a markdown-to-reportlab parser)
        for line in content.split('\n'):
            if line.strip():
                elements.append(Paragraph(line, body_style))
                elements.append(Spacer(1, 6))
        
        # Footer
        elements.append(Spacer(1, 48))
        elements.append(Paragraph(footer, styles['Italic']))
        
        doc.build(elements)
        return buffer.getvalue()

format_service = FormatService()
