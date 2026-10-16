import subprocess
import os
import tempfile

def export_markdown_to_pdf(markdown_content: str) -> str:
    """
    Exports markdown content to PDF using Pandoc.
    Returns the path to the generated PDF file.
    Requires pandoc to be installed on the system.
    """
    fd, md_path = tempfile.mkstemp(suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(markdown_content)
        
    pdf_path = md_path.replace(".md", ".pdf")
    
    try:
        subprocess.run(["pandoc", md_path, "-o", pdf_path], check=True)
    except subprocess.CalledProcessError as e:
        if os.path.exists(md_path):
            os.remove(md_path)
        raise Exception(f"Pandoc failed: {e}")
        
    if os.path.exists(md_path):
        os.remove(md_path)
        
    return pdf_path

