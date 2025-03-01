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
    context_before: str = ""     # Text context before the abbreviation
    context_after: str = ""      # Text context after the abbreviation
    

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
        
        # Context extraction settings
        self.context_words_before = config.get('xml_processing', 'context_words_before', 5)
        self.context_words_after = config.get('xml_processing', 'context_words_after', 5)
        
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
            
    def _extract_word_context(self, element: etree.Element) -> Tuple[str, str]:
        """
        Extract word context before and after an abbreviation element.
        
        Args:
            element: The abbreviation element
            
        Returns:
            Tuple containing:
            - Text context before the abbreviation (number of words defined in config)
            - Text context after the abbreviation (number of words defined in config)
        """
        parent = element.getparent()
        if parent is None:
            return "", ""
            
        # Get the full text of the parent element
        parent_text = self._get_element_text_content(parent)
        
        # Get the text of the abbreviation element
        abbr_text = self._get_element_text_content(element)
        
        # Try to find the position of the abbreviation in the parent text
        try:
            # Use a more complex approach to handle cases where the element's text appears multiple times
            # or where there's complex nesting
            
            # Get the entire subtree as XML string
            parent_xml = etree.tostring(parent, encoding='unicode')
            elem_xml = etree.tostring(element, encoding='unicode')
            
            # Find position of element XML within parent XML
            pos = parent_xml.find(elem_xml)
            if pos < 0:
                # If can't find exact XML, fallback to simple text search
                pos = parent_text.find(abbr_text)
                
            if pos < 0:
                # If still can't find, try to get an approximation
                for ancestor in element.iterancestors():
                    ancestor_text = self._get_element_text_content(ancestor)
                    
                    # If we found a larger context with the text
                    if abbr_text in ancestor_text:
                        parent_text = ancestor_text
                        pos = parent_text.find(abbr_text)
                        break
                
                # If still can't find, return empty context
                if pos < 0:
                    return "", ""
            
            # Extract context before the abbreviation
            before_text = parent_text[:pos].strip()
            words_before = before_text.split()
            context_before = " ".join(words_before[-self.context_words_before:]) if words_before else ""
            
            # Extract context after the abbreviation
            after_pos = pos + len(abbr_text)
            after_text = parent_text[after_pos:].strip()
            words_after = after_text.split()
            context_after = " ".join(words_after[:self.context_words_after]) if words_after else ""
            
            return context_before, context_after
            
        except Exception as e:
            self.logger.error(f"Error extracting context: {e}")
            return "", ""
    
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
        
        # Extract context around the abbreviation
        context_before, context_after = self._extract_word_context(abbr_el)
            
        return AbbreviationInfo(
            abbr_element=abbr_el,
            abbr_id=abbr_id,
            parent_element=parent,
            xpath=xpath,
            file_path=str(file_path),
            metadata=metadata,
            normalized_form=normalized_form,
            context_before=context_before,
            context_after=context_after
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
        
        # Extract context around the abbreviation
        context_before, context_after = self._extract_word_context(g_el)
            
        return AbbreviationInfo(
            abbr_element=g_el,
            abbr_id=g_id,
            parent_element=parent,
            xpath=xpath,
            file_path=str(file_path),
            metadata=metadata,
            normalized_form=normalized_form,
            context_before=context_before,
            context_after=context_after
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
        
        # Extract context around the abbreviation
        context_before, context_after = self._extract_word_context(am_el)
            
        return AbbreviationInfo(
            abbr_element=am_el,
            abbr_id=am_id,
            parent_element=parent,
            xpath=xpath,
            file_path=str(file_path),
            metadata=metadata,
            normalized_form=normalized_form,
            context_before=context_before,
            context_after=context_after
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
    
    def _create_element(self, tag_name: str) -> etree.Element:
        """
        Create a new element with the TEI namespace.
        
        Args:
            tag_name: Name of the tag without namespace
            
        Returns:
            New element
        """
        return etree.Element(f"{{{self.tei_ns}}}{tag_name}")
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary of statistics
        """
        return self.stats