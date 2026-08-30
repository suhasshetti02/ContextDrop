import requests
import json
import urllib.parse
import socket
import ipaddress
from django.conf import settings
from bs4 import BeautifulSoup

def safe_requests_get(url, headers=None, timeout=10, max_size=10485760, max_redirects=5):
    """
    Safely fetches a URL, preventing SSRF by resolving and verifying IPs,
    handling redirects manually, and enforcing a max response size.
    """
    current_url = url
    session = requests.Session()
    
    for _ in range(max_redirects):
        parsed = urllib.parse.urlparse(current_url)
        if parsed.scheme not in ('http', 'https'):
            raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
            
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Invalid URL: missing hostname")
            
        try:
            addr_info = socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            raise ValueError(f"Could not resolve hostname: {hostname}")
            
        for info in addr_info:
            ip_str = info[4][0]
            try:
                ip = ipaddress.ip_address(ip_str)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
                    raise ValueError(f"Disallowed IP address resolved: {ip_str}")
            except ValueError:
                pass
                
        res = session.get(current_url, headers=headers, timeout=timeout, allow_redirects=False, stream=True)
        
        if 300 <= res.status_code < 400:
            redirect_url = res.headers.get('Location')
            if not redirect_url:
                raise ValueError("Redirect missing Location header")
            current_url = urllib.parse.urljoin(current_url, redirect_url)
            continue
            
        res.raise_for_status()
        content = b""
        for chunk in res.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > max_size:
                raise ValueError("Response size exceeds limit")
                
        res._content = content
        return res
        
    raise ValueError("Too many redirects")


def chunk_text_by_pages(pages_dict, chunk_size=1000, overlap=200):
    """
    Chunks text page-by-page, preserving metadata.
    Uses structure-aware chunking (by paragraphs/newlines) before falling back to length.
    Returns a list of dicts: [{'text': str, 'page_number': int, 'chunk_index': int}]
    """
    chunks = []
    chunk_index = 0

    for page_num, text in pages_dict.items():
        text = text.strip()
        if not text:
            continue

        if len(text) <= chunk_size:
            chunks.append({
                'text': text,
                'page_number': page_num,
                'chunk_index': chunk_index
            })
            chunk_index += 1
            continue
            
        # Structure-aware splitting
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            if len(current_chunk) + len(para) + 2 <= chunk_size:
                current_chunk += ("\n\n" + para) if current_chunk else para
            else:
                if current_chunk:
                    chunks.append({
                        'text': current_chunk,
                        'page_number': page_num,
                        'chunk_index': chunk_index
                    })
                    chunk_index += 1
                    
                    # Handle overlap by taking the last part of the previous chunk
                    overlap_text = current_chunk[-overlap:] if overlap > 0 else ""
                    
                    # If the paragraph itself is huge, we have to blind split it
                    if len(para) > chunk_size:
                        start = 0
                        while start < len(para):
                            end = start + chunk_size
                            part = para[start:end]
                            chunks.append({
                                'text': part,
                                'page_number': page_num,
                                'chunk_index': chunk_index
                            })
                            chunk_index += 1
                            start += (chunk_size - overlap)
                        current_chunk = "" # We consumed the large paragraph
                    else:
                        current_chunk = (overlap_text + "\n\n" + para) if overlap_text else para
                else:
                    # Current chunk is empty, but para is larger than chunk_size
                    start = 0
                    while start < len(para):
                        end = start + chunk_size
                        part = para[start:end]
                        chunks.append({
                            'text': part,
                            'page_number': page_num,
                            'chunk_index': chunk_index
                        })
                        chunk_index += 1
                        start += (chunk_size - overlap)
        
        if current_chunk:
            chunks.append({
                'text': current_chunk,
                'page_number': page_num,
                'chunk_index': chunk_index
            })
            chunk_index += 1

    return chunks

