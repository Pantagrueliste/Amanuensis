"""
Comprehensive tests for the TEI processor module.
"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from modules.tei.processor import TEIProcessor, AbbreviationInfo

# Try to import lxml, otherwise fallback to ElementTree
try:
    from lxml import etree
    LXML_AVAILABLE = True
except ImportError:
    import xml.etree.ElementTree as etree
    LXML_AVAILABLE = False


class TestTEIProcessor:
    """Test suite for the TEI Processor"""

    def test_init(self, mock_config):
        """Test initializing the TEI processor."""
        processor = TEIProcessor(mock_config)
        
        # Check if the processor was initialized correctly
        assert processor.namespaces['tei'] == "http://www.tei-c.org/ns/1.0"
        assert processor.abbr_xpath == "//tei:abbr"
        assert processor.expan_xpath == "//tei:expan"
        assert processor.choice_xpath == "//tei:choice"
        assert processor.context_window == 50
        assert processor.include_ancestor_context is True
        assert processor.use_choice_tags is False
        assert processor.add_xml_ids is True
        
        # Check if statistics are initialized
        assert processor.stats['documents_processed'] == 0
        assert processor.stats['abbreviations_found'] == 0
        assert processor.stats['already_expanded'] == 0
        assert processor.stats['malformed_abbr'] == 0

    def test_parse_document(self, mock_config, sample_xml_path):
        """Test parsing a TEI document."""
        processor = TEIProcessor(mock_config)
        abbreviations, tree = processor.parse_document(sample_xml_path)
        
        # Check if the document was parsed correctly
        assert tree is not None
        assert len(abbreviations) > 0
        
        # Check if the stats were updated
        assert processor.stats['documents_processed'] == 1
        assert processor.stats['abbreviations_found'] > 0

    def test_parse_document_nonexistent(self, mock_config):
        """Test parsing a nonexistent document."""
        processor = TEIProcessor(mock_config)
        abbreviations, tree = processor.parse_document("/nonexistent/file.xml")
        
        # Check if the function handles errors correctly
        assert tree is None
        assert len(abbreviations) == 0

    def test_extract_metadata(self, mock_config, sample_xml_path):
        """Test extracting metadata from a TEI document."""
        processor = TEIProcessor(mock_config)
        tree = etree.parse(sample_xml_path)
        root = tree.getroot()
        
        metadata = processor._extract_metadata(root)
        
        # Check if metadata was extracted correctly
        assert metadata['title'] == "Sample Early Modern Text with Abbreviations"
        assert metadata['author'] == "Anonymous"
        assert metadata['date'] == "1650"
        assert metadata['language'] == "eng"
        assert "Original Source Title" in metadata['source']
        assert "Letter" in metadata['genre']

    def test_get_element_text(self, mock_config):
        """Test getting text content from an element."""
        processor = TEIProcessor(mock_config)
        
        # Test with None element
        assert processor._get_element_text(None) == ''
        
        # Test with simple element
        element = etree.Element("test")
        element.text = "Test text"
        assert processor._get_element_text(element) == "Test text"
        
        # Test with nested elements
        parent = etree.Element("parent")
        parent.text = "Parent text "
        child = etree.SubElement(parent, "child")
        child.text = "Child text"
        child.tail = " after child"
        assert processor._get_element_text(parent) == "Parent text Child text after child"

    def test_process_abbreviation(self, mock_config, sample_xml_path):
        """Test processing an abbreviation."""
        processor = TEIProcessor(mock_config)
        tree = etree.parse(sample_xml_path)
        root = tree.getroot()
        
        # Find the first abbreviation
        abbr_elements = root.xpath("//tei:abbr", namespaces=processor.namespaces)
        assert len(abbr_elements) > 0
        
        metadata = processor._extract_metadata(root)
        abbr_info = processor._process_abbreviation(abbr_elements[0], sample_xml_path, metadata)
        
        # Check if the abbreviation was processed correctly
        assert abbr_info is not None
        assert abbr_info.abbr_text == "motiõ"
        assert abbr_info.file_path == sample_xml_path
        assert len(abbr_info.context_before) > 0
        assert len(abbr_info.context_after) > 0

    def test_extract_context(self, mock_config, sample_xml_path):
        """Test extracting context around an abbreviation."""
        processor = TEIProcessor(mock_config)
        tree = etree.parse(sample_xml_path)
        root = tree.getroot()
        
        # Find the first abbreviation
        abbr_elements = root.xpath("//tei:abbr", namespaces=processor.namespaces)
        assert len(abbr_elements) > 0
        
        abbr_text = processor._get_element_text(abbr_elements[0])
        context_before, context_after = processor._extract_context(abbr_elements[0], abbr_text)
        
        # Check if context was extracted correctly
        assert len(context_before) > 0
        assert len(context_after) > 0
        assert "In these latter days, we have observed the" in context_before
        assert "of celestial" in context_after

    def test_is_block_element(self, mock_config):
        """Test identifying block elements."""
        processor = TEIProcessor(mock_config)
        
        # Test with None element
        assert processor._is_block_element(None) is False
        
        # Test with non-block element
        element = etree.Element("span")
        assert processor._is_block_element(element) is False
        
        # Test with block element
        element = etree.Element("div")
        assert processor._is_block_element(element) is True
        
        # Test with namespaced element
        element = etree.Element("{http://www.tei-c.org/ns/1.0}p")
        assert processor._is_block_element(element) is True

    @pytest.mark.parametrize(
        "parent_tag,use_choice,expected_success",
        [
            ("div", False, True),       # Regular parent, no choice
            ("div", True, True),        # Regular parent, use choice
            ("choice", False, True),    # Already a choice element
        ]
    )
    def test_add_expansion(self, mock_config, parent_tag, use_choice, expected_success):
        """Test adding expansion elements with different configurations."""
        # Update the config to use choice tags or not
        mock_config.settings['xml_processing']['use_choice_tags'] = use_choice
        processor = TEIProcessor(mock_config)
        
        # Create test elements
        abbr = etree.Element("abbr")
        abbr.text = "co$cerning"
        abbr_id = "abbr_123"
        abbr.set("{http://www.w3.org/XML/1998/namespace}id", abbr_id)
        
        parent = etree.Element(parent_tag)
        parent.append(abbr)
        
        # Create abbreviation info
        abbr_info = AbbreviationInfo(
            abbr_text="co$cerning",
            abbr_id=abbr_id,
            abbr_element=abbr,
            parent_element=parent,
            context_before="before",
            context_after="after",
            file_path="/test/file.xml",
            line_number=1,
            xpath="/TEI/text/body/div/p/abbr",
            metadata={}
        )
        
        # Add expansion
        result = processor.add_expansion(abbr_info, "concerning")
        
        # Check if expansion was added correctly
        assert result == expected_success
        
        if parent_tag == "choice":
            # Find expan element
            expan = None
            for child in parent:
                if child.tag == "expan" or child.tag.endswith("}expan"):
                    expan = child
                    break
            assert expan is not None
            assert expan.text == "concerning"
            
        elif use_choice:
            # Find the choice element
            choice = None
            for child in parent:
                if child.tag == "choice" or child.tag.endswith("}choice"):
                    choice = child
                    break
            assert choice is not None
            
            # Find abbr and expan within choice
            abbr_in_choice = None
            expan_in_choice = None
            for child in choice:
                if child.tag == "abbr" or child.tag.endswith("}abbr"):
                    abbr_in_choice = child
                elif child.tag == "expan" or child.tag.endswith("}expan"):
                    expan_in_choice = child
            
            assert abbr_in_choice is not None
            assert expan_in_choice is not None
            assert expan_in_choice.text == "concerning"
            
        else:
            # Find expan sibling
            expan = None
            for child in parent:
                if child.tag == "expan" or child.tag.endswith("}expan"):
                    expan = child
                    break
            assert expan is not None
            assert expan.text == "concerning"

    def test_create_expan_element(self, mock_config):
        """Test creating expansion elements."""
        processor = TEIProcessor(mock_config)
        
        # Test without abbr_id
        expan = processor._create_expan_element("concerning", None)
        assert expan.text == "concerning"
        assert expan.get("corresp") is None
        assert expan.get("{http://www.w3.org/XML/1998/namespace}id") is not None
        
        # Test with abbr_id
        expan = processor._create_expan_element("concerning", "abbr_123")
        assert expan.text == "concerning"
        assert expan.get("corresp") == "#abbr_123"
        assert expan.get("{http://www.w3.org/XML/1998/namespace}id") is not None

    def test_create_element(self, mock_config):
        """Test creating elements with namespace."""
        processor = TEIProcessor(mock_config)
        
        element = processor._create_element("test")
        
        # Check if element was created with correct namespace
        if LXML_AVAILABLE:
            assert element.tag == "{http://www.tei-c.org/ns/1.0}test"
        else:
            assert element.tag == "test"

    def test_save_document(self, mock_config, sample_xml_path, temp_output_dir):
        """Test saving a modified document."""
        processor = TEIProcessor(mock_config)
        
        # Parse and modify a document
        abbreviations, tree = processor.parse_document(sample_xml_path)
        assert tree is not None
        
        # Add an expansion to the first abbreviation
        if abbreviations:
            processor.add_expansion(abbreviations[0], "motion")
        
        # Save the document
        output_path = os.path.join(temp_output_dir, "test_output.xml")
        result = processor.save_document(tree, output_path)
        
        # Check if document was saved correctly
        assert result is True
        assert os.path.exists(output_path)
        
        # Check if saved document is valid XML
        try:
            saved_tree = etree.parse(output_path)
            assert saved_tree is not None
        except Exception as e:
            pytest.fail(f"Failed to parse saved document: {e}")

    def test_get_xpath(self, mock_config, sample_xml_path):
        """Test generating XPath for elements."""
        processor = TEIProcessor(mock_config)
        
        # Parse a document
        tree = etree.parse(sample_xml_path)
        root = tree.getroot()
        
        # Find the first abbreviation
        abbr_elements = root.xpath("//tei:abbr", namespaces=processor.namespaces)
        assert len(abbr_elements) > 0
        
        # Generate XPath
        xpath = processor._get_xpath(abbr_elements[0])
        
        # Check if XPath was generated
        assert len(xpath) > 0
        assert "abbr" in xpath

    def test_get_statistics(self, mock_config, sample_xml_path):
        """Test getting processing statistics."""
        processor = TEIProcessor(mock_config)
        
        # Parse a document
        processor.parse_document(sample_xml_path)
        
        # Get statistics
        stats = processor.get_statistics()
        
        # Check if statistics were updated
        assert stats['documents_processed'] == 1
        assert stats['abbreviations_found'] > 0

    @pytest.mark.skipif(not LXML_AVAILABLE, reason="lxml not available")
    def test_is_valid_tei(self, mock_config, sample_xml_path):
        """Test checking if a file is valid TEI XML."""
        processor = TEIProcessor(mock_config)
        
        # Check valid TEI document
        assert processor.is_valid_tei(sample_xml_path) is True
        
        # Check invalid file
        with tempfile.NamedTemporaryFile(suffix=".xml") as tmp:
            tmp.write(b"<root>Not a TEI document</root>")
            tmp.flush()
            assert processor.is_valid_tei(tmp.name) is False

    def test_functional_workflow(self, mock_config, sample_xml_path, temp_output_dir):
        """Full functional test of the TEI processor workflow."""
        processor = TEIProcessor(mock_config)
        
        # Parse document
        abbreviations, tree = processor.parse_document(sample_xml_path)
        assert len(abbreviations) > 0
        assert tree is not None
        
        # Process each abbreviation
        expansions = {
            "motiõ": "motion",
            "co$cerning": "concerning",
            "lear$ed": "learned",
            "iudgme$t": "iudgment",
            "substa$tial": "substantial",
            "co$sider": "consider",
            "argume$ts": "arguments",
            "Natu$": "Nature",
            "demo$strated": "demonstrated",
            "mai$tained": "maintained",
            "natu$": "nature"
        }
        
        for abbr in abbreviations:
            if abbr.abbr_text in expansions:
                processor.add_expansion(abbr, expansions[abbr.abbr_text])
        
        # Save the modified document
        output_path = os.path.join(temp_output_dir, "functional_test_output.xml")
        result = processor.save_document(tree, output_path)
        assert result is True
        
        # Parse the saved document
        saved_tree = etree.parse(output_path)
        root = saved_tree.getroot()
        
        # Check if expansions were added
        expan_elements = root.xpath("//tei:expan", namespaces=processor.namespaces)
        assert len(expan_elements) > 0
        
        # Check if some expansions have the expected text
        expan_texts = [processor._get_element_text(expan) for expan in expan_elements]
        assert "motion" in expan_texts or "concerning" in expan_texts or "learned" in expan_texts

    def test_error_handling(self, mock_config):
        """Test error handling in TEI processor."""
        processor = TEIProcessor(mock_config)
        
        # Test with invalid file
        abbreviations, tree = processor.parse_document("/nonexistent/file.xml")
        assert len(abbreviations) == 0
        assert tree is None
        
        # Test with None parent element
        abbr = etree.Element("abbr")
        abbr.text = "test"
        abbr_info = AbbreviationInfo(
            abbr_text="test",
            abbr_id=None,
            abbr_element=abbr,
            parent_element=None,
            context_before="",
            context_after="",
            file_path="test.xml",
            line_number=1,
            xpath="",
            metadata={}
        )
        
        result = processor.add_expansion(abbr_info, "test_expansion")
        assert result is False