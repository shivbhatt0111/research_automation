"""Central prompt templates for all AI research operations."""

DISCOVERY_EXCLUSION_LIMIT = 30


def company_discovery_prompt(industry: str, location: str, count: int, exclude_names: list[str] = None) -> str:
    exclude_block = ''
    if exclude_names:
        listed = '\n'.join(f'- {name}' for name in exclude_names[:DISCOVERY_EXCLUSION_LIMIT])
        exclude_block = f"\nALREADY TRIED - DO NOT REPEAT THESE:\n{listed}\n"
        
    industry_guidance = ''
    industry_lower = (industry or '').strip().lower()
    broad_triggers = ('industrial', 'all types', 'any type', 'all companies', 'all businesses')
    if any(word in industry_lower for word in broad_triggers):
        industry_guidance = f"""
SPECIAL INTERPRETATION:
"{industry}" is a BROAD category, not a specific business type. It means: include businesses of ALL types in this area across the full industry spectrum - manufacturing, food processing, chemicals, engineering, packaging, textiles, pharma, hospitality, services, etc.
"""

    return f"""You are a strict, professional business research analyst working on ground-level market research.

TASK: Find exactly {count} real, currently operating businesses matching "{industry}" physically located in "{location}".

STRICT BOUNDARY RULE (HIGHEST PRIORITY):
Under NO circumstances should you return a business located outside of "{location}" or completely unrelated to "{industry}". If a business is in a different city, state, or unrelated sector, REJECT IT IMMEDIATELY. Do not provide "nearby" or "similar" businesses from other regions.

CRITICAL VERIFICATION RULES (VIOLATION = REJECTION):
1. LOCATION STRICTNESS: Every business MUST be physically located in {location}. The location "{location}" may be a specific area, road, or industrial zone within a larger city. Businesses MUST be located IN that exact area/zone. (e.g., Pithampur Industrial Area ≠ Sanwer Road Industrial Area ≠ Vijay Nagar - these are separate zones even if all are in Indore city).
2. WEBSITE FIELD - STRICT RULE: The website value MUST be the business's OWN official website (its own domain). NEVER provide a directory, listing, aggregator, marketplace, social media, or third-party page as the website. Banned domains include: justdial.com, indiamart.com, zomato.com, tradeindia.com, sulekha.com, linkedin.com/company, facebook.com, instagram.com, cataloxy.in, newclothmarketonline.com, or ANY site with "/list/", "/directory/", "/companies/" in the URL.
3. NO WEBSITE FALLBACK: If a business does not have its own official website, you MUST return an empty string "" for the website field. DO NOT guess or substitute with a directory link.
4. ADDRESS FIELD - STRICT RULE: Do not copy-paste one address onto multiple entries. Each business entry must have its own unique address (or empty string if unknown). One shared address across many entries = directory contamination = hard violation.
5. UNIQUENESS: Each business entry must have ITS OWN unique website. NEVER assign the same URL to multiple entries. If you found all businesses on one listing page, that listing page is NOT their website.
6. SUB-BUSINESSES: A business operating INSIDE another business (a restaurant inside a hotel, an outlet inside a mall) must NOT inherit the parent business's website or contact details. If it has no own website, use empty string "".
7. NO HALLUCINATION: Only include businesses you are confident actually exist in {location}. Do not invent, guess, or repeat the same business twice under slightly different names.
{exclude_block}

For each business provide:
- company_name: exact business name
- website: official website URL (own domain only, unique per business) or empty string ""
- description: one short line about what the business does
- contact_page: contact page URL on the official website if known, else empty string ""

Respond ONLY with a valid JSON array. No markdown, no explanations:
[{{"company_name": "...", "website": "https://...", "description": "...", "contact_page": "https://..."}}]"""



