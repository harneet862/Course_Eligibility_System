# Course_Eligibility_System

This project automates the process of determining which university courses a student is eligible to take, based on prerequisite relationships between courses.

It parses course prerequisite data, builds a dependency graph, and uses topological sorting to compute valid course orderings. The system can handle messy prerequisite text (like “one of A or B” and “A and B”) and even supports automated scraping of course data using Beautiful Soup.

# Features

- Automated Parsing: Extracts course prerequisite relationships from a text file or website.

- Dependency Graph Construction: Builds a directed graph representing course dependencies.

- Topological Sorting: Computes valid course sequences and detects cycles.

- Eligibility Checking: Determines which courses a student can take based on their completed courses.

- Web Scraping Template: Includes a BeautifulSoup-based scraper for automatically gathering course data.

# Project Structure
```
├── eligibility_check.py     # Main script with parser, graph builder, and eligibility logic
├── prereq.txt               # Input file containing course prerequisites
└── README.md                # Project documentation
```
