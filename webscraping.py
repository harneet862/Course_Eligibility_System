"""
UAlberta Course Catalogue Prerequisite Scraper

This script scrapes course information including prerequisites and corequisites
from the University of Alberta course catalogue website.

Author: [Your Name]
Date: October 2025
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from collections import defaultdict
import json


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


def scrape_all_courses(fac_courses):
    """
    Scrape all courses with their prerequisites and corequisites.
    
    Args:
        fac_courses (dict): Dictionary mapping faculty names to course URLs
        
    Returns:
        dict: Nested dictionary structure with all course information
              Format: {'Faculty': {'Department': {'COURSE 123': {'prereq': '...', 'coreq': '...'}}}}
    """
    cors = {}  # Structure: {'Faculty': {'Department': {'COURSE 123': {'prereq': '...', 'coreq': '...'}}}}
    
    # Initialize faculty structure
    for faculty in fac_courses:
        cors[faculty] = {}
    
    # Process each faculty's courses
    for faculty_name, course_urls in fac_courses.items():
        print(f"\nProcessing {faculty_name}...")
        
        for url in course_urls:
            try:
                r = requests.get(url)
                soup = BeautifulSoup(r.content, 'html.parser')
                
                # Get department name
                content_div = soup.find('div', class_='content')
                if content_div:
                    container_div = content_div.find('div', class_='container')
                    if container_div:
                        dept_heading = container_div.find('h1')
                        if dept_heading:
                            dept_name = dept_heading.text
                        else:
                            dept_name = "Unknown Department"
                    else:
                        dept_name = "Unknown Department"
                else:
                    dept_name = "Unknown Department"
                
                # Initialize department if not exists
                if dept_name not in cors[faculty_name]:
                    cors[faculty_name][dept_name] = {}
                
                # Find all course elements
                course_elements = soup.find_all('div', class_=["course", "course ms-3"])
                
                for course_elem in course_elements:
                    # Extract course code
                    course_link = course_elem.find('a')
                    if course_link:
                        course_text = course_link.text
                        ind = course_text.find('-')
                        if ind != -1:
                            course_code = course_text[:ind-1].strip()
                        else:
                            course_code = course_text.strip()
                        
                        # Extract prerequisites and corequisites
                        course_para = course_elem.find('p')
                        prereq = -1
                        coreq = -1
                        
                        if course_para:
                            prereq = prereq_finder(course_para)
                            coreq = coreq_finder(course_para)
                        
                        # Store course information
                        cors[faculty_name][dept_name][course_code] = {
                            'prereq': prereq if prereq != -1 else None,
                            'coreq': coreq if coreq != -1 else None
                        }
                        
                        # Print courses with prerequisites
                        if prereq != -1:
                            print(f"{course_code}: {prereq}")
                
            except Exception as e:
                print(f"Error processing {url}: {e}")
                continue
    
    return cors


def save_to_file(cors, filename='course_prerequisites.json'):
    """
    Save the course structure to a JSON file.
    
    Args:
        cors (dict): Course data structure
        filename (str): Output filename
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(cors, f, indent=2, ensure_ascii=False)
    print(f"\nData saved to {filename}")


def save_prereqs_to_txt(cors, filename='prereq.txt'):
    """
    Save all prerequisites to a text file.
    
    Args:
        cors (dict): Course data structure
        filename (str): Output filename
    """
    with open(filename, 'w', encoding='utf-8') as f:
        for faculty, departments in cors.items():
            for dept, courses in departments.items():
                for course_code, info in courses.items():
                    if info['prereq']:
                        f.write(f"{course_code}: {info['prereq']}\n")
    print(f"Prerequisites saved to {filename}")


def main():
    """Main function to orchestrate the scraping process."""
    base_url = "https://apps.ualberta.ca/catalogue"
    
    print("=" * 60)
    print("UAlberta Course Catalogue Scraper")
    print("=" * 60)
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
    
    # Step 3: Scrape all courses with prerequisites and corequisites
    print("Step 3: Scraping all course information...")
    print("=" * 60)
    cors = scrape_all_courses(fac_courses)
    
    # Step 4: Save results
    print("\n" + "=" * 60)
    print("Step 4: Saving results...")
    save_to_file(cors)
    save_prereqs_to_txt(cors)
    
    # Print summary
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    for faculty, departments in cors.items():
        total_dept_courses = sum(len(courses) for courses in departments.values())
        courses_with_prereqs = sum(
            1 for dept in departments.values() 
            for course in dept.values() 
            if course['prereq']
        )
        print(f"{faculty}: {total_dept_courses} courses, {courses_with_prereqs} with prerequisites")
    
    return cors


if __name__ == "__main__":
    main()