def contact_extraction_prompt(company_name: str, location: str, page_text: str) -> str:
    return f"""Extract contact information for the business "{company_name}" from this webpage text. This text comes from the business's OWN official website.

RULES:
- email: official email physically present on the page. Prefer info@, contact@, sales@, office@ over personal or career emails. Exclude career/job emails unless nothing else exists. NEVER use template/placeholder emails like info@your-business-name.com — developer leftovers, not real contacts. NEVER report a parent brand's central reservation email (e.g. centralreservations@hotelbrand.com for one restaurant inside that hotel).
- phone: Indian phone numbers only (+91 format or 10-digit starting with 6-9). If multiple numbers exist, pick the one associated with {location}.
- address: the complete postal address of the {location} premises only - building/street, area, city, state, 6-digit pincode. If the page shows multiple office addresses, pick ONLY the one in {location}. Copy it as one clean readable line exactly as written. Empty string if no {location} address appears on the page.
- Never fabricate any value. Use empty string when a field is not found.

Respond ONLY with valid JSON:
{{"email": "", "phone": "", "address": ""}}

Webpage text:
{page_text[:3000]}"""


def contact_search_prompt(company_name: str, location: str,
                          official_domain: str = '') -> str:
    domain_block = ''
    if official_domain:
        domain_block = f"""
OFFICIAL DOMAIN RULE (HIGHEST PRIORITY):
The company's official website domain is: {official_domain}
Trust and report contact details ONLY if they come from this official domain or are clearly published by the company itself. Contact details found on ANY third-party source - directories (Zomato, JustDial, IndiaMART, Wanderlog, EazyDiner), aggregators, review sites, social media, or any other domain - are NOT acceptable. Report empty strings for those, even if the details look correct.
"""
    return f"""Search the web for the business "{company_name}" located in {location}.

Find its publicly listed contact details from ITS OWN OFFICIAL WEBSITE only.

{domain_block}
STRICT RULES:
- Third-party sources (Zomato, EazyDiner, JustDial, IndiaMART, Wanderlog, hotel websites, any directory or aggregator) are FORBIDDEN as data sources. They show MULTIPLE businesses together and their contacts often belong to the directory or a DIFFERENT business.
- phone: official Indian phone number for its {location} premises, from official sources only
- email: official email from official sources only. NEVER a parent brand's central reservation email (e.g. centralreservations@hotelbrand.com for one restaurant inside that hotel).
- address: full postal address of the {location} premises - street, area, city, state, 6-digit pincode
- Report ONLY details actually found. Never guess or fabricate.
- Empty string for any field not found.

Respond ONLY with valid JSON:
{{"email": "", "phone": "", "address": ""}}"""


def key_persons_prompt(company_name: str, page_text: str, linkedin_urls: list[str] = None) -> str:
    linkedin_block = ''
    if linkedin_urls:
        listed = '\n'.join(f'- {u}' for u in linkedin_urls[:10])
        linkedin_block = f"""
LinkedIn URLs found on website:
{listed}
STRICT MATCHING RULE: Assign a LinkedIn URL to a person ONLY IF their exact first AND last name appear in the URL slug (e.g., "Rajesh Kumar" matches "/in/rajesh-kumar-123"). If the name does not clearly match the URL slug, you MUST return "" for linkedin_url. NEVER guess or assign a generic company LinkedIn page to a person.
"""
    return f"""Identify key decision-makers of "{company_name}" from this webpage text.

{linkedin_block}
RULES:
- Only extract persons whose names are explicitly written on the page.
- Priority roles: Owner, Founder, CEO, Managing Director, Director, General Manager, CTO, CFO, HR Head.
- email: assign ONLY if physically present AND the email prefix contains the person's name or a role (e.g., ceo@). Otherwise "".
- phone: only if physically present.
- linkedin_url: ONLY per the STRICT MATCHING RULE above. Otherwise "".
- Maximum 5 most relevant persons.
- NEVER invent, guess, or hallucinate names, emails, or URLs. Use "" if not found.

Respond ONLY with valid JSON:
{{"persons": [{{"name": "", "designation": "", "email": "", "phone": "", "linkedin_url": ""}}]}}

Webpage text:
{page_text[:4000]}"""


