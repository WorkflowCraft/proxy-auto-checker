import requests
import concurrent.futures
import os
import shutil
import time

import requests
import concurrent.futures
import os
import shutil
import time

def check_proxy(proxy_info):
    addr = proxy_info['addr']
    ptype = proxy_info['type']
    ip_only = addr.rsplit(':', 1)[0]
    
    # Format proxy URL
    proxy_url = f"http://{addr}"
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    
    try:
        test_start = time.time()
        
        # Test 1: Basic connectivity with httpbin.org
        response = requests.get(
            "http://httpbin.org/get",
            proxies=proxies,
            timeout=10,
            allow_redirects=True
        )
        
        # Check if we got a valid response
        if response.status_code != 200:
            print(f"[FAILED]  {addr} -> HTTP {response.status_code}")
            return None
            
        # Verify it's actually httpbin's response, not an ISP redirect
        try:
            data = response.json()
            if "headers" not in data:
                print(f"[FAILED]  {addr} -> Invalid response (not httpbin)")
                return None
        except:
            print(f"[FAILED]  {addr} -> Response not JSON")
            return None
        
        # Test 2: Check if GitHub blocks this proxy (important for dev use)
        try:
            github_response = requests.get(
                "https://api.github.com/zen",
                proxies=proxies,
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            
            if github_response.status_code == 403:
                print(f"[BLOCKED] {addr} -> GitHub blocks this proxy")
                return None
            elif github_response.status_code not in [200, 201, 304]:
                print(f"[FAILED]  {addr} -> GitHub test failed (HTTP {github_response.status_code})")
                return None
        except requests.exceptions.Timeout:
            print(f"[FAILED]  {addr} -> GitHub test timeout")
            return None
        except Exception as e:
            print(f"[FAILED]  {addr} -> GitHub error: {str(e)[:30]}")
            return None
        
        # Both tests passed! Get country info
        geo_resp = requests.get(f"http://ip-api.com/json/{ip_only}", timeout=5)
        country = "Unknown"
        if geo_resp.status_code == 200:
            geo_data = geo_resp.json()
            if geo_data.get("status") == "success":
                country = geo_data.get("country", "Unknown").replace(" ", "_")
        
        duration = time.time() - test_start
        print(f"[WORKING] {addr} ({ptype}) -> {country} ({duration:.2f}s) ✓GitHub")
        return {
            "addr": addr,
            "type": ptype,
            "country": country
        }
            
    except requests.exceptions.Timeout:
        print(f"[FAILED]  {addr} -> Timeout")
    except requests.exceptions.ProxyError:
        print(f"[FAILED]  {addr} -> Proxy error")
    except requests.exceptions.ConnectionError:
        print(f"[FAILED]  {addr} -> Connection error")
    except Exception as e:
        err_msg = str(e)[:40]
        print(f"[FAILED]  {addr} -> {err_msg}")
    
    return None

def normalize_proxy_addr(addr):
    """Remove protocol prefix and extra country info from proxy address if present"""
    # Step 1: Remove protocol prefix like http://, https://, socks4://, socks5://
    prefixes = ["http://", "https://", "socks4://", "socks5://"]
    for prefix in prefixes:
        if addr.lower().startswith(prefix):
            addr = addr[len(prefix):]
    
    # Step 2: Handle format like IP:PORT:Country - keep only IP:PORT
    parts = addr.split(':')
    if len(parts) >= 3:
        # Format is IP:PORT:Country or IP:PORT:Country:etc
        # Keep only IP:PORT
        addr = f"{parts[0]}:{parts[1]}"
    
    return addr

def main():
    # List of proxy sources
    sources = [ 
        # TheSpeedX (github.com/TheSpeedX/SOCKS-List)
        {"url": "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt", "type": "http"},
        {"url": "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt", "type": "socks4"},
        {"url": "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt", "type": "socks5"},

        # iplocate (github.com/iplocate/free-proxy-list)
        {"url": "https://raw.githubusercontent.com/iplocate/free-proxy-list/refs/heads/main/protocols/http.txt", "type": "http"},
        {"url": "https://raw.githubusercontent.com/iplocate/free-proxy-list/refs/heads/main/protocols/socks4.txt", "type": "socks4"},
        {"url": "https://raw.githubusercontent.com/iplocate/free-proxy-list/refs/heads/main/protocols/socks5.txt", "type": "socks5"},
        {"url": "https://raw.githubusercontent.com/iplocate/free-proxy-list/refs/heads/main/protocols/https.txt", "type": "https"},

        # proxifly (github.com/proxifly/free-proxy-list)
        {"url": "https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/protocols/http/data.txt", "type": "http"},
        {"url": "https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/protocols/https/data.txt", "type": "https"},
        {"url": "https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/protocols/socks4/data.txt", "type": "socks4"},
        {"url": "https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/protocols/socks5/data.txt", "type": "socks5"},

        # hideip.me (github.com/zloi-user/hideip.me)
        {"url": "https://raw.githubusercontent.com/zloi-user/hideip.me/refs/heads/main/http.txt", "type": "http"},
        {"url": "https://raw.githubusercontent.com/zloi-user/hideip.me/refs/heads/main/https.txt", "type": "https"},
        {"url": "https://raw.githubusercontent.com/zloi-user/hideip.me/refs/heads/main/socks4.txt", "type": "socks4"},
        {"url": "https://raw.githubusercontent.com/zloi-user/hideip.me/refs/heads/main/socks5.txt", "type": "socks5"},

        # Zaeem20 (github.com/Zaeem20/FREE_PROXIES_LIST)
        {"url": "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/refs/heads/master/http.txt", "type": "http"},
        {"url": "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/refs/heads/master/https.txt", "type": "https"},
        {"url": "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/refs/heads/master/socks4.txt", "type": "socks4"},
        {"url": "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/refs/heads/master/socks5.txt", "type": "socks5"},

        # vakhov (github.com/vakhov/fresh-proxy-list)
        {"url": "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/refs/heads/master/http.txt", "type": "http"},
        {"url": "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/refs/heads/master/https.txt", "type": "https"},
        {"url": "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/refs/heads/master/socks4.txt", "type": "socks4"},
        {"url": "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/refs/heads/master/socks5.txt", "type": "socks5"},

        # elliottophellia (github.com/elliottophellia/proxylist)
        {"url": "https://raw.githubusercontent.com/elliottophellia/proxylist/refs/heads/master/results/http/global/http_checked.txt", "type": "http"},

        # ALIILAPRO (github.com/ALIILAPRO/Proxy)
        {"url": "https://raw.githubusercontent.com/ALIILAPRO/Proxy/refs/heads/main/http.txt", "type": "http"},
        {"url": "https://raw.githubusercontent.com/ALIILAPRO/Proxy/refs/heads/main/socks4.txt", "type": "socks4"},
        {"url": "https://raw.githubusercontent.com/ALIILAPRO/Proxy/refs/heads/main/socks5.txt", "type": "socks5"}
    ]
    
    unique_proxies = {} # Use dict to store unique addr and its type
    duplicate_count = 0
    for source in sources:
        try:
            r = requests.get(source["url"])
            lines = [line.strip() for line in r.text.splitlines() if line.strip()]
            for addr in lines:
                # Normalize address by removing protocol prefix if present
                normalized_addr = normalize_proxy_addr(addr)
                if normalized_addr not in unique_proxies:
                    unique_proxies[normalized_addr] = source["type"]
                else:
                    duplicate_count += 1
        except Exception as e:
            print(f"Error fetching {source['url']}: {e}")

    proxy_list = [{"addr": addr, "type": ptype} for addr, ptype in unique_proxies.items()]
    print(f"Collected {len(proxy_list)} unique proxies (Skipped {duplicate_count} duplicates).")
    print("-" * 50)
    
    # Recreate country directory
    if os.path.exists("country"):
        shutil.rmtree("country")
    os.makedirs("country")

    working_proxies = []
    # Reduce max_workers to avoid congestion and rate limits
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        results = executor.map(check_proxy, proxy_list)
        for res in results:
            if res:
                # Create directory structure: country/CountryName/type.txt
                country_dir = os.path.join("country", res["country"])
                if not os.path.exists(country_dir):
                    os.makedirs(country_dir)
                
                file_path = os.path.join(country_dir, f"{res['type']}.txt")
                with open(file_path, "a") as f:
                    f.write(f"{res['addr']}\n")
                
                working_proxies.append(res)
    
    print("-" * 50)
    print(f"Total: Found {len(working_proxies)} working proxies.")
    
    # Update README.md with statistics
    update_readme_stats(working_proxies)

def update_readme_stats(working_proxies):
    """Update README.md with proxy statistics"""
    from datetime import datetime
    from collections import Counter
    
    # Gather statistics
    total_proxies = len(working_proxies)
    country_stats = Counter([p["country"] for p in working_proxies])
    type_stats = Counter([p["type"] for p in working_proxies])
    
    # Format last update time
    last_update = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Create stats section
    stats_section = f"""
## 📊 Proxy Statistics

**Last Updated:** {last_update}

**Total Working Proxies:** {total_proxies}

### By Type
{chr(10).join([f"- **{ptype.upper()}**: {count}" for ptype, count in sorted(type_stats.items())])}

### By Country (Top 10)
{chr(10).join([f"- **{country}**: {count}" for country, count in country_stats.most_common(10)])}

---
"""
    
    # Read current README
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            readme_content = f.read()
        
        # Check if stats section exists
        if "## 📊 Proxy Statistics" in readme_content:
            # Replace existing stats section
            import re
            # Match from "## 📊 Proxy Statistics" to the next "---" or "##"
            pattern = r'## 📊 Proxy Statistics.*?---\n'
            readme_content = re.sub(pattern, stats_section.strip() + "\n\n", readme_content, flags=re.DOTALL)
        else:
            # Insert stats section after disclaimer
            insert_marker = "## How It Works"
            if insert_marker in readme_content:
                readme_content = readme_content.replace(insert_marker, stats_section + insert_marker)
        
        # Write updated README
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(readme_content)
        
        print(f"✓ README.md updated with statistics")
    except Exception as e:
        print(f"Warning: Could not update README.md: {e}")

if __name__ == "__main__":
    main()
