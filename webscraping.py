import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from collections import defaultdict


def get_faculties(base_url):
    """
    Scrape all faculty URLs from the main catalogue page.
    
    Args:
        base_url (str): The base URL of the UAlberta catalogue
        
    Returns:
        list: List of faculty URLs
    """
    r = requests.get(base_url)
    soup = BeautifulSoup(r.content, 'html.parser')
    
    faculties = []
    for link in soup.find_all('a'):
        href = link.get('href')
        if href and "/catalogue/faculty" in href:
            faculties.append(urljoin(base_url, href))
    
    return faculties


def get_departments(faculties, base_url):
    """
    Get all department/course URLs organized by faculty.
    
    Args:
        faculties (list): List of faculty URLs
        base_url (str): The base URL for joining relative paths
        
    Returns:
        dict: Dictionary mapping faculty names to lists of course URLs
    """
    fac_courses = defaultdict(list)
    
    for faculty_url in faculties:
        r = requests.get(faculty_url)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        # Extract faculty name from heading
        heading = soup.find('h1')
        if heading:
            faculty_name = heading.text[13:]  # Remove "Catalogue - " prefix
        else:
            faculty_name = "Unknown Faculty"
        
        # Find all course links
        for ul in soup.find_all('ul'):
            for li in ul.find_all('li'):
                anch = li.find('a')
                if anch:
                    href = anch.get('href')
                    if href and 'catalogue/course/' in href:
                        fac_courses[faculty_name].append(urljoin(base_url, href))
    
    return fac_courses


def prereq_finder(paragraph_tag):
    """
    Extract prerequisite information from a paragraph tag.
    
    Args:
        paragraph_tag: BeautifulSoup tag object containing course description
        
    Returns:
        str or int: Prerequisite text, or -1 if not found
    """
    txt = paragraph_tag.text
    lower_txt = txt.lower()
    
    # Check for plural form first
    index = lower_txt.find("prerequisites:")
    plural = True
    
    if index == -1:
        index = lower_txt.find("prerequisite:")
        plural = False
    
    if index == -1:
        return -1
    
    # Find the end of prerequisite section (period)
    start_offset = 15 if plural else 14
    start_pos = index + start_offset
    
    end = 0
    for char in txt[start_pos:]:
        if char != '.':
            end += 1
        else:
            break
    
    return txt[start_pos:start_pos + end]


def coreq_finder(paragraph_tag):
    """
    Extract corequisite information from a paragraph tag.
    
    Args:
        paragraph_tag: BeautifulSoup tag object containing course description
        
    Returns:
        str or int: Corequisite text, or -1 if not found
    """
    txt = paragraph_tag.text
    lower_txt = txt.lower()
    
    # Check for plural form first
    index = lower_txt.find("corequisites:")
    plural = True
    
    if index == -1:
        index = lower_txt.find("corequisite:")
        plural = False
    
    if index == -1:
        return -1
    
    start_offset = 13 if plural else 12
    return txt[index + start_offset:]


def scrape_course_info(course_url):
    """
    Scrape detailed information for a specific course.
    
    Args:
        course_url (str): URL of the course page
        
    Returns:
        dict: Dictionary containing course information
    """
    r = requests.get(course_url)
    soup = BeautifulSoup(r.content, 'html.parser')
    
    course_info = {
        'url': course_url,
        'prerequisites': None,
        'corequisites': None
    }
    
    # Find course description paragraphs
    for p in soup.find_all('p'):
        prereq = prereq_finder(p)
        if prereq != -1:
            course_info['prerequisites'] = prereq
        
        coreq = coreq_finder(p)
        if coreq != -1:
            course_info['corequisites'] = coreq
    
    return course_info


def main():
    """Main function to orchestrate the scraping process."""
    base_url = "https://apps.ualberta.ca/catalogue"
    
    print("Scraping UAlberta Course Catalogue...")
    print(f"Base URL: {base_url}\n")
    
    # Step 1: Get all faculties
    print("Step 1: Fetching faculties...")
    faculties = get_faculties(base_url)
    print(f"Found {len(faculties)} faculties\n")
    
    # Step 2: Get all course URLs by faculty
    print("Step 2: Fetching course URLs by faculty...")
    fac_courses = get_departments(faculties, base_url)
    
    total_courses = sum(len(courses) for courses in fac_courses.values())
    print(f"Found {total_courses} total courses across {len(fac_courses)} faculties\n")
    
    # Step 3: Example - scrape first course from first faculty
    print("Step 3: Example - scraping course information...")
    for faculty_name, courses in fac_courses.items():
        if courses:
            print(f"\nFaculty: {faculty_name}")
            print(f"Number of courses: {len(courses)}")
            
            # Scrape first course as example
            example_course = scrape_course_info(courses[0])
            print(f"Example course: {example_course['url']}")
            print(f"Prerequisites: {example_course['prerequisites']}")
            print(f"Corequisites: {example_course['corequisites']}")
            break
    
    return fac_courses


if __name__ == "__main__":
    main()
