"""Generate stylish code screenshots for tech tweets.

Uses carbon.now.sh style rendering for beautiful code snippets.
Great for tech takes and dev content.
"""

import hashlib
import logging
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)


# Sample code snippets for different tech topics
SAMPLE_SNIPPETS = {
    "typescript": '''const useAPI = async <T>(url: string): Promise<T> => {
  const res = await fetch(url);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
};''',
    "react": '''export const Button = ({ onClick, children }) => (
  <button 
    className="px-4 py-2 bg-blue-500 hover:bg-blue-600"
    onClick={onClick}
  >
    {children}
  </button>
);''',
    "python": '''async def process_batch(items: list[dict]) -> list[Result]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(process(item)) for item in items]
    return [t.result() for t in tasks]''',
    "rust": '''fn main() {
    let data: Vec<i32> = (0..100)
        .filter(|x| x % 2 == 0)
        .map(|x| x * 2)
        .collect();
    println!("{:?}", data);
}''',
    "api": '''{
  "endpoint": "/api/v1/users",
  "method": "POST",
  "response": {
    "id": "usr_123",
    "status": "created"
  }
}''',
    "terminal": '''$ npm create next-app@latest my-app
✓ Would you like to use TypeScript? Yes
✓ Would you like to use ESLint? Yes
✓ Would you like to use Tailwind CSS? Yes
Creating a new Next.js app in ./my-app''',
    "bug": '''// Before (bug)
if (user = null) {
  return "no user";
}

// After (fixed)
if (user === null) {
  return "no user";
}''',
}


@dataclass
class CodeScreenshot:
    """Generated code screenshot."""
    
    path: Path
    language: str
    code: str
    theme: str


class CodeScreenshotGenerator:
    """Generate code screenshot images.
    
    Note: For production, integrate with:
    - carbon.now.sh API
    - ray.so
    - Or use Playwright to capture styled code
    
    This implementation creates a simple HTML-based screenshot
    using Playwright if available, or returns None to fallback to Unsplash.
    """

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or Path(tempfile.gettempdir()) / "code-screenshots"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _detect_language(self, description: str, tweet: str) -> str:
        """Detect code language from description/tweet content."""
        combined = f"{description} {tweet}".lower()
        
        if any(kw in combined for kw in ["typescript", "ts", "type"]):
            return "typescript"
        if any(kw in combined for kw in ["react", "jsx", "component"]):
            return "react"
        if any(kw in combined for kw in ["python", "py", "async", "await"]):
            return "python"
        if any(kw in combined for kw in ["rust", "cargo"]):
            return "rust"
        if any(kw in combined for kw in ["api", "json", "endpoint"]):
            return "api"
        if any(kw in combined for kw in ["terminal", "cli", "npm", "bash"]):
            return "terminal"
        if any(kw in combined for kw in ["bug", "fix", "error"]):
            return "bug"
        
        return "typescript"  # Default for dev content

    def _get_sample_code(self, language: str) -> str:
        """Get a sample code snippet for the language."""
        return SAMPLE_SNIPPETS.get(language, SAMPLE_SNIPPETS["typescript"])

    def generate_from_tweet(
        self,
        tweet_content: str,
        description: str,
    ) -> "GeneratedImage | None":
        """Generate a code screenshot based on tweet content.
        
        Args:
            tweet_content: The tweet text
            description: The [IMAGE: ...] description
            
        Returns:
            GeneratedImage or None if generation fails
        """
        from twitter_bot.images.generator import GeneratedImage
        
        language = self._detect_language(description, tweet_content)
        code = self._get_sample_code(language)
        
        # Try to generate with Playwright
        try:
            return self._generate_with_playwright(code, language)
        except Exception as e:
            logger.warning(f"Playwright screenshot failed: {e}")
            return None

    def _generate_with_playwright(
        self,
        code: str,
        language: str,
    ) -> "GeneratedImage | None":
        """Generate screenshot using Playwright and carbon.now.sh style HTML."""
        from twitter_bot.images.generator import GeneratedImage
        
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("Playwright not installed, skipping code screenshot")
            return None
        
        # Generate unique filename
        code_hash = hashlib.md5(code.encode()).hexdigest()[:8]
        filename = f"code_{language}_{code_hash}.png"
        filepath = self.output_dir / filename
        
        # Skip if already generated
        if filepath.exists():
            return GeneratedImage(
                path=filepath,
                source="code_screenshot",
                description=f"{language} code snippet",
                width=800,
                height=400,
            )
        
        # HTML template with carbon.now.sh style
        html = self._get_html_template(code, language)
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 800, "height": 600})
                page.set_content(html)
                
                # Wait for render and capture
                page.wait_for_timeout(100)
                element = page.query_selector(".code-window")
                if element:
                    element.screenshot(path=str(filepath))
                else:
                    page.screenshot(path=str(filepath))
                
                browser.close()
                
            return GeneratedImage(
                path=filepath,
                source="code_screenshot",
                description=f"{language} code snippet",
                width=800,
                height=400,
            )
            
        except Exception as e:
            logger.error(f"Playwright capture failed: {e}")
            return None

    def _get_html_template(self, code: str, language: str) -> str:
        """Get HTML template for code screenshot."""
        # Escape HTML
        code_escaped = (
            code.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        
        return f'''<!DOCTYPE html>
<html>
<head>
<style>
body {{
    margin: 0;
    padding: 40px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    font-family: system-ui, -apple-system, sans-serif;
}}
.code-window {{
    background: #1e1e1e;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 20px 68px rgba(0,0,0,0.55);
    max-width: 720px;
}}
.window-header {{
    background: #323232;
    padding: 12px 16px;
    display: flex;
    gap: 8px;
}}
.dot {{
    width: 12px;
    height: 12px;
    border-radius: 50%;
}}
.dot-red {{ background: #ff5f56; }}
.dot-yellow {{ background: #ffbd2e; }}
.dot-green {{ background: #27ca40; }}
.code-content {{
    padding: 24px;
    overflow-x: auto;
}}
pre {{
    margin: 0;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 14px;
    line-height: 1.6;
    color: #d4d4d4;
}}
.language-tag {{
    position: absolute;
    top: 10px;
    right: 16px;
    color: #666;
    font-size: 12px;
}}
</style>
</head>
<body>
<div class="code-window">
    <div class="window-header">
        <div class="dot dot-red"></div>
        <div class="dot dot-yellow"></div>
        <div class="dot dot-green"></div>
    </div>
    <div class="code-content">
        <pre>{code_escaped}</pre>
    </div>
</div>
</body>
</html>'''
