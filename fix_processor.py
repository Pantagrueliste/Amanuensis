#!/usr/bin/env python3
"""
This script fixes direct text_content() calls in the TEI processor module.
Save this file as fix_text_content.py in your project root and run it.
"""

import os
import re
import sys

# Define the path - provide as command line argument or use default
if len(sys.argv) > 1:
    file_path = sys.argv[1]
else:
    file_path = 'modules/tei/processor.py'

print(f"Fixing text_content() calls in {file_path}")

# Check if the file exists
if not os.path.exists(file_path):
    print(f"Error: File not found: {file_path}")
    sys.exit(1)

# Read the current content
with open(file_path, 'r', encoding='utf-8') as file:
    content = file.read()

# Check if text_content() is directly called
direct_calls = re.findall(r'\.text_content\(\)', content)
if direct_calls:
    print(f"Found {len(direct_calls)} direct calls to text_content()")
    
    # Find line numbers for these calls
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '.text_content()' in line:
            print(f"Line {i+1}: {line.strip()}")
else:
    print("No direct calls to text_content() found")

# Check if our fixed _get_element_text_content method exists and if it uses xpath
get_element_method = re.search(r'def _get_element_text_content.*?xpath\(.*?string\(.*?\)', content, re.DOTALL)
if get_element_method:
    print("\n_get_element_text_content method appears to be properly updated (uses xpath)")
else:
    # Replace the _get_element_text_content method
    print("\nReplacing the _get_element_text_content method...")
    
    # Find the existing method
    old_method_pattern = r'def _get_element_text_content\(self, element: etree\.Element\) -> str:.*?return.*?\.strip\(\)'
    
    # The new implementation 
    new_method = '''def _get_element_text_content(self, element: etree.Element) -> str:
    """
    Get the text content of an element including all child text.
    This preserves ordering of text and is only used for metadata extraction.
    """
    if element is None:
        return ''
    
    try:
        # Try lxml specific method first - lxml has the xpath method
        return element.xpath('string(.)').strip()
    except (AttributeError, TypeError):
        # Fallback for standard ElementTree or when xpath fails
        text = element.text or ''
        for child in element:
            text += self._get_element_text_content(child)
            if child.tail:
                text += child.tail
        return text.strip()'''
    
    # Replace the method
    content = re.sub(old_method_pattern, new_method, content, flags=re.DOTALL)
    print("Replaced _get_element_text_content method")

# Replace all direct text_content() calls
fixed_content = re.sub(r'(\w+)\.text_content\(\)', r'self._get_element_text_content(\1)', content)

# Count how many replacements were made
replacement_count = len(re.findall(r'self._get_element_text_content\(\w+\)', fixed_content)) - len(re.findall(r'self._get_element_text_content\(\w+\)', content))
print(f"\nReplaced {replacement_count} direct text_content() calls")

# Ensure the content actually changed before writing
if fixed_content != content:
    # Write back the fixed content
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(fixed_content)
    print("\nFile updated successfully!")
else:
    print("\nNo changes were made to the file.")

print("\nPlease restart your application to ensure the changes take effect.")