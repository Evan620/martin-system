"""
Deal Pipeline Tools for AI Agents

This module provides tools for the Resource Mobilization Agent to interact with
the deal pipeline, including fetching project details, running matching, and
generating investment memos.
"""

from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime
from sqlalchemy import select

# Import dependencies
from app.core.database import get_db_session_context
from app.services.project_pipeline_service import ProjectPipelineService
from app.services.investor_matching_service import InvestorMatchingService, get_investor_matching_service
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

# Note: These tools are async because they need DB access

async def get_project_details(project_id: str) -> str:
    """
    Fetch detailed information about a specific project, including scores and status.
    
    Args:
        project_id: The UUID of the project to retrieve.
        
    Returns:
        JSON string containing project details, scores, and status.
    """
    try:
        import uuid as _uuid
        _project_uuid = _uuid.UUID(project_id)
        async with get_db_session_context() as db:
            service = ProjectPipelineService(db)

            from app.models.models import Project, ProjectScoreDetail, ScoringCriteria

            # 1. Fetch Project
            stmt = select(Project).where(Project.id == _project_uuid)
            result = await db.execute(stmt)
            project = result.scalars().first()
            
            if not project:
                return f"Error: Project with ID {project_id} not found."
            
            # 2. Fetch Scores
            score_stmt = select(ProjectScoreDetail, ScoringCriteria).join(ScoringCriteria)\
                .where(ProjectScoreDetail.project_id == _project_uuid)
            score_res = await db.execute(score_stmt)
            scores = score_res.all() # list of (ProjectScoreDetail, ScoringCriteria)
            
            # 3. Format Response
            project_dict = {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "status": project.status.value if hasattr(project.status, 'value') else project.status,
                "investment_size": float(project.investment_size or 0),
                "currency": project.currency,
                "readiness_score": float(project.readiness_score or 0),
                "afcen_score": float(project.afcen_score or 0),
                "pillar": project.pillar.value if hasattr(project.pillar, 'value') else project.pillar,
                "is_flagship": project.is_flagship,
                "lead_country": project.lead_country
            }
            
            score_details = []
            for detail, criteria in scores:
                score_details.append({
                    "criterion": criteria.criterion_name,
                    "score": float(detail.score or 0),
                    "notes": detail.notes
                })
                
            return json.dumps({
                "project": project_dict,
                "scores": score_details
            }, indent=2)
            
    except Exception as e:
        logger.error(f"Error fetching project details: {e}")
        return f"Error fetching project details: {str(e)}"

async def list_flagship_projects() -> str:
    """
    List all projects marked as 'Flagship' in the Deal Room.
    
    Returns:
        JSON string of flagship projects.
    """
    try:
        async with get_db_session_context() as db:
            from app.models.models import Project
            
            stmt = select(Project).where(Project.is_flagship == True)
            result = await db.execute(stmt)
            projects = result.scalars().all()
            
            formatted = []
            for p in projects:
                formatted.append({
                    "id": str(p.id),
                    "name": p.name,
                    "investment_size": float(p.investment_size or 0),
                    "status": p.status.value if hasattr(p.status, 'value') else p.status,
                    "afcen_score": float(p.afcen_score or 0)
                })
                
            if not formatted:
                return "No flagship projects found in the Deal Room."
                
            return json.dumps(formatted, indent=2)
            
    except Exception as e:
        logger.error(f"Error listing flagship projects: {e}")
        return f"Error listing flagship projects: {str(e)}"

async def trigger_investor_matching(project_id: str) -> str:
    """
    Trigger the investor matching engine for a specific project.
    
    Args:
        project_id: The UUID of the project.
        
    Returns:
        Summary of matches found.
    """
    try:
        import uuid as _uuid
        async with get_db_session_context() as db:
            service = get_investor_matching_service(db)
            result = await service.match_investors(_uuid.UUID(project_id))
            
            return json.dumps(result, indent=2)
            
    except Exception as e:
        logger.error(f"Error triggering matching: {e}")
        return f"Error triggering matching: {str(e)}"

async def generate_investment_memo(project_id: str) -> str:
    """
    Generate a draft investment memo for a project.
    
    Args:
        project_id: The UUID of the project.
        
    Returns:
        The generated memo text.
    """
    try:
        # 1. Fetch Data (Re-using the logic from get_project_details but internally)
        details_json = await get_project_details(project_id)
        
        if "Error" in details_json:
            return details_json
            
        # 2. LLM Service
        llm = get_llm_service()

        prompt = f"""
        You are an Investment Analyst for the ECOWAS Summit.
        Please draft a professional Investment Memo for the following project based on the data provided:

        {details_json}

        Structure the memo with the following sections:
        1. Executive Summary
        2. Strategic Rationale
        3. Financial Overview
        4. Risks & Mitigations
        5. Recommendation

        Format as Markdown.
        """

        memo = llm.chat(prompt, max_tokens=2000)
        return memo
        
    except Exception as e:
        logger.error(f"Error generating memo: {e}")
        return f"Error generating memo: {str(e)}"

