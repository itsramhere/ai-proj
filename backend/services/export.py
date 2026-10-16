import subprocess
import os
import tempfile
import shutil

def find_browser_executable() -> str:
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        shutil.which("msedge"),
        shutil.which("chrome"),
        shutil.which("google-chrome")
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None

def export_markdown_to_pdf(markdown_content: str) -> str:
    """
    Exports markdown content to PDF via Pandoc HTML conversion followed by headless browser rendering.
    Produces high-fidelity styled PDF documents.
    """
    fd, md_path = tempfile.mkstemp(suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(markdown_content)
        
    html_path = md_path.replace(".md", ".html")
    pdf_path = md_path.replace(".md", ".pdf")
    
    # Modern styling for PDF export
    css = """
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1e293b; max-width: 800px; margin: 40px auto; padding: 0 20px; }
    h1 { color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }
    h2 { color: #1e293b; margin-top: 24px; }
    code { background-color: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; font-family: Consolas, monospace; }
    pre { background-color: #0f172a; color: #f8fafc; padding: 16px; border-radius: 8px; overflow-x: auto; }
    pre code { background-color: transparent; color: inherit; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; }
    th, td { border: 1px solid #cbd5e1; padding: 8px 12px; text-align: left; }
    th { background-color: #f8fafc; }
    blockquote { border-left: 4px solid #6366f1; padding-left: 16px; color: #475569; margin: 16px 0; }
    """
    
    try:
        # Step 1: Convert Markdown to Standalone HTML with CSS
        subprocess.run([
            "pandoc", md_path, "-s", "--metadata", "title=AI Lecture Notes",
            "-V", f"header-includes=<style>{css}</style>",
            "-o", html_path
        ], check=True)
        
        # Step 2: Print HTML to PDF using Edge or Chrome headless
        browser = find_browser_executable()
        if browser:
            subprocess.run([
                browser, "--headless=new", "--disable-gpu",
                f"--print-to-pdf={pdf_path}", html_path
            ], check=True)
        else:
            # Fallback to direct pandoc if no browser is found
            subprocess.run(["pandoc", md_path, "-o", pdf_path], check=True)
            
    finally:
        if os.path.exists(md_path):
            os.remove(md_path)
        if os.path.exists(html_path):
            os.remove(html_path)
            
    return pdf_path
