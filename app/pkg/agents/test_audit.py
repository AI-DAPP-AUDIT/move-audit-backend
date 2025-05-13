import unittest
from app.pkg.agents.audit import extract_markdown_content

class TestExtractMarkdownContent(unittest.TestCase):
    def test_no_markdown_block(self):
        """test markdown content is block"""
        input_text = "Just some regular text without markdown"
        expected = "Just some regular text without markdown"
        result = extract_markdown_content(input_text)
        self.assertEqual(result, expected)


    def test_markdown_with_code_blocks(self):
        """test code markdown"""
        input_text = """Before
        ```markdown
        # Title
        ```python
        def hello():
            print("world")
        ```
        ## Subtitle
        ```
        After"""
        # expected = """# Title
        # ```python
        # def hello():
        #     print("world")
        # ```
        # ## Subtitle"""
        result = extract_markdown_content(input_text)
        # self.assertEqual(result, expected)
        print(result)

if __name__ == '__main__':
    unittest.main()