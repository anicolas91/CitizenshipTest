import os
import re
import uuid
import requests
from datetime import date
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from PyPDF2 import PdfReader
from utils.io import save_to_json
from utils.rag import llm
from utils.prompts import CIVICS_QA_UPDATING_PROMPT

def download_civics_documents(save_dir: str = "../documents/") -> Dict[str, any]:
    """
    Download US Civics Test PDFs and study guide from USCIS.
    
    Downloads the 2008 civics test, 2025 civics test, and the civics study guide.
    
    Args:
        save_dir: Directory path where PDFs will be saved (default: "../documents/")
        
    Returns:
        Dictionary containing:
            - "tests" (List[Dict]): List of test metadata with keys:
                - "test_type" (str): Identifier (e.g., "2008_civics_test")
                - "url" (str): Source URL
                - "filename" (str): Local path where saved
            - "guide" (Dict): Guide metadata (same structure)
            
    Example:
        >>> results = download_civics_documents()
        >>> print(results["tests"][0]["filename"])
        "../documents/2008_civics_test.pdf"
        >>> print(results["guide"]["filename"])
        "../documents/civics_guide.pdf"
        
    Raises:
        requests.exceptions.RequestException: If download fails
        OSError: If unable to create directory or write file
    """
    # Create save directory if it doesn't exist
    os.makedirs(save_dir, exist_ok=True)
    
    # Define all documents to download
    tests = [
        {
            "test_type": "2008_civics_test",
            "url": "https://www.uscis.gov/sites/default/files/document/questions-and-answers/100q.pdf"
        },
        {
            "test_type": "2025_civics_test",
            "url": "https://www.uscis.gov/sites/default/files/document/questions-and-answers/2025-Civics-Test-128-Questions-and-Answers.pdf"
        }
    ]
    
    guide = {
        "test_type": "civics_guide",
        "url": "https://www.uscis.gov/sites/default/files/document/brochures/OOC_M-1175_CivicsTextbook_8.5x11_V7_RGB_English_508.pdf"
    }
    
    results = {
        "tests": [],
        "guide": None
    }
    
    # Download all documents
    all_documents = tests + [guide]
    
    print("Downloading civics documents...")
    for doc in all_documents:
        url = doc["url"]
        filename = os.path.join(save_dir, f"{doc['test_type']}.pdf")
        
        try:
            # Download PDF
            print(f"  Downloading {doc['test_type']}...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Save to file
            with open(filename, "wb") as f:
                f.write(response.content)
            
            print(f"    ✓ Saved as {filename}")
            
            # Add filename to result
            doc["filename"] = filename
            
            # Categorize result
            if doc == guide:
                results["guide"] = doc
            else:
                results["tests"].append(doc)
            
        except requests.exceptions.RequestException as e:
            print(f"    ✗ Error downloading {doc['test_type']}: {str(e)}")
            raise
        except OSError as e:
            print(f"    ✗ Error saving {filename}: {str(e)}")
            raise
    
    print(f"\n✓ Successfully downloaded {len(results['tests'])} tests and 1 guide")
    
    return results


def parse_clean_qa_pdf(filename: str) -> List[Dict[str, Any]]:
    """
    Parse a US Civics Test PDF and extract question-answer pairs.
    
    Expects a PDF formatted with:
    - Numbered questions (e.g., "1. What is...")
    - Bullet points (• or ▪) for each answer
    
    Args:
        filename: Path to the PDF file containing civics test questions
        
    Returns:
        List of dictionaries, each containing:
            - "question" (str): The question text
            - "answers" (List[str]): List of acceptable answers
            
    Example:
        [
            {
                "question": "What is the supreme law of the land?",
                "answers": ["the Constitution"]
            },
            ...
        ]
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        Exception: If PDF parsing fails
    """
    try:
        # Parse text from the PDF
        reader = PdfReader(filename)
        pages_text = []
        
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
        
        all_text = "\n".join(pages_text)
        
    except FileNotFoundError:
        raise FileNotFoundError(f"PDF file not found: {filename}")
    except Exception as e:
        raise Exception(f"Failed to parse PDF: {str(e)}")

    # Clean up text
    all_text = all_text.replace("\t", " ").replace("  ", " ")

    # Split the text into question blocks by looking for numbers at the start of a line
    blocks = re.split(r"\n?\s*\d+\.\s+", all_text)

    # Initialize QA pairs list
    qa_pairs = []

    # Skip the first block since it's just intro data
    for block in blocks[1:]:
        block = block.strip()
        if not block:
            continue

        # First line is the question, the rest are answers
        lines = block.splitlines()
        question = lines[0].strip().replace('*', '')
        
        # Extract lines starting with bullets (• or ▪)
        answers = [
            line.strip()[1:].strip()
            for line in lines[1:]
            if line.strip() and line.strip()[0] in ("•", "▪")
        ]

        # Only add if we have both a question and at least one answer
        if question and answers:
            qa_pairs.append({
                "question": question,
                "answers": answers
            })

    return qa_pairs

def clean_text(text: str) -> str:
    """
    Remove footnotes, extra whitespace, and common artifacts from scraped text.
    """
    text = re.sub(r'\[\d+\]', '', text)  # Remove [1], [2] footnotes
    text = re.sub(r'\s+', ' ', text)     # Normalize whitespace
    return text.strip()


def get_officeholder(qid: str) -> str:
    """
    Given a Wikidata entity QID (e.g., President of the US = Q11696),
    return the current officeholder's name.
    """
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    headers = {"User-Agent": "CitizenshipTestApp/0.1 (anicol11@asu.edu)"}
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return f"Error: {r.status_code}"
        
        data = r.json()
    except requests.exceptions.RequestException as e:
        return f"Request error: {str(e)}"
    except ValueError as e:
        return f"JSON parsing error: {str(e)}"

    entity = data.get("entities", {}).get(qid)
    if not entity:
        return "Entity not found"

    claims = entity.get("claims", {})
    
    # Try different properties that might indicate the current holder
    holder_id = None
    for prop in ["P1308", "P488", "P35"]:
        officeholders = claims.get(prop, [])
        if officeholders:
            # Look for the one without an end date (P582)
            for holder in reversed(officeholders):  # Check from most recent
                qualifiers = holder.get("qualifiers", {})
                # If no end date (P582), they're currently in office
                if "P582" not in qualifiers:
                    try:
                        holder_id = holder["mainsnak"]["datavalue"]["value"]["id"]
                        break
                    except (KeyError, TypeError):
                        continue
            
            # If we still don't have one, just take the last
            if not holder_id and officeholders:
                try:
                    holder_id = officeholders[-1]["mainsnak"]["datavalue"]["value"]["id"]
                except (KeyError, TypeError):
                    continue
            
            if holder_id:
                break
    
    if not holder_id:
        return "No officeholder found"

    # Fetch the officeholder's data separately
    holder_url = f"https://www.wikidata.org/wiki/Special:EntityData/{holder_id}.json"
    
    try:
        holder_r = requests.get(holder_url, headers=headers, timeout=10)
        if holder_r.status_code != 200:
            return holder_id

        holder_data = holder_r.json()
    except requests.exceptions.RequestException:
        return holder_id
    except ValueError:
        return holder_id

    holder_name = holder_data.get("entities", {}).get(holder_id, {}).get("labels", {}).get("en", {}).get("value")
    
    if holder_name:
        return holder_name
    return holder_id


def get_current_governors() -> List[str]:
    """
    Scrape Wikipedia for current US governors (states and territories).
    Returns a list of strings in format "STATE/TERRITORY: Governor Name"
    """
    
    url = "https://en.wikipedia.org/wiki/List_of_current_United_States_governors"
    headers = {"User-Agent": "CitizenshipTestApp/0.1 (anicol11@asu.edu)"}
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return [f"Error: {r.status_code}"]
    except requests.exceptions.RequestException as e:
        return [f"Request error: {str(e)}"]
    
    soup = BeautifulSoup(r.content, 'html.parser')
    governors = []
    
    # Find all tables on the page
    tables = soup.find_all('table', {'class': 'wikitable'})
    
    # The first table contains the state governors list
    if tables:
        table = tables[0]
        rows = table.find_all('tr')[1:]  # Skip header row
        
        for row in rows:
            cols = row.find_all(['td', 'th'])
            
            if len(cols) >= 3:
                # Column 0: State, Column 2: Governor name
                state = clean_text(cols[0].get_text(strip=True).replace('(list)', ''))
                governor = clean_text(cols[2].get_text(strip=True))
                
                if state and governor:
                    governors.append(f"{state}: {governor}")
    
    # Find the "Territory governors" heading and get the next table
    territory_heading = soup.find(id="Territory_governors")
    
    if territory_heading:
        territory_table = territory_heading.find_next('table', {'class': 'wikitable'})
        
        if territory_table:
            rows = territory_table.find_all('tr')[1:]  # Skip header row
            
            for row in rows:
                cols = row.find_all(['td', 'th'])
                
                if len(cols) >= 3:
                    # Column 0: Territory, Column 2: Governor name
                    territory = clean_text(cols[0].get_text(strip=True).replace('(list)', ''))
                    governor = clean_text(cols[2].get_text(strip=True))
                    
                    if territory and governor:
                        governors.append(f"{territory}: {governor}")
    
    return governors


def get_current_senators() -> List[str]:
    """
    Scrape Wikipedia for current US senators.
    Returns a list of strings in format "STATE: Senator1, Senator2"
    """
    url = "https://en.wikipedia.org/wiki/List_of_current_United_States_senators"
    headers = {"User-Agent": "CitizenshipTestApp/0.1 (anicol11@asu.edu)"}
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return [f"Error: {r.status_code}"]
    except requests.exceptions.RequestException as e:
        return [f"Request error: {str(e)}"]
    
    soup = BeautifulSoup(r.content, 'html.parser')
    senators_by_state = {}
    
    # Find all tables - the 5th table (index 4) contains the full senator list
    tables = soup.find_all('table', {'class': 'wikitable'})
    
    if len(tables) >= 5:
        table = tables[4]
        rows = table.find_all('tr')[1:]  # Skip header row
        
        current_state = None
        
        for row in rows:
            cols = row.find_all(['td', 'th'])
            
            if len(cols) >= 3:
                first_col = cols[0].get_text(strip=True)
                
                # If first column has text, it's a new state with first senator
                if first_col:
                    current_state = clean_text(first_col)
                    senator = clean_text(cols[2].get_text(strip=True))
                else:
                    # Empty first column means second senator for current state
                    senator = clean_text(cols[1].get_text(strip=True))
                
                # Add senator to state's list
                if current_state and senator:
                    if current_state not in senators_by_state:
                        senators_by_state[current_state] = []
                    senators_by_state[current_state].append(senator)
    
    # Format as sorted list
    result = []
    for state in sorted(senators_by_state.keys()):
        senators = ", ".join(senators_by_state[state])
        result.append(f"{state}: {senators}")
    
    return result


def get_current_representatives() -> List[str]:
    """
    Scrape Wikipedia for current US representatives.
    Returns a list of strings in format "STATE: Rep1, Rep2, Rep3..."
    """
    
    url = "https://en.wikipedia.org/wiki/List_of_current_United_States_representatives"
    headers = {"User-Agent": "CitizenshipTestApp/0.1 (anicol11@asu.edu)"}
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return [f"Error: {r.status_code}"]
    except requests.exceptions.RequestException as e:
        return [f"Request error: {str(e)}"]
    
    soup = BeautifulSoup(r.content, 'html.parser')
    reps_by_state = {}
    
    # Find the "List of representatives" heading
    heading = soup.find(['h2', 'h3'], string=re.compile(r'List of representatives', re.IGNORECASE))
    
    if not heading:
        # Try finding by id
        heading = soup.find(id="List_of_representatives")
    
    target_table = None
    if heading:
        # Find the next table after this heading
        target_table = heading.find_next('table', {'class': 'wikitable'})
    
    if target_table:
        rows = target_table.find_all('tr')[1:]  # Skip header row
        
        # Pattern to match valid district entries: "State Number" or "State at-large"
        district_pattern = re.compile(r'^[A-Z][a-z]+(\s[A-Z][a-z]+)*\s+(\d+|at-large)$')
        
        for row in rows:
            cols = row.find_all(['td', 'th'])
            
            # We need at least 2 columns: District and Member
            if len(cols) >= 2:
                district_text = cols[0].get_text(strip=True)
                member_text = clean_text(cols[1].get_text(strip=True))
                
                # Only process rows that match the district pattern
                if district_pattern.match(district_text) and member_text:
                    # Extract state name from district column
                    state = ' '.join(district_text.split()[:-1])  # Everything except the last word
                    
                    if state not in reps_by_state:
                        reps_by_state[state] = []
                    reps_by_state[state].append(member_text)
    
    # Format as sorted list
    result = []
    for state in sorted(reps_by_state.keys()):
        reps = ", ".join(reps_by_state[state])
        result.append(f"{state}: {reps}")
    
    return result

def get_current_officials_summary() -> str:
    """
    Retrieves current US government officeholders and formats them into a readable reference string.
    
    Returns a formatted string containing:
    - All US Representatives (by state)
    - All US Senators (by state)
    - All US Governors (states and territories)
    - President of the United States
    - Speaker of the House
    - Vice President
    - Chief Justice of the Supreme Court
    
    Returns:
        str: Multi-line formatted string with all current officeholders
        
    Note:
        Data is scraped from Wikipedia and Wikidata. May contain errors
        if scraping fails or data is unavailable.
    """
    
    # Scrape main information
    senators = '\n'.join(get_current_senators())
    representatives = '\n'.join(get_current_representatives())
    governors = '\n'.join(get_current_governors())
    president = get_officeholder("Q11696")
    speaker = get_officeholder("Q912994")
    vice_president = get_officeholder("Q11699")
    chief_justice = get_officeholder("Q11201")

    # Format output
    references = f"""
Current Representatives:
{representatives}

Current Senators:
{senators}

Current Governors:
{governors}

President of the United States:
{president}

Speaker of the House:
{speaker}

Vice President:
{vice_president}

Chief Justice of the Supreme Court:
{chief_justice}
"""

    return references.strip()


def populate_missing_questions(qa_pairs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Populate placeholder answers in civics test questions with current information.
    
    Scans question-answer pairs for placeholder responses (e.g., "answers will vary",
    "visit uscis.gov") and uses an LLM to retrieve up-to-date answers based on
    current government officials and civic information.
    
    Args:
        qa_pairs: List of dictionaries, each containing:
            - "question" (str): The civics test question
            - "answers" (List[str]): List of acceptable answers
            
    Returns:
        List[Dict[str, Any]]: Updated qa_pairs with populated answers
        
    Example:
        >>> qa_pairs = [
        ...     {"question": "Who is the President?", "answers": ["answers will vary"]}
        ... ]
        >>> updated = populate_missing_questions(qa_pairs)
        >>> updated[0]["answers"]
        ["Joseph R. Biden Jr.", "Joe Biden", "Biden"]
        
    Note:
        - Modifies the qa_pairs list in place and returns it
        - Prints progress for each placeholder found
        - Requires references to be available in scope (current officials data)
    """
    # Get today's date for context
    today = date.today()

    # Keywords that flag placeholder answers
    placeholder_keywords = ["answers will vary", "visit uscis.gov"]
    
    # Get current officeholder references
    references = get_current_officials_summary()

    for qa_pair in qa_pairs:
        question = qa_pair["question"]
        
        # Skip if no answers exist
        if not qa_pair.get("answers"):
            continue
            
        answer = qa_pair["answers"][0].lower()

        # Check if answer is a placeholder
        if any(keyword in answer for keyword in placeholder_keywords):
            print(f"Variable response found, extracting latest answer for:")
            print(f"  Question: {question}")

            # Setup prompt with current context
            user_prompt = CIVICS_QA_UPDATING_PROMPT.format(
                today=today,
                question=question,
                references=references
            )

            try:
                # Call LLM to get current answer
                response = llm(
                    system_prompt="You are a helpful assistant that provides accurate, up-to-date information about US civics and government.",
                    user_prompt=user_prompt,
                    temperature=0.5
                )

                # Parse and update answers
                if "answers" in response:
                    qa_pair["answers"] = response["answers"]
                    print(f"  ✓ Updated with {len(response['answers'])} answer(s)\n")
                else:
                    print(f"  ✗ Warning: No 'answers' key in LLM response\n")
                    
            except Exception as e:
                print(f"  ✗ Error calling LLM: {str(e)}\n")
    
    return qa_pairs

import os
from typing import List, Dict, Any


def process_civics_tests(
    download_info: Dict[str, Any],
    save_dir: str = '../documents/'
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Process civics test PDFs: parse Q&A pairs, populate missing answers, and save to JSON.
    
    Takes the output from download_civics_documents(), processes each test PDF to extract
    question-answer pairs, fills in variable answers (like current officials), and saves
    the results as JSON files.
    
    Args:
        download_info: Dictionary from download_civics_documents() containing:
            - "tests" (List[Dict]): List of test metadata with "test_type" keys
        save_dir: Directory where PDFs are located and JSON files will be saved
        
    Returns:
        Dict mapping test types to their processed Q&A pairs:
            {
                "2008_civics_test": [{"question": "...", "answers": [...]}],
                "2025_civics_test": [{"question": "...", "answers": [...]}]
            }
            
    Example:
        >>> download_info = download_civics_documents()
        >>> results = process_civics_tests(download_info)
        >>> print(len(results["2008_civics_test"]))
        100
        
    Side Effects:
        - Saves JSON files to save_dir for each test
        - Prints progress for each test processed
    """
    civics_tests = download_info['tests']
    all_qa_pairs = {}
    
    print(f"Processing {len(civics_tests)} civics tests...")
    
    for test in civics_tests:
        test_type = test["test_type"]
        print(f"\n  Processing {test_type}...")
        
        # Get filename with civics test
        pdf_filename = os.path.join(save_dir, f"{test_type}.pdf")
        
        # Validate PDF exists
        if not os.path.exists(pdf_filename):
            print(f"    ✗ Warning: {pdf_filename} not found, skipping...")
            continue
        
        try:
            # Parse the Q&A from the PDF
            print(f"    • Parsing PDF...")
            qa_pairs = parse_clean_qa_pdf(pdf_filename)
            print(f"    • Extracted {len(qa_pairs)} questions")
            
            # Replace variable/undefined answers with latest info
            print(f"    • Populating missing answers...")
            qa_pairs = populate_missing_questions(qa_pairs)
            
            # Save to JSON
            json_filename = os.path.join(save_dir, f"{test_type}_qa_pairs.json")
            save_to_json(json_filename, qa_pairs)
            print(f"    ✓ Saved {len(qa_pairs)} Q&A pairs to {json_filename}")
            
            # Store in results
            all_qa_pairs[test_type] = qa_pairs
            
        except Exception as e:
            print(f"    ✗ Error processing {test_type}: {str(e)}")
            continue
    
    print(f"\n✓ Processed {len(all_qa_pairs)} tests successfully")
    return all_qa_pairs

def extract_clean_text_from_guide(filename: str) -> str:
    """
    Extract and clean text from the US Civics Test guide PDF.
    
    Removes headers, footers, instructional boxes, test sections, and other
    non-content elements from the PDF to extract only the main educational text.
    
    Args:
        filename: Path to the civics guide PDF file
        
    Returns:
        str: Cleaned text content from the PDF, with filtered pages joined by newlines
        
    Processing steps:
        - Skips first 4 pages (cover/intro)
        - Skips last 7 pages (appendix/back matter)
        - Removes "TEST YOUR KNOWLEDGE" sections
        - Removes instructional boxes and image credits
        - Removes page numbers and book titles
        - Filters out chapter headers
        
    Example:
        >>> text = extract_clean_text_from_guide("documents/civics_guide.pdf")
        >>> print(len(text))
        45000
    """
    reader = PdfReader(filename)
    all_text = []
    
    total_pages = len(reader.pages)
    
    for i, page in enumerate(reader.pages):
        # Skip first 4 pages (cover, title, TOC)
        if i < 4:
            continue
        
        # Skip last 7 pages (appendix, back matter)
        if i >= total_pages - 7:
            continue
        
        text = page.extract_text()
        if not text:
            continue
        
        # Remove common repeating sections
        lines = text.split('\n')
        filtered_lines = []
        skip_section = False
        skip_test_section = False  # Separate flag for TEST YOUR KNOWLEDGE
        
        for line in lines:
            # Check if line contains "TEST YOUR KNOWLEDGE"
            if "TEST YOUR KNOWLEDGE" in line.upper():
                # Keep text before "TEST YOUR KNOWLEDGE" if any
                before_test = re.split(r'TEST YOUR KNOWLEDGE', line, flags=re.IGNORECASE)[0]
                if before_test.strip():
                    filtered_lines.append(before_test)
                skip_test_section = True
                continue
            
            # Check if we've reached the end of TEST YOUR KNOWLEDGE section
            if skip_test_section and "you may study just the questions that have been marked with an asterisk" in line.lower():
                skip_test_section = False
                continue  # Skip this line too
            
            # If we're in TEST YOUR KNOWLEDGE section, skip everything
            if skip_test_section:
                continue
            
            # Skip instruction boxes, image credits, and common footers
            if any(phrase in line for phrase in [
                "Within each chapter there are some",
                "sentences and phrases that are written",
                "in bold font",
                "number in a red box",
                "Civics Test Questions",
                "For example, the following sentence",
                "This sentence is from Question",
                "Photo by",
                "Courtesy of",
                "Associate Justice Sonia",
                "President George W. Bush",
                "President Obama"
            ]):
                skip_section = True
                continue
            
            # Resume after sections end (look for next chapter or substantial content)
            if skip_section and (line.startswith("CHAPTER") or len(line.strip()) > 50):
                skip_section = False
            
            if not skip_section:
                # Remove the book title from the line (case insensitive)
                line = re.sub(
                    r'ONE NATION, ONE PEOPLE:?\s*(THE USCIS CIVICS TEST TEXTBOOK)?',
                    '',
                    line,
                    flags=re.IGNORECASE
                )
                
                # Remove 1-3 digit numbers that appear right before a period or colon
                line = re.sub(r'\s\d{1,3}\.', '.', line)
                line = re.sub(r'\s\d{1,3}\:', ':', line)
                line = re.sub(r'^\d{1,3}\.\s*', '', line)
                line = re.sub(r'^\d{1,3}\:\s*', ':', line)
                line = re.sub(r'^\s*\d{1,3}\s*$', '', line)
                
                # Remove leftover info from example question boxes
                line = line.replace('written? 1787  66  ', '')
                
                # Skip lines that start with CHAPTER
                if line.strip().startswith("CHAPTER"):
                    continue
                
                # Only add non-empty lines to filtered_lines
                if line.strip():
                    filtered_lines.append(line)
        
        # Add filtered page content
        if filtered_lines:
            all_text.append('\n'.join(filtered_lines))
    
    # convert list to dict with page info and uuid
    data = []
    for i, text in enumerate(all_text):
        entry={
            "page_no" : i + 4 + 1,
            "uuid" : str(uuid.uuid4()),
            "text" : text
            }
        data.append(entry)

    return data

