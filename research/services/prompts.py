"""Central prompt templates for all AI research operations."""

DISCOVERY_EXCLUSION_LIMIT = 30


def company_discovery_prompt(industry: str, location: str, count: int,
                             exclude_names: list[str] = None) -> str:
    exclude_block = ''
    if exclude_names:
        listed = '\n'.join(f'- {name}' for name in exclude_names[:DISCOVERY_EXCLUSION_LIMIT])
        exclude_block = f"""
ALREADY TRIED - DO NOT REPEAT THESE:
{listed}
"""
    industry_guidance = ''
    industry_lower = (industry or '').strip().lower()
    broad_triggers = ('industrial', 'all types', 'any type', 'all companies', 'all businesses')
    if any(word in industry_lower for word in broad_triggers):
        industry_guidance = f"""
SPECIAL INTERPRETATION:
"{industry}" is a BROAD category, not a specific business type. It means: include businesses of ALL industrial/manufacturing types in this area - auto components, pharma, food processing, packaging, plastics, textiles, engineering, chemicals, warehouses, fabrication units, etc.
"""
    return f"""You are a professional business research analyst working on ground-level market research.

TASK: Find {count} real, currently operating businesses matching "{industry}" located in {location}.
{industry_guidance}
This must work for ANY industry - hotels, restaurants, hospitals, schools, real estate, IT, manufacturing, retail, transport, services, etc.

STRICT VERIFICATION RULES:
1. Every business MUST be physically located in {location}. A brand merely serving {location} from another city is NOT acceptable.
2. If a business is part of a national/international chain, identify the specific {location} branch/property and prefer its dedicated website or property page.
3. Never include businesses whose main presence is in another city, even if the same brand name is common.
4. Only include businesses you are confident actually exist in {location}. Do not invent or guess.
5. The location "{location}" may be a specific area, road, or industrial zone within a larger city. Businesses MUST be located IN that exact area/zone. Pithampur Industrial Area ≠ Sanwer Road Industrial Area ≠ Vijay Nagar - these are separate zones even if all in Indore city.
6. Prefer businesses with their own working website (independent businesses, local brands, franchises) over only big national chains.
7. "{location}" me jo area/district specified hai (e.g. Pithampur vs Sanwer Road vs Vijay Nagar - these are DIFFERENT industrial zones), businesses MUST belong to THAT specific zone. A company in a neighboring industrial zone is NOT acceptable even if in the same city.
{exclude_block}
For each business provide:
- company_name: exact business name
- website: official website URL if it has one. Many small industrial units have no website - for these, still include the business (website field empty string "") IF you are confident about its exact name and location.
- description: one line about what the business does
- contact_page: contact or location page URL if known

Respond ONLY with a valid JSON array:
[{{"company_name": "...", "website": "https://...", "description": "...", "contact_page": "https://..."}}]"""


def contact_extraction_prompt(company_name: str, location: str, page_text: str) -> str:
    return f"""Extract contact information for the business "{company_name}" from this webpage text. The business is located in {location}.

RULES:
- email: official email physically present on the page. Prefer info@, contact@, sales@, reservations@, office@ over personal or career emails. Exclude career/job emails unless nothing else exists. NEVER use template/placeholder emails like info@your-business-name.com, yourname@domain.com — these are developer leftovers, not real contacts.
- phone: Indian phone numbers only (+91 format or 10-digit starting with 6-9). If multiple numbers exist, pick the one associated with {location}.
- address: the complete postal address of the {location} premises only - building/street, area, city, state, 6-digit pincode. If the page shows multiple office addresses, pick ONLY the one in {location}. Copy it as one clean readable line exactly as written. Empty string if no {location} address appears on the page.
- Never fabricate any value. Use empty string when a field is not found.

Respond ONLY with valid JSON:
{{"email": "", "phone": "", "address": ""}}

Webpage text:
{page_text[:3000]}"""


def contact_search_prompt(company_name: str, location: str) -> str:
    return f"""Search the web for the business "{company_name}" located in {location}.

Find its publicly listed contact details from official sites or business directories.

STRICT RULES:
- phone: official publicly listed Indian phone number for its {location} premises
- email: official publicly listed email, if any
- address: full postal address of the {location} premises - street, area, city, state, 6-digit pincode
- Report ONLY details actually found in search results. Never guess or fabricate.
- Empty string for any field not found.

Respond ONLY with valid JSON:
{{"email": "", "phone": "", "address": ""}}"""

def key_persons_prompt(company_name: str, page_text: str,
                       linkedin_urls: list[str] = None) -> str:
    linkedin_block = ''
    if linkedin_urls:
        listed = '\n'.join(f'- {u}' for u in linkedin_urls[:10])
        linkedin_block = f"""
LinkedIn profile URLs found on this website:
{listed}
MATCHING RULE for linkedin_url:
- Assign a URL to a person ONLY if the profile slug contains BOTH their first name AND last name (e.g. "Dharmendra Jain" matches /in/ca-dharmendra-jain-95491326)
- NEVER assign a URL based on company association, page location, or guessing
- If no URL contains the person's full name, use empty string ""
"""
    return f"""Identify key decision-makers of the business "{company_name}" from this webpage text.

{linkedin_block}
RULES:
- Only persons whose names are explicitly written on the page
- Priority roles: Owner, Founder, Co-Founder, CEO, Managing Director, Director, General Manager, CTO, CFO, HR Head
- email: assign ONLY if physically present AND the email prefix contains the person's name (e.g. "rajesh.sharma@x.com" for Rajesh Sharma) or a role (ceo@, director@). Otherwise empty string.
- phone: only if physically present in the text
- linkedin_url: only per the MATCHING RULE above
- Maximum 5 most relevant persons
- Empty array if no persons are found. Never invent or force-match any data.

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





