async def analyze_project_documents(project_id: str) -> str:
    """
    Analyze all project documents using AI to assess investment readiness and bankability.
    
    This tool uses OCR and LLM to read PDFs and extract:
    - Document completeness (feasibility study, ESIA, financial model, etc.)
    - Financial metrics (IRR, NPV)
    - Compliance indicators (ESG, permits, government support)
    - Investment recommendation based on analysis
    
    Args:
        project_id: The UUID of the project to analyze.
        
    Returns:
        Detailed analysis report with investment recommendation.
    """
    try:
        async with get_db_session_context() as db:
            from app.models.models import Project, Document
            from app.services.document_intelligence import DocumentIntelligenceService
            from app.services.document_analyzer import get_document_analyzer
            
            # 1. Fetch Project
            import uuid as _uuid
            _project_uuid = _uuid.UUID(project_id)
            stmt = select(Project).where(Project.id == _project_uuid)
            result = await db.execute(stmt)
            project = result.scalars().first()

            if not project:
                return f"Error: Project with ID {project_id} not found."

            # 2. Fetch Documents
            doc_stmt = select(Document).where(Document.project_id == _project_uuid)
            doc_res = await db.execute(doc_stmt)
            documents = doc_res.scalars().all()
            
            if not documents:
                return f"⚠️ **No documents uploaded for {project.name}**\n\nCannot perform AI analysis without project documents. Please upload:\n- Feasibility Study\n- ESIA Report\n- Financial Model\n- Government Support Letter"
            
            # 3. Analyze Documents with AI
            doc_intelligence = DocumentIntelligenceService()
            analyzer = get_document_analyzer()
            
            all_analyses = []
            doc_summaries = []
            
            for doc in documents:
                try:
                    # Extract text
                    text = await doc_intelligence.extract_text_from_document(
                        doc.file_path,
                        doc.file_type
                    )
                    
                    # Analyze with LLM
                    analysis = await analyzer.analyze_document(text, doc.file_name)
                    all_analyses.append(analysis)
                    
                    # Build summary
                    doc_type = analysis.get('document_type', 'unknown')
                    confidence = analysis.get('confidence', 0)
                    doc_summaries.append(f"  - **{doc.file_name}**: {doc_type} (confidence: {confidence:.0%})")
                    
                except Exception as e:
                    logger.error(f"Failed to analyze {doc.file_name}: {e}")
                    doc_summaries.append(f"  - **{doc.file_name}**: Analysis failed")
            
            # 4. Aggregate Results
            aggregated = {
                "has_feasibility_study": any(a.get("has_feasibility_study") for a in all_analyses),
                "has_esia": any(a.get("has_esia") for a in all_analyses),
                "has_financial_model": any(a.get("has_financial_model") for a in all_analyses),
                "has_government_support": any(a.get("has_government_support") for a in all_analyses),
                "has_permits": any(a.get("has_permits") for a in all_analyses),
                "has_site_control": any(a.get("has_site_control") for a in all_analyses),
                "cross_border_impact": any(a.get("cross_border_impact") for a in all_analyses),
                "esg_compliant": any(a.get("esg_compliant") for a in all_analyses),
                "irr_percentage": next((a.get("irr_percentage") for a in all_analyses if a.get("irr_percentage")), None),
                "npv_value": next((a.get("npv_value") for a in all_analyses if a.get("npv_value")), None),
            }
            
            # 5. Calculate Readiness Score
            readiness_items = [
                aggregated["has_feasibility_study"],
                aggregated["has_esia"],
                aggregated["has_financial_model"],
                aggregated["has_permits"],
                aggregated["has_site_control"]
            ]
            readiness_pct = sum(readiness_items) / len(readiness_items) * 100
            
            strategic_items = [
                aggregated["has_government_support"],
                aggregated["cross_border_impact"]
            ]
            strategic_pct = sum(strategic_items) / len(strategic_items) * 100
            
            # 6. Investment Recommendation
            if readiness_pct >= 80 and strategic_pct >= 50:
                recommendation = "✅ **RECOMMEND FOR DEAL ROOM** - Project is investment-ready"
                rating = "BANKABLE"
            elif readiness_pct >= 60:
                recommendation = "⚠️ **CONDITIONAL APPROVAL** - Requires additional documentation"
                rating = "NEAR-BANKABLE"
            else:
                recommendation = "❌ **NOT READY** - Significant gaps in documentation"
                rating = "EARLY STAGE"
            
            # 7. Build Report
            report = f"""📊 **AI DOCUMENT ANALYSIS REPORT**

**Project:** {project.name}
**Investment Size:** ${project.investment_size:,.0f} {project.currency}
**Current AfCEN Score:** {project.afcen_score or 0:.1f}/100

---

**Documents Analyzed ({len(documents)}):**
{chr(10).join(doc_summaries)}

---

**READINESS ASSESSMENT:**

**Technical Readiness:** {readiness_pct:.0f}%
- Feasibility Study: {"✅" if aggregated["has_feasibility_study"] else "❌"}
- ESIA Report: {"✅" if aggregated["has_esia"] else "❌"}
- Financial Model: {"✅" if aggregated["has_financial_model"] else "❌"}
- Permits/Licenses: {"✅" if aggregated["has_permits"] else "❌"}
- Site Control: {"✅" if aggregated["has_site_control"] else "❌"}

**Strategic Alignment:** {strategic_pct:.0f}%
- Government Support: {"✅" if aggregated["has_government_support"] else "❌"}
- Cross-Border Impact: {"✅" if aggregated["cross_border_impact"] else "❌"}

**ESG Compliance:** {"✅" if aggregated["esg_compliant"] else "⚠️ Not verified"}

---

**FINANCIAL METRICS:**
- IRR: {f"{aggregated['irr_percentage']}%" if aggregated['irr_percentage'] else "Not found"}
- NPV: {f"${aggregated['npv_value']:,.0f}" if aggregated['npv_value'] else "Not found"}

---

**INVESTMENT RATING:** {rating}

{recommendation}

---

**NEXT STEPS:**
"""
            
            # Add specific recommendations
            if not aggregated["has_feasibility_study"]:
                report += "\n- ⚠️ Upload Feasibility Study"
            if not aggregated["has_esia"]:
                report += "\n- ⚠️ Upload ESIA Report"
            if not aggregated["has_financial_model"]:
                report += "\n- ⚠️ Upload Financial Model"
            if not aggregated["has_government_support"]:
                report += "\n- ⚠️ Obtain Government Support Letter"
            
            if rating == "BANKABLE":
                report += "\n- ✅ Ready for investor matching"
                report += "\n- ✅ Can be featured in Deal Room"
            
            return report
            
    except Exception as e:
        logger.error(f"Error analyzing project documents: {e}")
        return f"Error analyzing project documents: {str(e)}"

