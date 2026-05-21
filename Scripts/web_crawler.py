#!/usr/bin/env python3

"""
Web Grounding Tool - Fetch and extract web content for LLM grounding.
Uses trafilatura for clean content extraction.

Usage:
    python web_grounding.py <url> [name] [--depth N] [--max-pages N]
"""

import sys
import os
import argparse
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin
from collections import deque

# Use venv if available
SCRIPT_DIR = Path(__file__).parent
VENV_SITE_PACKAGES = SCRIPT_DIR / ".venv" / "lib" / "python3.13" / "site-packages"
if VENV_SITE_PACKAGES.exists():
    sys.path.insert(0, str(VENV_SITE_PACKAGES))

try:
    import trafilatura
    from trafilatura.settings import use_config
    from trafilatura import extract_metadata
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"Error: Required package not installed: {e}")
    print("Run: pip install trafilatura beautifulsoup4 lxml")
    sys.exit(1)

# Configuration
MIN_DELAY = 1.5
GROUNDING_DIR = Path(".agent/grounding_repos")
CREDENTIALS_FILE = SCRIPT_DIR / ".credentials.env"

# Domains to exclude from crawling
EXCLUDED_DOMAINS = {
    'github.com', 'gitlab.com', 'bitbucket.org',
    'twitter.com', 'x.com', 'facebook.com', 'linkedin.com',
    'instagram.com', 'youtube.com', 'reddit.com',
    'stackoverflow.com', 'stackexchange.com',
    'npmjs.com', 'pypi.org', 'packagist.org',
}


def load_credentials():
    """Load credentials from .credentials.env file."""
    credentials = {}
    if not CREDENTIALS_FILE.exists():
        print(f"[*] No credentials file found at {CREDENTIALS_FILE}")
        return credentials
    
    with open(CREDENTIALS_FILE) as f:
        print(f"[*] Loading credentials from {CREDENTIALS_FILE}")
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                credentials[key.strip()] = value.strip()
        
        print(f"  Loaded {len(credentials)} credential entries")
        print(f"  Credentials keys: {list(credentials.keys())}")
    
    return credentials


def get_auth_for_domain(domain, credentials):
    """Get (user, pass) tuple for a domain, or None."""
    if not credentials:
        return None
    
    # Convert domain to env key format: docs.example.com -> DOCS_EXAMPLE_COM
    key_prefix = domain.upper().replace('.', '_').replace('-', '_')
    
    # Try to find matching credentials
    user_key = f"{key_prefix}_USER"
    pass_key = f"{key_prefix}_PASS"
    
    user = credentials.get(user_key)
    password = credentials.get(pass_key)
    
    if user and password:
        print(f"  [*] Found credentials for {domain}")
        return (user, password)
    
    return None


def configure_trafilatura():
    """Configure trafilatura for optimal extraction."""
    config = use_config()
    config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")
    config.set("DEFAULT", "MIN_OUTPUT_SIZE", "100")
    return config


def is_external_resource(url, base_domain):
    """Check if URL points to external resource that should be saved but not crawled."""
    parsed = urlparse(url)
    
    # Check if it's an external domain
    if parsed.netloc and parsed.netloc != base_domain:
        # Check if it's a known external service
        for excluded in EXCLUDED_DOMAINS:
            if excluded in parsed.netloc:
                return True
    
    return False


def extract_links_from_html(html_content, base_url):
    """Extract all internal links from HTML content using BeautifulSoup."""
    internal_links = []
    external_references = []
    
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc
        
        # Find all <a> tags with href
        for tag in soup.find_all('a', href=True):
            href = tag.get('href', '').strip()
            
            # Skip empty, anchor-only, or javascript links
            if not href or href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                continue
            
            # Convert relative URLs to absolute
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            
            # Normalize URL (remove fragment, trailing slash from path)
            normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
            if parsed.query:
                normalized_url += f"?{parsed.query}"
            
            # Check if it's internal or external
            if parsed.netloc == base_domain:
                # Internal link - crawl it
                internal_links.append(normalized_url)
            elif parsed.netloc:
                # External link - save reference but don't crawl
                if is_external_resource(normalized_url, base_domain):
                    external_references.append((tag.get_text(strip=True), normalized_url))
    
    except Exception as e:
        print(f"  [!] Error parsing links: {e}")
    
    return list(set(internal_links)), external_references


def fetch_and_extract(url, config, credentials=None):
    """Fetch URL and extract content as markdown."""
    time.sleep(MIN_DELAY)
    
    parsed_url = urlparse(url)
    auth = get_auth_for_domain(parsed_url.netloc, credentials or {})
    
    print(f"[*] Processing URL: {url}")
    
    try:
        # Fetch content
        if auth:
            import base64
            import urllib.request
            
            # Create request with basic auth header
            auth_string = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
            req = urllib.request.Request(url)
            req.add_header("Authorization", f"Basic {auth_string}")
            req.add_header("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")
            
            with urllib.request.urlopen(req, timeout=30) as response:
                downloaded = response.read().decode('utf-8', errors='replace')
                print(f"  [âœ“] Fetched with auth (Status: {response.status})")
        else:
            # Use trafilatura.fetch_url
            downloaded = trafilatura.fetch_url(url, config=config)
            print(f"  [âœ“] Fetched without auth (Length: {len(downloaded) if downloaded else 0} bytes)")
        
        if not downloaded:
            print(f"  [!] Failed to fetch: {url}")
            return None, None, [], []
        
        # Extract main content as markdown
        content = trafilatura.extract(
            downloaded,
            output_format='markdown',
            include_links=True,
            include_tables=True,
            include_images=False,
            include_comments=False,
            config=config
        )
        
        if not content:
            print(f"  [!] No content extracted from: {url}")
            return None, None, [], []
        
        # Get metadata
        metadata = extract_metadata(downloaded)
        
        # Extract links using BeautifulSoup
        internal_links, external_references = extract_links_from_html(downloaded, url)
        
        print(f"  [âœ“] Found {len(internal_links)} internal links, {len(external_references)} external references")
        
        return content, metadata, internal_links, external_references
        
    except Exception as e:
        print(f"  [!] Error processing {url}: {e}")
        return None, None, [], []


