from bs4 import BeautifulSoup
from typing import List, Dict, Any

def extract_auth_relevant_html(html: str, max_length: int = 8000) -> str:
    """
    Extract only authentication-related HTML to save tokens.
    Reduces 200KB HTML to ~5-8KB of relevant content.
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    relevant_elements = []
    
    # Find forms
    forms = soup.find_all('form')
    relevant_elements.extend(forms)
    
    # Find password inputs
    password_inputs = soup.find_all('input', type='password')
    relevant_elements.extend(password_inputs)
    
    # Find email/text inputs
    email_inputs = soup.find_all('input', type=['email', 'text'])
    relevant_elements.extend(email_inputs[:10])  # Limit to 10
    
    # Find buttons with auth-related text
    auth_keywords = ['login', 'sign in', 'sign up', 'register', 'auth', 'log in']
    buttons = soup.find_all(['button', 'a'], string=lambda s: s and 
                            any(kw in s.lower() for kw in auth_keywords))
    relevant_elements.extend(buttons)
    
    # Find OAuth buttons (common class patterns)
    oauth_patterns = ['oauth', 'google', 'github', 'facebook', 'twitter', 'microsoft', 'apple']
    oauth_elements = []
    for pattern in oauth_patterns:
        oauth_elements.extend(soup.find_all(class_=lambda c: c and pattern in c.lower()))
    relevant_elements.extend(oauth_elements[:20])  # Limit
    
    # Find divs/sections with login-related classes or IDs
    login_containers = soup.find_all(['div', 'section'], 
                                     class_=lambda c: c and any(kw in c.lower() for kw in auth_keywords))
    login_containers.extend(soup.find_all(['div', 'section'], 
                                          id=lambda i: i and any(kw in i.lower() for kw in auth_keywords)))
    relevant_elements.extend(login_containers[:5])  # Limit to 5 containers
    
    # Convert to strings and deduplicate
    seen = set()
    unique_elements = []
    for elem in relevant_elements:
        elem_str = str(elem)
        if elem_str not in seen:
            seen.add(elem_str)
            unique_elements.append(elem_str)
    
    # Join and truncate
    result = '\n'.join(unique_elements)
    
    if len(result) > max_length:
        result = result[:max_length] + '\n... (truncated)'
    
    return result if result else html[:max_length]


def extract_delta_html(html_before: str, html_after: str, max_length: int = 5000) -> str:
    """
    Extract only the HTML that changed between two states.
    Useful for trigger analysis.
    """
    soup_before = BeautifulSoup(html_before, 'html.parser')
    soup_after = BeautifulSoup(html_after, 'html.parser')
    
    # Get all elements from after
    after_elements = soup_after.find_all(['form', 'input', 'button', 'div', 'a'])
    
    # Find elements that are new
    before_text = html_before
    new_elements = []
    
    for elem in after_elements:
        elem_str = str(elem)
        if elem_str not in before_text:
            new_elements.append(elem_str)
    
    result = '\n'.join(new_elements[:50])  # Limit to 50 new elements
    
    if len(result) > max_length:
        result = result[:max_length] + '\n... (truncated)'
    
    return result if result else extract_auth_relevant_html(html_after, max_length)


def extract_network_auth_requests(requests: List[str]) -> List[str]:
    """
    Filter network requests for auth-related endpoints.
    """
    auth_patterns = ['/login', '/signin', '/auth', '/oauth', '/api/auth', 
                     '/session', '/token', '/verify', '/register', '/signup']
    
    auth_requests = []
    for req in requests:
        if any(pattern in req.lower() for pattern in auth_patterns):
            auth_requests.append(req)
    
    return auth_requests


def clean_html_for_display(html: str) -> str:
    """
    Clean HTML for display in UI (remove extra whitespace, format).
    """
    soup = BeautifulSoup(html, 'html.parser')
    return soup.prettify()