def get_embedding(text):
    """
    Generates embedding for a given text based on active provider.
    Returns a list of floats.
    """
    provider = getattr(settings, 'EMBEDDING_PROVIDER', 'ollama').lower()
    openai_key = getattr(settings, 'OPENAI_API_KEY', '')
    nomic_key = getattr(settings, 'NOMIC_API_KEY', '')
    
    if provider == 'openai' and openai_key:
        try:
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "input": text,
                "model": "text-embedding-3-small"
            }
            res = requests.post("https://api.openai.com/v1/embeddings", json=payload, headers=headers, timeout=10)
            res.raise_for_status()
            return res.json()["data"][0]["embedding"]
        except Exception as e:
            print(f"OpenAI embedding failed: {e}. Falling back to Nomic/Ollama.")
            
    if nomic_key:
        try:
            url = "https://api-atlas.nomic.ai/v1/embedding/text"
            headers = {"Authorization": f"Bearer {nomic_key}"}
            payload = {
                "model": "nomic-embed-text-v1.5",
                "texts": [text],
                "task_type": "search_document"
            }
            res = requests.post(url, json=payload, headers=headers, timeout=10)
            res.raise_for_status()
            return res.json()["embeddings"][0]
        except Exception as ex:
            print(f"Nomic API fallback failed: {ex}. Falling back to Ollama.")

    ollama_host = getattr(settings, 'OLLAMA_HOST', 'http://localhost:11434')
    try:
        payload = {
            "model": "nomic-embed-text",
            "prompt": text
        }
        res = requests.post(f"{ollama_host}/api/embeddings", json=payload, timeout=300)
        res.raise_for_status()
        return res.json()["embedding"]
    except Exception as e:
        print(f"Ollama API /api/embeddings failed: {e}. Trying /api/embed...")
        try:
            payload = {
                "model": "nomic-embed-text",
                "input": [text]
            }
            res = requests.post(f"{ollama_host}/api/embed", json=payload, timeout=300)
            res.raise_for_status()
            return res.json()["embeddings"][0]
        except Exception as ex:
            raise RuntimeError(f"Failed to generate embedding from Ollama: {ex}. Please ensure Ollama is running or provide NOMIC_API_KEY in .env")

def classify_domain(sample_text):
    """
    Zero-shot classifies the document domain into legal, medical, academic, technical, business, general.
    """
    prompt = (
        "You are a document classifier. Classify this document snippet into exactly one of these categories: "
        "legal, medical, academic, technical, business, general.\n\n"
        "Respond with ONLY the category name in lowercase, nothing else. No punctuation, no explanation.\n\n"
        f"Snippet:\n{sample_text[:1500]}"
    )

    groq_key = getattr(settings, 'GROQ_API_KEY', '')
    if groq_key and not groq_key.startswith("YOUR_") and not groq_key.startswith("gsk_3X7j3"):
        try:
            headers = {
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 10
            }
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=10)
            res.raise_for_status()
            domain = res.json()["choices"][0]["message"]["content"].strip().lower()
            if domain in ['legal', 'medical', 'academic', 'technical', 'business', 'general']:
                return domain
        except Exception as e:
            print(f"Groq classification failed: {e}. Falling back to Ollama.")

    ollama_host = getattr(settings, 'OLLAMA_HOST', 'http://localhost:11434')
    try:
        payload = {
            "model": "gemma4:e2b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 10
            }
        }
        res = requests.post(f"{ollama_host}/api/generate", json=payload, timeout=300)
        res.raise_for_status()
        domain = res.json()["response"].strip().lower()
        domain = ''.join(c for c in domain if c.isalnum())
        if domain in ['legal', 'medical', 'academic', 'technical', 'business', 'general']:
            return domain
    except Exception as e:
        print(f"Ollama classification failed: {e}")
        
    return "general"