def derive_filename(url, counter=0):
    """Derive filename from URL."""
    parsed = urlparse(url)
    path = parsed.path.rstrip('/')
    
    if not path or path == '/':
        name = "index"
    else:
        basename = os.path.basename(path)
        if '.' in basename and not basename.startswith('.'):
            name = basename.rsplit('.', 1)[0]
        else:
            name = basename if basename else "page"
    
    # Sanitize filename
    name = "".join(c for c in name if c.isalnum() or c in '-_')
    if not name:
        name = "page"
    
    suffix = f"_{counter}" if counter > 0 else ""
    return f"{name}{suffix}.md"


def derive_repo_name(url):
    """Derive repository name from URL."""
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]
    
    if path_parts:
        name = path_parts[0]
    else:
        name = parsed.netloc.replace('.', '_')
    
    return "".join(c for c in name if c.isalnum() or c in '-_')


def save_content(content, metadata, current_url, external_refs, output_dir):
    """Save content to file with proper naming and collision avoidance."""
    filename = derive_filename(current_url)
    output_file = output_dir / filename
    counter = 1
    
    # Avoid filename collisions
    while output_file.exists():
        filename = derive_filename(current_url, counter)
        output_file = output_dir / filename
        counter += 1
    
    # Add metadata header
    header = f"# {metadata.title if metadata and metadata.title else 'Untitled'}\n"
    header += f"> Source: {current_url}\n\n"
    
    # Add external references section if any
    if external_refs:
        footer = "\n\n---\n\n## External References\n\n"
        for text, link in external_refs[:50]:  # Limit to first 50
            footer += f"- [{text if text else link}]({link})\n"
        content = content + footer
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(header + content)
    
    print(f"  [âœ“] Saved: {output_file.name}")
    return output_file.name


def main():
    parser = argparse.ArgumentParser(
        description="Ground webpage content for LLM context.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("url", help="URL to ground")
    parser.add_argument("name", nargs="?", help="Local name for grounded content directory")
    parser.add_argument("--depth", "-d", type=int, default=0,
                       help="Follow internal links to this depth (default: 0 = single page)")
    parser.add_argument("--max-pages", "-m", type=int, default=50,
                       help="Maximum pages to fetch when following links (default: 50)")
    
    args = parser.parse_args()
    
    url = args.url
    repo_name = args.name if args.name else derive_repo_name(url)
    output_dir = GROUNDING_DIR / repo_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    config = configure_trafilatura()
    credentials = load_credentials()
    
    if credentials:
        print(f"[*] Loaded credentials for {len(credentials) // 2} domain(s)")
    
    # Track visited URLs and use BFS queue
    visited = set()
    to_visit = deque([(url, 0)])  # (url, depth)
    pages_fetched = 0
    saved_files = []
    
    print(f"[*] Grounding {url} to {output_dir}/")
    if args.depth > 0:
        print(f"[*] Following links up to depth {args.depth} (max {args.max_pages} pages)")
    
    while to_visit and pages_fetched < args.max_pages:
        current_url, depth = to_visit.popleft()
        
        if current_url in visited:
            continue
        
        visited.add(current_url)
        
        print(f"\n[{pages_fetched + 1}/{args.max_pages}] Depth {depth}: {current_url[:100]}...")
        
        content, metadata, links, external_refs = fetch_and_extract(current_url, config, credentials)
        
        if content:
            saved_file = save_content(content, metadata, current_url, external_refs, output_dir)
            saved_files.append((saved_file, current_url))
            pages_fetched += 1
            
            # Queue internal links if within depth
            if depth < args.depth:
                new_links = [link for link in links if link not in visited]
                print(f"  [*] Queueing {len(new_links)} new links for depth {depth + 1}")
                
                for link in new_links:
                    to_visit.append((link, depth + 1))
    
    print(f"\n{'='*80}")
    print(f"[âœ“] Successfully grounded {pages_fetched} page(s) to: {output_dir}/")
    
    # Create an index file
    index_file = output_dir / "_index.md"
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(f"# Grounded Content Index\n\n")
        f.write(f"**Source:** {url}\n\n")
        f.write(f"**Pages fetched:** {pages_fetched}\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"---\n\n")
        f.write(f"## Pages\n\n")
        
        for filename, source_url in saved_files:
            f.write(f"- [{filename}]({filename}) - {source_url}\n")
    
    print(f"[âœ“] Index created: {index_file}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()