# Tool definitions
DEAL_PIPELINE_TOOLS = [
    {
        "name": "get_project_details",
        "description": "Fetch full project profile including investment size, readiness score, AfCEN score, and scoring breakdown. Use when the user asks about a specific project's details, scores, or status. Returns JSON with project info (name, description, status, investment_size, currency, readiness_score, afcen_score, pillar, lead_country) and score details. Example: User asks 'tell me about the solar project' → find its ID first, then call get_project_details(project_id='...').",
        "parameters": {
            "project_id": "The UUID of the project"
        },
        "function": get_project_details
    },
    {
        "name": "list_flagship_projects",
        "description": "List all high-priority 'Flagship' projects in the Deal Room. Use when the user asks about flagship projects, top-priority investments, or key deals. Returns JSON array of projects with: id, name, investment_size, status, afcen_score. Example: User asks 'what are our flagship projects?' → call list_flagship_projects().",
        "parameters": {},
        "function": list_flagship_projects
    },
    {
        "name": "trigger_investor_matching",
        "description": "Run the investor matching algorithm for a specific project. Use when the user asks to find investors for a project or run matching. Returns summary of matched investors with compatibility scores. Example: User asks 'find investors for the wind farm project' → call trigger_investor_matching(project_id='...').",
        "parameters": {
            "project_id": "The UUID of the project"
        },
        "function": trigger_investor_matching
    },
    {
        "name": "generate_investment_memo",
        "description": "Generate a Markdown-formatted investment memo for a project with executive summary, strategic rationale, financials, risks, and recommendations. Use when the user asks to draft or generate a memo for a project. Example: User asks 'draft an investment memo for the solar project' → call generate_investment_memo(project_id='...').",
        "parameters": {
            "project_id": "The UUID of the project"
        },
        "function": generate_investment_memo
    },
    {
        "name": "analyze_project_documents",
        "description": "Use AI to analyze all project documents (PDFs) and provide investment readiness assessment. Reads actual document content using OCR and LLM to verify completeness, extract financial metrics (IRR, NPV), check ESG compliance, and recommend next steps. Returns detailed report with readiness percentage and BANKABLE/NEAR-BANKABLE/EARLY STAGE rating. Example: User asks 'analyze the documents for project X' → call analyze_project_documents(project_id='...').",
        "parameters": {
            "project_id": "The UUID of the project"
        },
        "function": analyze_project_documents
    }
]
