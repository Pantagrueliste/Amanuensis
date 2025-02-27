"""
TEIProcessor: Core module for processing TEI XML documents
Extracts abbreviations and their context for dataset creation.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass

# Try to import lxml, otherwise fallback to ElementTree
try:
    from lxml import etree
    LXML_AVAILABLE = True
except ImportError:
    import xml.etree.ElementTree as etree
    LXML_AVAILABLE = False
    logging.warning("lxml not available, falling back to ElementTree. Some XPath features may not work correctly.")


@dataclass
class AbbreviationInfo:
    """Data class for storing information about an abbreviation."""
    abbr_text: str
    abbr_id: Optional[str]
    abbr_element: etree.Element
    parent_element: etree.Element
    context_before: str
    context_after: str
    file_path: str
    line_number: int
    xpath: str
    metadata: Dict[str, Any]


class TEIProcessor:
    """
    Processor for TEI XML documents that extracts abbreviations and their context.
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
        self.namespaces = {
            'tei': config.get('xml_processing', 'tei_namespace', 'http://www.tei-c.org/ns/1.0'),
        }
        
        # XPath queries for common elements
        self.abbr_xpath = config.get('xml_processing', 'abbr_xpath', '//tei:abbr')
        self.expan_xpath = config.get('xml_processing', 'expan_xpath', '//tei:expan')
        self.choice_xpath = config.get('xml_processing', 'choice_xpath', '//tei:choice')
        
        # Context extraction settings
        self.context_window = config.get('xml_processing', 'context_window_size', 50)
        self.include_ancestor_context = config.get('xml_processing', 'include_ancestor_context', True)
        
        # Output structure settings
        self.use_choice_tags = config.get('xml_processing', 'use_choice_tags', False)
        self.add_xml_ids = config.get('xml_processing', 'add_xml_ids', True)
        
        # Initialize statistics
        self.stats = {
            'documents_processed': 0,
            'abbreviations_found': 0,
            'already_expanded': 0,
            'malformed_abbr': 0,
        }

    def parse_document(self, file_path: Union[str, Path]) -> Tuple[List[AbbreviationInfo], Optional[etree.ElementTree]]:
        """
        Parse a TEI XML document and extract abbreviation information.
        
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
            
            # Parse the XML document
            parser = etree.XMLParser(remove_blank_text=True) if LXML_AVAILABLE else None
            tree = etree.parse(str(file_path), parser=parser)
            root = tree.getroot()
            
            # Extract metadata from TEI header
            metadata = self._extract_metadata(root)
            
            # Find all abbreviation elements
            abbr_elements = root.xpath(self.abbr_xpath, namespaces=self.namespaces)
            
            # Check if we found any
            if not abbr_elements:
                self.logger.info(f"No abbreviation elements found in {file_path}")
                return [], tree
                
            self.logger.info(f"Found {len(abbr_elements)} abbreviation elements in {file_path}")
            self.stats['abbreviations_found'] += len(abbr_elements)
            self.stats['documents_processed'] += 1
            
            # Process each abbreviation
            abbreviations = []
            for abbr in abbr_elements:
                try:
                    # Extract and process abbreviation
                    abbr_info = self._process_abbreviation(abbr, file_path, metadata)
                    if abbr_info:
                        abbreviations.append(abbr_info)
                except Exception as e:
                    self.logger.error(f"Error processing abbreviation in {file_path}: {e}")
                    self.stats['malformed_abbr'] += 1
            
            return abbreviations, tree
            
        except Exception as e:
            self.logger.error(f"Error parsing TEI document {file_path}: {e}")
            return [], None

    def _extract_metadata(self, root: etree.Element) -> Dict[str, Any]:
        """
        Extract metadata from TEI header.
        
        Args:
            root: Root element of TEI document
            
        Returns:
            Dictionary of metadata
        """
        metadata = {
            'title': '',
            'author': '',
            'date': '',
            'language': '',
            'source': '',
            'genre': '',
        }
        
        try:
            # Extract title
            title_elements = root.xpath('//tei:titleStmt/tei:title', namespaces=self.namespaces)
            if title_elements:
                metadata['title'] = self._get_element_text(title_elements[0])
            
            # Extract author
            author_elements = root.xpath('//tei:titleStmt/tei:author', namespaces=self.namespaces)
            if author_elements:
                metadata['author'] = self._get_element_text(author_elements[0])
            
            # Extract date
            date_elements = root.xpath('//tei:publicationStmt/tei:date', namespaces=self.namespaces)
            if not date_elements:
                # Try alternate location
                date_elements = root.xpath('//tei:sourceDesc//tei:date', namespaces=self.namespaces)
            if date_elements:
                metadata['date'] = date_elements[0].get('when', self._get_element_text(date_elements[0]))
            
            # Extract language
            language_elements = root.xpath('//tei:profileDesc/tei:langUsage/tei:language', 
                                          namespaces=self.namespaces)
            if language_elements:
                metadata['language'] = language_elements[0].get('ident', '')
            
            # Extract source
            source_elements = root.xpath('//tei:sourceDesc/tei:bibl', namespaces=self.namespaces)
            if source_elements:
                metadata['source'] = self._get_element_text(source_elements[0])
                
            # Try to extract genre/text type
            text_class_elements = root.xpath('//tei:profileDesc/tei:textClass//tei:term', 
                                            namespaces=self.namespaces)
            if text_class_elements:
                genres = [self._get_element_text(term) for term in text_class_elements[:3]]
                metadata['genre'] = ', '.join(filter(None, genres))
                
        except Exception as e:
            self.logger.error(f"Error extracting metadata: {e}")
        
        return metadata

    def _get_element_text(self, element: etree.Element) -> str:
        """
        Get the text content of an element, handling possible None values.
        
        Args:
            element: XML element
            
        Returns:
            Text content of the element
        """
        if element is None:
            return ''
        
        # Get text directly
        text = element.text or ''
        
        # If there are child elements, get their text too
        for child in element:
            # Add text before the child's tail
            if child.text:
                text += ' ' + child.text
            # Add the child's tail
            if child.tail:
                text += ' ' + child.tail
                
        return text.strip()

    def _process_abbreviation(self,
                              abbr_element: etree.Element,
                              file_path: Union[str, Path],
                              metadata: Dict[str, Any]) -> Optional[AbbreviationInfo]:
        """
        Process an abbreviation element and extract relevant information.
        
        Args:
            abbr_element: XML element representing the abbreviation
            file_path: Path to the source document
            metadata: Document metadata
            
        Returns:
            AbbreviationInfo object or None if processing failed
        """
        # Extract abbr text content
        abbr_text = self._get_element_text(abbr_element)
        if not abbr_text or not abbr_text.strip():
            self.logger.warning(f"Empty abbreviation found in {file_path}")
            return None
            
        abbr_text = abbr_text.strip()
        
        # Get element ID if present
        abbr_id = abbr_element.get('{http://www.w3.org/XML/1998/namespace}id') or abbr_element.get('id')
        
        # Check if this is already part of a choice element (already expanded)
        parent = abbr_element.getparent()
        already_expanded = False
        
        if parent is not None and parent.tag.endswith('choice'):
            # Check if there's an expansion sibling
            for sibling in parent:
                if sibling != abbr_element and sibling.tag.endswith('expan'):
                    already_expanded = True
                    self.stats['already_expanded'] += 1
                    break
        else:
            # Check for sibling expan element
            next_sibling = abbr_element.getnext()
            if next_sibling is not None and next_sibling.tag.endswith('expan'):
                already_expanded = True
                self.stats['already_expanded'] += 1
        
        # Skip if already expanded and configured to do so
        if already_expanded and self.config.get('settings', 'skip_expanded', False):
            return None
        
        # Get line number (approximation)
        line_number = 0
        for i, el in enumerate(parent.xpath('.//*') if parent is not None else []):
            if el == abbr_element:
                line_number = i
                break
        
        # Get XPath
        xpath = self._get_xpath(abbr_element)
        
        # Extract context
        context_before, context_after = self._extract_context(abbr_element, abbr_text)
        
        return AbbreviationInfo(
            abbr_text=abbr_text,
            abbr_id=abbr_id,
            abbr_element=abbr_element,
            parent_element=parent,
            context_before=context_before,
            context_after=context_after,
            file_path=str(file_path),
            line_number=line_number,
            xpath=xpath,
            metadata=metadata
        )

    def _extract_context(self, abbr_element: etree.Element, abbr_text: str) -> Tuple[str, str]:
        """
        Extract text context before and after an abbreviation.
        
        Args:
            abbr_element: The abbreviation XML element
            abbr_text: The text content of the abbreviation
            
        Returns:
            Tuple of (text_before, text_after)
        """
        parent = abbr_element.getparent()
        if parent is None:
            return '', ''
        
        try:
            # Determine the context scope based on configuration
            context_element = parent
            if self.include_ancestor_context and not self._is_block_element(parent):
                # Try to find a higher-level block element
                ancestor = parent
                for _ in range(3):  # Look up to 3 levels
                    ancestor = ancestor.getparent()
                    if ancestor is None or self._is_block_element(ancestor):
                        context_element = ancestor or context_element
                        break
            
            if context_element is None:
                return '', ''
                
            # Extract all text
            full_text = self._get_element_text(context_element)
            
            # Find position of abbreviation in full text
            abbr_pos = full_text.find(abbr_text)
            
            if abbr_pos >= 0:
                context_before = full_text[:abbr_pos].strip()[-self.context_window:]
                context_after = full_text[abbr_pos + len(abbr_text):].strip()[:self.context_window]
            else:
                # Fallback if exact match not found
                self.logger.warning(f"Could not locate abbreviation '{abbr_text}' in parent text")
                context_before = ''
                context_after = ''
                
                # Find preceding siblings
                current = abbr_element
                for _ in range(3):
                    prev_sibling = current.getprevious()
                    if prev_sibling is None:
                        break
                    current = prev_sibling
                    sibling_text = self._get_element_text(prev_sibling)
                    context_before = sibling_text + ' ' + context_before
                    context_before = context_before.strip()[-self.context_window:]
                
                # Find following siblings
                current = abbr_element
                for _ in range(3):
                    next_sibling = current.getnext()
                    if next_sibling is None:
                        break
                    current = next_sibling
                    sibling_text = self._get_element_text(next_sibling)
                    context_after = context_after + ' ' + sibling_text
                    context_after = context_after.strip()[:self.context_window]
            
            return context_before, context_after
            
        except Exception as e:
            self.logger.error(f"Error extracting context: {e}")
            return '', ''

    def _is_block_element(self, element: Optional[etree.Element]) -> bool:
        """
        Determine if an element is a block-level element.
        
        Args:
            element: XML element to check
            
        Returns:
            True if it's a block element, False otherwise
        """
        if element is None:
            return False
            
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        # Common TEI block elements
        block_elements = {
            'div', 'p', 'lg', 'l', 'ab', 'head', 'list', 'item', 'table', 'row',
            'cell', 'quote', 'figure', 'note', 'milestone', 'pb', 'cb', 'lb'
        }
        return tag in block_elements

    def add_expansion(self, abbr_info: AbbreviationInfo, expansion: str) -> bool:
        """
        Add an expansion element next to an abbreviation in the TEI document.
        
        Args:
            abbr_info: Information about the abbreviation
            expansion: Expansion text to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            abbr_element = abbr_info.abbr_element
            parent = abbr_info.parent_element
            
            if parent is None:
                self.logger.error("Cannot add expansion: parent element is None")
                return False
            
            # Check if parent is already a choice element
            if parent.tag.endswith('choice'):
                # Look for existing expan element
                for child in parent:
                    if child.tag.endswith('expan'):
                        child.text = expansion
                        return True
                # No existing expan, create a new one
                expan = self._create_expan_element(expansion, abbr_info.abbr_id)
                parent.append(expan)
                return True
            
            elif self.use_choice_tags:
                # Create a new choice element and move the abbr into it
                choice = self._create_element('choice')
                
                abbr_index = -1
                for i, child in enumerate(parent):
                    if child == abbr_element:
                        abbr_index = i
                        break
                if abbr_index == -1:
                    self.logger.error("Cannot add expansion: abbr element not found in parent")
                    return False
                    
                expan = self._create_expan_element(expansion, abbr_info.abbr_id)
                
                # Remove abbr from its parent
                parent.remove(abbr_element)
                
                # Add abbr + expan to choice
                choice.append(abbr_element)
                choice.append(expan)
                
                # Reinsert choice into parent at the same position
                parent.insert(abbr_index, choice)
                return True
            
            else:
                # Create expan element and insert after abbr
                expan = self._create_expan_element(expansion, abbr_info.abbr_id)
                abbr_index = -1
                for i, child in enumerate(parent):
                    if child == abbr_element:
                        abbr_index = i
                        break
                if abbr_index == -1:
                    self.logger.error("Cannot add expansion: abbr element not found in parent")
                    return False
                parent.insert(abbr_index + 1, expan)
                return True
                
        except Exception as e:
            self.logger.error(f"Error adding expansion to document: {e}")
            return False

    def _create_expan_element(self, expansion: str, abbr_id: Optional[str]) -> etree.Element:
        """
        Create an expansion element.
        
        Args:
            expansion: Expansion text
            abbr_id: ID of the abbreviation element
            
        Returns:
            New expan element
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
        tei_ns = self.namespaces['tei']
        if LXML_AVAILABLE:
            return etree.Element(f"{{{tei_ns}}}{tag_name}")
        else:
            return etree.Element(f"{tag_name}", nsmap={'tei': tei_ns})

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
            output_dir = os.path.dirname(str(output_path))
            os.makedirs(output_dir, exist_ok=True)
            
            if LXML_AVAILABLE:
                tree.write(
                    str(output_path), 
                    pretty_print=True, 
                    encoding='utf-8', 
                    xml_declaration=True
                )
            else:
                tree.write(
                    str(output_path),
                    encoding='utf-8'
                )
            self.logger.info(f"Saved document to {output_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error saving document to {output_path}: {e}")
            return False

    def _get_xpath(self, element: etree.Element) -> str:
        """
        Generate an XPath expression to locate an element.
        
        Args:
            element: XML element to generate XPath for
            
        Returns:
            XPath expression as string
        """
        if element is None:
            return ""
        
        if LXML_AVAILABLE and hasattr(element, 'getroottree'):
            try:
                tree = element.getroottree()
                if tree is not None:
                    return tree.getpath(element)
            except Exception:
                pass
        
        path = []
        parent = element.getparent()
        while element is not None:
            tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            if parent is None:
                # Root element
                path.insert(0, f'/{tag}')
                break
            
            # Position among siblings of same tag
            index = 1
            for sibling in parent:
                if sibling == element:
                    break
                if sibling.tag == element.tag:
                    index += 1
            
            path.insert(0, f'{tag}[{index}]')
            element = parent
            parent = element.getparent()
        return '/'.join(path)

    def get_statistics(self) -> Dict[str, int]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary of statistics
        """
        return self.stats

    def validate_document(self, file_path: Union[str, Path]) -> bool:
        """
        Validate a TEI XML document against the TEI schema.
        
        Args:
            file_path: Path to the document to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not LXML_AVAILABLE:
            self.logger.warning("lxml not available, document validation not supported")
            return True
        
        try:
            from lxml import isoschematron
            tei_schema_url = "https://tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng"
            
            parser = etree.XMLParser(remove_blank_text=True)
            doc = etree.parse(str(file_path), parser=parser)
            relaxng = etree.RelaxNG(etree.parse(tei_schema_url))
            is_valid = relaxng.validate(doc)
            
            if not is_valid:
                self.logger.warning(f"Document {file_path} is not valid TEI:")
                for error in relaxng.error_log:
                    self.logger.warning(f"  - {error}")
            return is_valid
        
        except Exception as e:
            self.logger.error(f"Error validating document {file_path}: {e}")
            return False

    def find_document_for_id(self, document_id: str, directory: Union[str, Path]) -> Optional[str]:
        """
        Find a document containing a specific ID.
        
        Args:
            document_id: ID to search for
            directory: Directory to search in
            
        Returns:
            Path to the document if found, None otherwise
        """
        try:
            directory = Path(directory)
            for file_path in directory.glob('**/*.xml'):
                try:
                    tree = etree.parse(str(file_path))
                    root = tree.getroot()
                    id_elements = root.xpath(
                        f'//*[@xml:id="{document_id}" or @id="{document_id}"]',
                        namespaces=self.namespaces
                    )
                    if id_elements:
                        return str(file_path)
                except Exception as e:
                    self.logger.error(f"Error searching in {file_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error finding document for ID {document_id}: {e}")
            return None

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
        except Exception:
            return False