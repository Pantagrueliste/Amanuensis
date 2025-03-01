"""
TEIProcessor: Core module for processing TEI XML documents
Extracts abbreviations and their context for dataset creation.
Directly manipulates XML nodes without text extraction.
"""

import os
import logging
import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass

# Add base modules directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# Require lxml for proper XML handling 
from lxml import etree

# Import unicode replacement for abbreviation normalization
try:
    from unicode_replacement import UnicodeReplacement
except ImportError:
    logging.warning("Unicode replacement module not available. Abbreviation normalization will be limited.")


@dataclass
class AbbreviationInfo:
    """Data class for storing information about an abbreviation."""
    abbr_element: etree.Element  # The XML element itself
    abbr_id: Optional[str]       # Element ID if present
    parent_element: etree.Element
    xpath: str                   # XPath to locate the element
    file_path: str
    metadata: Dict[str, Any]
    normalized_form: Optional[str] = None  # Normalized form for dictionary lookup
    

class TEIProcessor:
    """
    XML-aware processor for TEI documents that preserves structure and works directly 
    with XML nodes without string extraction.
    """
    
    def __init__(self, config):
        """
        Initialize TEI processor with configuration.
        
        Args:
            config: Configuration object with settings for TEI processing
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # TEI namespace
        self.tei_ns = config.get('xml_processing', 'tei_namespace', 'http://www.tei-c.org/ns/1.0')
        self.namespaces = {'tei': self.tei_ns}
        
        # XPath queries for abbreviation elements
        self.abbr_xpath = config.get('xml_processing', 'abbr_xpath', '//tei:abbr')
        self.g_abbr_xpath = '//tei:g[@ref="char:cmbAbbrStroke" or @ref="char:abque"][not(ancestor::tei:expan)]'
        self.am_abbr_xpath = '//tei:am[not(ancestor::tei:expan)]'
        
        # Output structure settings
        self.use_choice_tags = config.get('xml_processing', 'use_choice_tags', True)
        self.add_xml_ids = config.get('xml_processing', 'add_xml_ids', True)
        
        # Normalization settings for dictionary lookup
        self.use_normalization = config.get('settings', 'normalize_abbreviations', True)
        
        # Initialize statistics
        self.stats = {
            'documents_processed': 0,
            'abbreviations_found': 0,
            'already_expanded': 0,
            'normalized_abbr': 0,
        }
    
    def parse_document(self, file_path: Union[str, Path]) -> Tuple[List[AbbreviationInfo], Optional[etree.ElementTree]]:
        """
        Parse a TEI XML document and extract abbreviation elements.
        
        Args:
            file_path: Path to the TEI XML document
            
        Returns:
            Tuple containing:
            - List of AbbreviationInfo objects
            - XML tree object for later modification
        """
        try:
            # Convert to Path object if string
            if isinstance(file_path, str):
                file_path = Path(file_path)
                
            self.logger.info(f"Parsing TEI document: {file_path}")
            
            # Parse the XML document with lxml preserving whitespace
            parser = etree.XMLParser(remove_blank_text=True)
            tree = etree.parse(str(file_path), parser=parser)
            root = tree.getroot()
            
            # Extract metadata from TEI header for context
            metadata = self._extract_metadata(root)
            
            # Find all abbreviation elements using XPath
            abbreviations = []
            
            # 1. Standard <abbr> elements
            abbr_elements = root.xpath(self.abbr_xpath, namespaces=self.namespaces)
            if abbr_elements:
                self.logger.info(f"Found {len(abbr_elements)} standard <abbr> elements in {file_path}")
                for abbr_el in abbr_elements:
                    if not self._is_already_expanded(abbr_el):
                        abbr_info = self._process_abbr_element(abbr_el, file_path, metadata)
                        if abbr_info:
                            abbreviations.append(abbr_info)
            
            # 2. Special <g> elements with abbreviation markers
            if self.config.get('settings', 'process_g_elements', True):
                g_elements = root.xpath(self.g_abbr_xpath, namespaces=self.namespaces)
                if g_elements:
                    self.logger.info(f"Found {len(g_elements)} special <g> elements in {file_path}")
                    for g_el in g_elements:
                        if not self._is_already_expanded(g_el):
                            abbr_info = self._process_g_element(g_el, file_path, metadata)
                            if abbr_info:
                                abbreviations.append(abbr_info)
            
            # 3. <am> elements (abbreviation markers)
            am_elements = root.xpath(self.am_abbr_xpath, namespaces=self.namespaces)
            if am_elements:
                self.logger.info(f"Found {len(am_elements)} <am> abbreviation marker elements in {file_path}")
                for am_el in am_elements:
                    if not self._is_already_expanded(am_el):
                        abbr_info = self._process_am_element(am_el, file_path, metadata)
                        if abbr_info:
                            abbreviations.append(abbr_info)
            
            # Update statistics
            self.stats['abbreviations_found'] += len(abbreviations)
            self.stats['documents_processed'] += 1
            
            return abbreviations, tree
            
        except Exception as e:
            self.logger.error(f"Error parsing TEI document {file_path}: {e}")
            return [], None
    
    def _extract_metadata(self, root: etree.Element) -> Dict[str, Any]:
        """Extract metadata from TEI header using XPath."""
        metadata = {
            'title': '',
            'author': '',
            'date': '',
            'language': '',
            'source': '',
            'genre': '',
        }
        
        try:
            # Extract title (using XPath directly)
            title_elements = root.xpath('//tei:titleStmt/tei:title', namespaces=self.namespaces)
            if title_elements:
                metadata['title'] = self._get_element_text_content(title_elements[0])
            
            # Extract author
            author_elements = root.xpath('//tei:titleStmt/tei:author', namespaces=self.namespaces)
            if author_elements:
                metadata['author'] = self._get_element_text_content(author_elements[0])
            
            # Extract date - first from publicationStmt, then from sourceDesc
            date_elements = root.xpath('//tei:publicationStmt/tei:date', namespaces=self.namespaces)
            if not date_elements:
                date_elements = root.xpath('//tei:sourceDesc//tei:date', namespaces=self.namespaces)
            if date_elements:
                # Use @when attribute if available, otherwise use text content
                metadata['date'] = date_elements[0].get('when', self._get_element_text_content(date_elements[0]))
            
            # Extract language
            language_elements = root.xpath('//tei:profileDesc/tei:langUsage/tei:language', 
                                          namespaces=self.namespaces)
            if language_elements:
                metadata['language'] = language_elements[0].get('ident', '')
            
            # Extract source
            source_elements = root.xpath('//tei:sourceDesc/tei:bibl', namespaces=self.namespaces)
            if source_elements:
                metadata['source'] = self._get_element_text_content(source_elements[0])
                
            # Extract genre from textClass
            text_class_elements = root.xpath('//tei:profileDesc/tei:textClass//tei:term', 
                                            namespaces=self.namespaces)
            if text_class_elements:
                genres = [self._get_element_text_content(term) for term in text_class_elements[:3]]
                metadata['genre'] = ', '.join(filter(None, genres))
                
        except Exception as e:
            self.logger.error(f"Error extracting metadata: {e}")
        
        return metadata
    
    def _get_element_text_content(self, element: etree.Element) -> str:
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
            return text.strip()
    
    def _get_xpath(self, element: etree.Element) -> str:
        """
        Generate a unique XPath to locate an element.
        Uses lxml's getpath which creates position predicates.
        """
        if element is None:
            return ""
        
        try:
            tree = element.getroottree()
            if tree is not None:
                return tree.getpath(element)
        except Exception as e:
            self.logger.error(f"Error generating XPath: {e}")
            
        # Fallback implementation
        path = []
        parent = element.getparent()
        while element is not None:
            # Get local name without namespace
            tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            
            if parent is None:
                # Root element
                path.insert(0, f'/{tag}')
                break
            
            # Calculate position among siblings with same tag
            position = 1
            for sibling in parent:
                if sibling == element:
                    break
                if sibling.tag == element.tag:
                    position += 1
            
            path.insert(0, f'{tag}[{position}]')
            element = parent
            parent = element.getparent()
            
        return '/'.join(path)
    
    def _is_already_expanded(self, element: etree.Element) -> bool:
        """
        Check if an abbreviation element already has an expansion.
        
        Args:
            element: The abbreviation element to check
            
        Returns:
            True if it's already expanded, False otherwise
        """
        # Case 1: Element is inside a <choice> with an <expan> sibling
        parent = element.getparent()
        if parent is not None and parent.tag.endswith('choice'):
            for sibling in parent:
                if sibling != element and sibling.tag.endswith('expan'):
                    self.stats['already_expanded'] += 1
                    return True
        
        # Case 2: Element is an <am> inside an <abbr> inside a <choice> with an <expan>
        if element.tag.endswith('am'):
            abbr_parent = parent
            if abbr_parent is not None and abbr_parent.tag.endswith('abbr'):
                choice_parent = abbr_parent.getparent()
                if choice_parent is not None and choice_parent.tag.endswith('choice'):
                    for sibling in choice_parent:
                        if sibling != abbr_parent and sibling.tag.endswith('expan'):
                            self.stats['already_expanded'] += 1
                            return True
        
        # Case 3: Element has a following <expan> sibling (without <choice>)
        next_sibling = element.getnext()
        if next_sibling is not None and next_sibling.tag.endswith('expan'):
            self.stats['already_expanded'] += 1
            return True
            
        # Not expanded
        return False
    
    def _process_abbr_element(self, abbr_el: etree.Element, file_path: str, metadata: Dict[str, Any]) -> Optional[AbbreviationInfo]:
        """
        Process a standard <abbr> element.
        
        Args:
            abbr_el: The <abbr> element
            file_path: Path to the source file
            metadata: Document metadata
            
        Returns:
            AbbreviationInfo object or None if processing fails
        """
        # Get element ID if present
        abbr_id = abbr_el.get('{http://www.w3.org/XML/1998/namespace}id') or abbr_el.get('id')
        
        # Get parent element for context
        parent = abbr_el.getparent()
        if parent is None:
            self.logger.warning(f"Abbr element without parent found in {file_path}")
            return None
        
        # Get XPath for locating the element
        xpath = self._get_xpath(abbr_el)
        
        # Create normalized form for dictionary lookup
        normalized_form = self._normalize_abbr_element(abbr_el)
            
        return AbbreviationInfo(
            abbr_element=abbr_el,
            abbr_id=abbr_id,
            parent_element=parent,
            xpath=xpath,
            file_path=str(file_path),
            metadata=metadata,
            normalized_form=normalized_form
        )
    
    def _process_g_element(self, g_el: etree.Element, file_path: str, metadata: Dict[str, Any]) -> Optional[AbbreviationInfo]:
        """
        Process a <g> element representing an abbreviation marker.
        
        Args:
            g_el: The <g> element
            file_path: Path to the source file
            metadata: Document metadata
            
        Returns:
            AbbreviationInfo object or None if processing fails
        """
        # Get ref attribute to identify abbreviation type
        ref = g_el.get('ref', '')
        if not ref:
            self.logger.warning(f"G element without ref attribute found in {file_path}")
            return None
        
        # Get element ID if present
        g_id = g_el.get('{http://www.w3.org/XML/1998/namespace}id') or g_el.get('id')
        
        # Get parent element for context
        parent = g_el.getparent()
        if parent is None:
            self.logger.warning(f"G element without parent found in {file_path}")
            return None
        
        # Get XPath for locating the element
        xpath = self._get_xpath(g_el)
        
        # Create normalized form for dictionary lookup
        normalized_form = self._normalize_g_element(g_el)
            
        return AbbreviationInfo(
            abbr_element=g_el,
            abbr_id=g_id,
            parent_element=parent,
            xpath=xpath,
            file_path=str(file_path),
            metadata=metadata,
            normalized_form=normalized_form
        )
    
    def _process_am_element(self, am_el: etree.Element, file_path: str, metadata: Dict[str, Any]) -> Optional[AbbreviationInfo]:
        """
        Process an <am> (abbreviation marker) element.
        
        Args:
            am_el: The <am> element
            file_path: Path to the source file
            metadata: Document metadata
            
        Returns:
            AbbreviationInfo object or None if processing fails
        """
        # Get element ID if present
        am_id = am_el.get('{http://www.w3.org/XML/1998/namespace}id') or am_el.get('id')
        
        # Get parent element for context
        parent = am_el.getparent()
        if parent is None:
            self.logger.warning(f"AM element without parent found in {file_path}")
            return None
        
        # Get XPath for locating the element
        xpath = self._get_xpath(am_el)
        
        # Create normalized form for dictionary lookup
        normalized_form = self._normalize_am_element(am_el)
            
        return AbbreviationInfo(
            abbr_element=am_el,
            abbr_id=am_id,
            parent_element=parent,
            xpath=xpath,
            file_path=str(file_path),
            metadata=metadata,
            normalized_form=normalized_form
        )
    
    def _normalize_abbr_element(self, abbr_el: etree.Element) -> str:
        """
        Create a normalized text representation of an <abbr> element.
        This is used for dictionary lookup only, not for display.
        
        Args:
            abbr_el: The <abbr> element to normalize
            
        Returns:
            Normalized abbreviation string
        """
        if not self.use_normalization:
            # Just return the text content if not normalizing
            return self._get_element_text_content(abbr_el)
        
        # Get the raw text content
        text = self._get_element_text_content(abbr_el)
        
        # Apply Unicode normalization 
        try:
            # Try to use the UnicodeReplacement static method
            normalized = UnicodeReplacement.normalize_abbreviation(text)
            if normalized != text:
                self.stats['normalized_abbr'] += 1
            return normalized
        except (NameError, AttributeError):
            # Fallback with basic normalization
            return self._basic_normalize_text(text)
    
    def _normalize_g_element(self, g_el: etree.Element) -> str:
        """
        Create a normalized representation of a <g> abbreviation element.
        Handles different types of <g> elements based on their @ref attribute.
        
        Args:
            g_el: The <g> element to normalize
            
        Returns:
            Normalized abbreviation string
        """
        ref = g_el.get('ref', '')
        
        # Different handling based on abbreviation type
        if ref == 'char:cmbAbbrStroke':
            # Combining macron - find preceding character and add $
            parent = g_el.getparent()
            if parent is not None and parent.text:
                # Get the character immediately before the <g> element
                prev_text = parent.text
                if prev_text.strip():
                    base_char = prev_text.strip()[-1]
                    return f"{base_char}$"
            
            # Fallback if we can't find the base character
            return "m$"  # Common default for macron
            
        elif ref == 'char:abque':
            # This is the special 'que' abbreviation
            return "q$"
        
        # Unknown <g> type, return as is
        return self._get_element_text_content(g_el)
    
    def _normalize_am_element(self, am_el: etree.Element) -> str:
        """
        Create a normalized representation of an <am> abbreviation marker element.
        
        Args:
            am_el: The <am> element to normalize
            
        Returns:
            Normalized abbreviation string
        """
        # Check for nested <g> elements which are common in <am>
        g_elements = am_el.xpath('.//tei:g', namespaces=self.namespaces)
        if g_elements:
            # Process the first <g> element as representative
            return self._normalize_g_element(g_elements[0])
        
        # If no <g> elements, use the text content
        text = self._get_element_text_content(am_el)
        
        # Basic normalization on the text content
        return self._basic_normalize_text(text)
    
    def _basic_normalize_text(self, text: str) -> str:
        """
        Basic normalization of abbreviation text with common patterns.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        normalized = text
        
        # Handle combining macron (Unicode U+0304)
        macron_pattern = r'([a-zA-Z])\u0304'
        if re.search(macron_pattern, normalized):
            normalized = re.sub(macron_pattern, r'\1$', normalized)
        
        # Handle precomposed characters with macrons
        for char, repl in [('ā', 'a$'), ('ē', 'e$'), ('ī', 'i$'), ('ō', 'o$'), ('ū', 'u$'), 
                           ('n̄', 'n$'), ('m̄', 'm$')]:
            normalized = normalized.replace(char, repl)
        
        # Handle characters with tildes
        for char, repl in [('ã', 'a$'), ('ẽ', 'e$'), ('ĩ', 'i$'), ('õ', 'o$'), ('ũ', 'u$'), 
                           ('ñ', 'n$')]:
            normalized = normalized.replace(char, repl)
        
        # Handle period abbreviations (e.g., Ill.mo → Ill$mo)
        period_regex = r'\.([a-z]{2})$'
        normalized = re.sub(period_regex, r'$\1', normalized)
        
        return normalized
    
    def add_expansion(self, abbr_info: AbbreviationInfo, expansion: str) -> bool:
        """
        Add an expansion to an abbreviation element, preserving XML structure.
        
        Args:
            abbr_info: Information about the abbreviation
            expansion: The expansion text to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            abbr_element = abbr_info.abbr_element
            parent = abbr_info.parent_element
            
            if parent is None:
                self.logger.error("Cannot add expansion: parent element is None")
                return False
            
            # Different handling based on element type
            element_type = abbr_element.tag.split('}')[-1] if '}' in abbr_element.tag else abbr_element.tag
            
            if element_type == 'abbr':
                # Standard <abbr> element
                return self._add_expansion_to_abbr(abbr_element, parent, expansion, abbr_info.abbr_id)
            
            elif element_type == 'g':
                # Special <g> abbreviation marker
                return self._add_expansion_to_g(abbr_element, parent, expansion, abbr_info.abbr_id)
            
            elif element_type == 'am':
                # <am> abbreviation marker
                return self._add_expansion_to_am(abbr_element, parent, expansion, abbr_info.abbr_id)
            
            else:
                self.logger.error(f"Unknown abbreviation element type: {element_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error adding expansion: {e}")
            return False
    
    def _add_expansion_to_abbr(self, abbr_el: etree.Element, parent: etree.Element, 
                               expansion: str, abbr_id: Optional[str]) -> bool:
        """Add expansion to a standard <abbr> element."""
        
        # Check if parent is already a <choice> element
        if parent.tag.endswith('choice'):
            # Look for existing <expan> sibling
            for child in parent:
                if child.tag.endswith('expan'):
                    # Update existing expansion
                    child.text = expansion
                    return True
            
            # No <expan> found, create new one
            expan = self._create_expansion_element(expansion, abbr_id)
            parent.append(expan)
            return True
            
        elif self.use_choice_tags:
            # Create a new <choice> structure
            choice = self._create_element('choice')
            
            # Find position of abbr in parent
            abbr_index = -1
            for i, child in enumerate(parent):
                if child == abbr_el:
                    abbr_index = i
                    break
                    
            if abbr_index == -1:
                self.logger.error("Cannot find abbr element within parent")
                return False
            
            # Create expansion element
            expan = self._create_expansion_element(expansion, abbr_id)
            
            # Remove abbr from parent and add to choice
            parent.remove(abbr_el)
            choice.append(abbr_el)
            choice.append(expan)
            
            # Insert choice at the same position
            parent.insert(abbr_index, choice)
            return True
            
        else:
            # Simple approach: just add <expan> after <abbr>
            expan = self._create_expansion_element(expansion, abbr_id)
            
            # Find position of abbr in parent
            abbr_index = -1
            for i, child in enumerate(parent):
                if child == abbr_el:
                    abbr_index = i
                    break
                    
            if abbr_index == -1:
                self.logger.error("Cannot find abbr element within parent")
                return False
                
            # Insert expan after abbr
            parent.insert(abbr_index + 1, expan)
            return True
    
    def _add_expansion_to_g(self, g_el: etree.Element, parent: etree.Element, 
                           expansion: str, g_id: Optional[str]) -> bool:
        """Add expansion to a <g> abbreviation element."""
        
        # Get the reference type to determine expansion approach
        ref = g_el.get('ref', '')
        
        if ref == 'char:abque':
            # This is the special 'que' abbreviation
            # Create specialized structure following TEI conventions
            if not parent.tag.endswith('am'):
                # If not already in <am>, create one
                am = self._create_element('am')
                
                # Find position of g_el in parent
                g_index = -1
                for i, child in enumerate(parent):
                    if child == g_el:
                        g_index = i
                        break
                
                if g_index == -1:
                    self.logger.error("Cannot find g element within parent")
                    return False
                
                # Remove g from parent and add to am
                parent.remove(g_el)
                am.append(g_el)
                
                # Create choice structure
                choice = self._create_element('choice')
                abbr = self._create_element('abbr')
                abbr.append(am)
                
                # Create expan with ex
                expan = self._create_element('expan')
                am_copy = self._create_element('am')
                am_copy.append(etree.fromstring(f'<g xmlns="{self.tei_ns}" ref="char:abque"/>'))
                ex = self._create_element('ex')
                ex.text = expansion
                
                expan.append(am_copy)
                expan.append(ex)
                
                # Build the complete structure
                choice.append(abbr)
                choice.append(expan)
                
                # Insert choice where g was
                parent.insert(g_index, choice)
                return True
                
            else:
                # Already inside <am>, create standard pattern
                am_parent = parent.getparent()
                if am_parent is None:
                    self.logger.error("AM element has no parent")
                    return False
                
                if am_parent.tag.endswith('abbr'):
                    # Good structure - create matching expan
                    abbr_parent = am_parent.getparent()
                    if abbr_parent is None:
                        self.logger.error("ABBR element has no parent")
                        return False
                        
                    if abbr_parent.tag.endswith('choice'):
                        # Already in choice - add/update expan
                        for child in abbr_parent:
                            if child.tag.endswith('expan'):
                                # Update existing expan
                                child.clear()
                                am_copy = self._create_element('am')
                                am_copy.append(etree.fromstring(f'<g xmlns="{self.tei_ns}" ref="char:abque"/>'))
                                ex = self._create_element('ex')
                                ex.text = expansion
                                child.append(am_copy)
                                child.append(ex)
                                return True
                        
                        # No expan found, create new one
                        expan = self._create_element('expan')
                        am_copy = self._create_element('am')
                        am_copy.append(etree.fromstring(f'<g xmlns="{self.tei_ns}" ref="char:abque"/>'))
                        ex = self._create_element('ex')
                        ex.text = expansion
                        expan.append(am_copy)
                        expan.append(ex)
                        abbr_parent.append(expan)
                        return True
                    else:
                        # Need to create choice
                        choice = self._create_element('choice')
                        expan = self._create_element('expan')
                        am_copy = self._create_element('am')
                        am_copy.append(etree.fromstring(f'<g xmlns="{self.tei_ns}" ref="char:abque"/>'))
                        ex = self._create_element('ex')
                        ex.text = expansion
                        expan.append(am_copy)
                        expan.append(ex)
                        
                        # Find position of abbr in parent
                        abbr_index = -1
                        for i, child in enumerate(abbr_parent):
                            if child == am_parent:
                                abbr_index = i
                                break
                                
                        if abbr_index == -1:
                            self.logger.error("Cannot find abbr element within parent")
                            return False
                            
                        # Remove abbr and add to choice with expan
                        abbr_parent.remove(am_parent)
                        choice.append(am_parent)
                        choice.append(expan)
                        
                        # Insert choice where abbr was
                        abbr_parent.insert(abbr_index, choice)
                        return True
                else:
                    # Unusual structure - add simple expansion
                    expan = self._create_expansion_element(expansion, g_id)
                    am_parent.append(expan)
                    return True
        
        elif ref == 'char:cmbAbbrStroke':
            # Combining macron
            # Create a simplified expansion that doesn't try to reproduce the complex TEI structure
            expan = self._create_expansion_element(expansion, g_id)
            
            # Find position of g in parent
            g_index = -1
            for i, child in enumerate(parent):
                if child == g_el:
                    g_index = i
                    break
                    
            if g_index == -1:
                self.logger.error("Cannot find g element within parent")
                return False
                
            # Insert expan after g
            parent.insert(g_index + 1, expan)
            return True
            
        else:
            # Unknown g type - use simple expansion
            expan = self._create_expansion_element(expansion, g_id)
            
            # Find position of g in parent
            g_index = -1
            for i, child in enumerate(parent):
                if child == g_el:
                    g_index = i
                    break
                    
            if g_index == -1:
                self.logger.error("Cannot find g element within parent")
                return False
                
            # Insert expan after g
            parent.insert(g_index + 1, expan)
            return True
    
    def _add_expansion_to_am(self, am_el: etree.Element, parent: etree.Element, 
                            expansion: str, am_id: Optional[str]) -> bool:
        """Add expansion to an <am> abbreviation marker element."""
        
        # Check if parent is <abbr>
        if parent.tag.endswith('abbr'):
            abbr_parent = parent.getparent()
            if abbr_parent is None:
                self.logger.error("ABBR parent is None")
                return False
                
            if abbr_parent.tag.endswith('choice'):
                # Already in choice structure, add/update expan
                for child in abbr_parent:
                    if child.tag.endswith('expan'):
                        # Update existing expan
                        child.clear()
                        am_copy = etree.fromstring(etree.tostring(am_el))
                        ex = self._create_element('ex')
                        ex.text = expansion
                        child.append(am_copy)
                        child.append(ex)
                        return True
                
                # No expan found, create new one
                expan = self._create_element('expan')
                am_copy = etree.fromstring(etree.tostring(am_el))
                ex = self._create_element('ex')
                ex.text = expansion
                expan.append(am_copy)
                expan.append(ex)
                abbr_parent.append(expan)
                return True
            else:
                # Need to create choice structure
                choice = self._create_element('choice')
                expan = self._create_element('expan')
                am_copy = etree.fromstring(etree.tostring(am_el))
                ex = self._create_element('ex')
                ex.text = expansion
                expan.append(am_copy)
                expan.append(ex)
                
                # Find position of abbr in parent
                abbr_index = -1
                for i, child in enumerate(abbr_parent):
                    if child == parent:
                        abbr_index = i
                        break
                        
                if abbr_index == -1:
                    self.logger.error("Cannot find abbr element within parent")
                    return False
                    
                # Remove abbr and add to choice with expan
                abbr_parent.remove(parent)
                choice.append(parent)
                choice.append(expan)
                
                # Insert choice where abbr was
                abbr_parent.insert(abbr_index, choice)
                return True
        else:
            # Unusual structure - add simple expansion
            expan = self._create_expansion_element(expansion, am_id)
            
            # Find position of am in parent
            am_index = -1
            for i, child in enumerate(parent):
                if child == am_el:
                    am_index = i
                    break
                    
            if am_index == -1:
                self.logger.error("Cannot find am element within parent")
                return False
                
            # Insert expan after am
            parent.insert(am_index + 1, expan)
            return True
    
    def _create_expansion_element(self, expansion: str, abbr_id: Optional[str]) -> etree.Element:
        """
        Create a simple <expan> element.
        
        Args:
            expansion: The expansion text
            abbr_id: Optional ID of the corresponding abbreviation
            
        Returns:
            New <expan> element
        """
        expan = self._create_element('expan')
        expan.text = expansion
        
        # Add reference to abbr if it has an ID
        if abbr_id and self.add_xml_ids:
            expan.set('corresp', f"#{abbr_id}")
        
        # Optionally add an ID to the expan element
        if self.add_xml_ids:
            import uuid
            expan_id = f"expan_{uuid.uuid4().hex[:8]}"
            expan.set('{http://www.w3.org/XML/1998/namespace}id', expan_id)
        
        return expan
    
    def _create_element(self, tag_name: str) -> etree.Element:
        """
        Create a new element with the TEI namespace.
        
        Args:
            tag_name: Name of the tag without namespace
            
        Returns:
            New element
        """
        return etree.Element(f"{{{self.tei_ns}}}{tag_name}")
    
    def save_document(self, tree: etree.ElementTree, output_path: Union[str, Path]) -> bool:
        """
        Save the modified TEI document.
        
        Args:
            tree: XML tree object
            output_path: Path to save document to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(str(output_path))
            os.makedirs(output_dir, exist_ok=True)
            
            # Write the tree with proper formatting
            tree.write(
                str(output_path), 
                pretty_print=True, 
                encoding='utf-8', 
                xml_declaration=True
            )
            
            self.logger.info(f"Saved document to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving document to {output_path}: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary of statistics
        """
        return self.stats
    
    def is_valid_tei(self, file_path: Union[str, Path]) -> bool:
        """
        Check if a file is a valid TEI XML document.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if it's a valid TEI document
        """
        try:
            tree = etree.parse(str(file_path))
            root = tree.getroot()
            # Check if it has the TEI namespace
            root_tag = root.tag
            return '{http://www.tei-c.org/ns/1.0}' in root_tag
        except Exception as e:
            self.logger.error(f"File is not valid TEI: {e}")
            return False