def key_persons_search_prompt(company_name: str, location: str, snippets: str,
                              linkedin_urls: list[str] = None) -> str:
    linkedin_block = ''
    if linkedin_urls:
        listed = '\n'.join(f'- {u}' for u in linkedin_urls[:8])
        linkedin_block = f"""
LinkedIn profile URLs found in search results for this business:
{listed}
MATCHING RULE for linkedin_url:
- Assign a URL to a person ONLY if the profile slug contains BOTH their first name AND last name
- NEVER assign a URL based on company association or guessing
- If no URL contains the person's full name, use empty string ""
"""
    return f"""From these live web search results about the business "{company_name}" in {location}, identify key people associated with THIS business.

{linkedin_block}
STRICT RULES:
- Only persons explicitly mentioned in the results as owner/founder/CEO/GM/director of "{company_name}"
- Ignore reviewers, customers, journalists, or people from other businesses
- email: assign ONLY if physically present AND the email prefix contains the person's name or a role (ceo@, director@). Otherwise empty string.
- Never guess names, emails, phones or URLs. Empty values when not found.
- Maximum 3 most relevant persons

Respond ONLY with valid JSON:
{{"persons": [{{"name": "", "designation": "", "email": "", "phone": "", "linkedin_url": ""}}]}}

Search results:
{snippets[:4000]}"""




def linkedin_profile_extraction_prompt(person_name: str, page_text: str) -> str:
    return f"""From this LinkedIn profile page text of "{person_name}", extract their contact details.

STRICT RULES:
- First VERIFY this profile actually belongs to "{person_name}".
- The name in the page text must match the person's name.
- If it's a different person or the page is a login wall, respond with empty values.
- email: ONLY if physically present in the text (typically in About/Contact section). Empty string otherwise.
- phone: ONLY if physically present. Indian numbers preferred, but any format is accepted. Empty string otherwise.
- Never fabricate.
- Empty strings are the normal outcome — most profiles don't show contact details.

Respond ONLY with valid JSON:
{{"is_match": true, "email": "", "phone": ""}}

Page text:
{page_text[:2500]}
"""







def outreach_email_prompt(company_name: str, industry: str, location: str,
                          website_text: str, sender_info: dict) -> str:
    return f"""You are a professional B2B outreach specialist writing on behalf of {sender_info['company_name']}.

SENDER IDENTITY (use this naturally in the email body):
- Company: {sender_info['company_name']}
- Website: {sender_info['website']}

TARGET COMPANY: {company_name}
INDUSTRY: {industry}
LOCATION: {location}

COMPANY WEBSITE CONTENT (scraped from their official website):
{website_text if website_text.strip() else 'No website content was available.'}

TASK:
Step 1 - Analyze the company: what it does, its products/services, and what makes it notable. Use ONLY the website content above. If the content is insufficient, make no specific claims about the company and keep the analysis general.

Step 2 - Write a professional B2B outreach email:
- Reference their actual business naturally in the opening (only what the analysis supports)
- Introduce {sender_info['company_name']} as a provider of professional business services relevant to their industry
- Keep the value proposition relevant to what this specific company does
- Include a clear, low-pressure call to action (a brief conversation)
- Professional business English, 120-180 words for the body
- No spammy patterns, no exaggerated claims, no fake urgency, no excessive flattery
- Never invent specific details about the company that are not supported by the website content

FORMATTING RULES (STRICT):
- Greeting: use "Dear {company_name} Team," — NEVER placeholders like [Recipient Name], [First Name] or [Name]
- Refer to the sender as "{sender_info['company_name']}" in the body — NEVER placeholders like [Your Company Name] or [Our Company]
- Do NOT add any signature, sign-off, sender name, phone or email at the end — the signature is appended automatically. End the body with the call-to-action paragraph.
- No placeholder brackets of any kind anywhere in the subject or body.

Respond ONLY with valid JSON:
{{"analysis": "one paragraph about what the company does", "subject": "email subject line", "body": "full email body text without the signature"}}"""

