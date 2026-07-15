import os
import markdown
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML, CSS
from app.core.config import settings

class PDFService:
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def generate_agenda_pdf(
        self,
        agenda_markdown: str,
        template_context: Dict[str, Any]
    ) -> bytes:
        """
        Generates a PDF agenda on official letterhead from markdown content.
        """
        # Convert Markdown to HTML
        agenda_html = markdown.markdown(agenda_markdown, extensions=['tables', 'fenced_code'])
        
        # Prepare context
        context = template_context.copy()
        context['agenda_html'] = agenda_html
        
        # Render Template
        template = self.jinja_env.get_template("agenda_pdf.html")
        rendered_html = template.render(**context)
        
        # Convert to PDF
        # Use simple default styling or load extra CSS if needed
        pdf_bytes = HTML(string=rendered_html).write_pdf()
        
        return pdf_bytes

    def generate_minutes_pdf(
        self,
        minutes_markdown: str,
        template_context: Dict[str, Any]
    ) -> bytes:
        """
        Generates a PDF of Meeting Minutes on official letterhead from markdown content.
        """
        # Convert Markdown to HTML
        # Use extensions for tables
        minutes_html = markdown.markdown(minutes_markdown, extensions=['tables', 'fenced_code', 'nl2br'])
        
        # Prepare context
        context = template_context.copy()
        context['minutes_html'] = minutes_html
        
        # Render Template
        template = self.jinja_env.get_template("minutes_pdf.html")
        rendered_html = template.render(**context)
        
        # Convert to PDF
        pdf_bytes = HTML(string=rendered_html).write_pdf()
        
        return pdf_bytes

    def generate_memo_pdf(
        self,
        memo_markdown: str,
        title: str = "Investment Memo",
        subtitle: str = "",
    ) -> bytes:
        """
        Generate a branded PDF of an investment memo from markdown content.
        Self-contained (no template file) — renders inline HTML via weasyprint.
        """
        body_html = markdown.markdown(memo_markdown or "", extensions=['tables', 'fenced_code', 'nl2br'])
        css = (
            "@page { size: A4; margin: 2.2cm 2cm; }"
            "body{font-family:'Helvetica Neue',Arial,sans-serif;color:#1f2937;font-size:11pt;line-height:1.5;}"
            ".eyebrow{font-size:8pt;letter-spacing:.14em;text-transform:uppercase;color:#6b7280;font-weight:700;}"
            "h1.doc-title{font-size:20pt;color:#1B2A4A;margin:4px 0 2px;}"
            ".subtitle{color:#2E75B6;font-size:11pt;margin:0 0 4px;}"
            ".rule{border:none;border-top:2px solid #D4A843;margin:10px 0 18px;}"
            "h1{font-size:15pt;color:#1B2A4A;} h2{font-size:13pt;color:#2E75B6;} h3{font-size:12pt;color:#1F4D78;}"
            "table{border-collapse:collapse;width:100%;margin:8px 0;} th,td{border:1px solid #d1d5db;padding:6px 8px;text-align:left;font-size:10pt;}"
            "th{background:#1B2A4A;color:#fff;} ul,ol{margin:6px 0 6px 18px;}"
        )
        sub = ('<div class="subtitle">%s</div>' % subtitle) if subtitle else ''
        html = (
            '<!doctype html><html><head><meta charset="utf-8"><style>' + css + '</style></head><body>'
            '<div class="eyebrow">AfCEN &middot; WAIIS Investment Pipeline</div>'
            '<h1 class="doc-title">' + (title or "Investment Memo") + '</h1>' + sub +
            '<hr class="rule"/>' + body_html + '</body></html>'
        )
        return HTML(string=html).write_pdf()


# Global instance
pdf_service = PDFService()