def generate_suggested_questions(sample_text):
    """
    Generates exactly 3 relevant starter questions about the document snippet.
    Returns a list of strings.
    """
    prompt = (
        "Based on the following document excerpt, generate exactly 3 relevant, interesting starter questions "
        "that a reader might want to ask to understand the document.\n\n"
        "You MUST respond with ONLY a valid JSON array of strings containing the 3 questions. "
        "Do not include markdown tags (e.g. ```json), explanation, or other text outside the JSON block.\n\n"
        f"Excerpt:\n{sample_text[:2000]}"
    )
    
    default_questions = [
        "What is the core summary of this document?",
        "What are the key findings or takeaways?",
        "Are there any specific limitations or details mentioned?"
    ]

    groq_key = getattr(settings, 'GROQ_API_KEY', '')
    if groq_key and not groq_key.startswith("YOUR_") and not groq_key.startswith("gsk_3X7j3"):
        try:
            headers = {
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 200
            }
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=10)
            res.raise_for_status()
            text = res.json()["choices"][0]["message"]["content"].strip()
            # Clean up markdown code blocks if the LLM hallucinated them
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            parsed = json.loads(text.strip())
            if isinstance(parsed, list) and len(parsed) >= 3:
                return [str(q) for q in parsed[:3]]
        except Exception as e:
            print(f"Groq question generation failed: {e}. Falling back to Ollama.")

    # Fallback to local Ollama
    ollama_host = getattr(settings, 'OLLAMA_HOST', 'http://localhost:11434')
    try:
        payload = {
            "model": "gemma4:e2b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 200
            }
        }
        res = requests.post(f"{ollama_host}/api/generate", json=payload, timeout=300)
        res.raise_for_status()
        text = res.json()["response"].strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text.strip())
        if isinstance(parsed, list) and len(parsed) >= 3:
            return [str(q) for q in parsed[:3]]
    except Exception as e:
        print(f"Ollama question generation failed: {e}")

    return default_questions

def scrape_url_text(url):
    """
    Scrapes text from the paragraphs and headers of a given website URL.
    Returns a string containing parsed text.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # Prepend schema if missing
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url

    # FANDOM WIKI HEURISTIC (Bypass Cloudflare protection)
    if 'fandom.com/wiki/' in url:
        try:
            domain = url.split('fandom.com')[0] + 'fandom.com'
            page_name = url.split('/wiki/')[-1].split('?')[0].split('#')[0]
            api_url = f"{domain}/api.php?action=parse&page={page_name}&format=json"
            res = safe_requests_get(api_url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if 'parse' in data and 'text' in data['parse']:
                    html_content = data['parse']['text']['*']
                    soup = BeautifulSoup(html_content, 'html.parser')
                    return soup.get_text(separator='\n\n').strip()
        except Exception as e:
            print("Fandom API fallback failed:", e)

    # JINA READER API HEURISTIC (High-quality LLM Markdown Extraction)
    try:
        jina_url = f"https://r.jina.ai/{url}"
        res = safe_requests_get(jina_url, headers=headers, timeout=15)
        if res.status_code == 200:
            content = res.text
            # Only return if it didn't hit anti-bot CAPTCHAs inside Jina
            if "Target URL returned error" not in content and "requiring CAPTCHA" not in content:
                if len(content.strip()) > 100:
                    return content
    except Exception as e:
        print(f"Jina API scrape failed: {e}")

    # DEFAULT BEAUTIFULSOUP FALLBACK
    try:
        res = safe_requests_get(url, headers=headers, timeout=10)
        res.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"HTTP request to web page failed. It may be protected by anti-bot software: {str(e)}")

    soup = BeautifulSoup(res.content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.extract()

    # Get article or paragraph text
    paragraphs = soup.find_all(['h1', 'h2', 'h3', 'p'])
    text_content = []
    
    for p in paragraphs:
        p_text = p.get_text().strip()
        if p_text:
            text_content.append(p_text)

    full_text = "\n\n".join(text_content)
    
    if len(full_text.strip()) < 100:
        raise ValueError("Extracted text is too short. The webpage may be blocked by anti-bot protection or Javascript-rendered.")

    return full_text if full_text.strip() else (soup.body.get_text(separator='\n\n', strip=True) if soup.body else soup.get_text(separator='\n\n', strip=True))
