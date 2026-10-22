import importlib.util,unittest
from pathlib import Path
try:
    import pdfplumber,pypdfium2
    spec=importlib.util.spec_from_file_location('reader',Path(__file__).parents[1]/'scripts/read_pdf.py')
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
except ImportError:reader=None
@unittest.skipIf(reader is None,'Run with the project pdf-venv to test PDF processing')
class PdfEvidenceTests(unittest.TestCase):
    def test_ocr_preserves_row_column_alignment_and_all_values(self):
        blocks=[{'text':'Alım','x':.3,'y':.1,'height':.02},{'text':'Satım','x':.6,'y':.1,'height':.02},{'text':'1.155.000','x':.3,'y':.2,'height':.02},{'text':'0','x':.6,'y':.2,'height':.02}]
        lines=reader.ocr_text(blocks).splitlines();self.assertEqual(len(lines),2)
        self.assertEqual(lines[0].index('Alım'),lines[1].index('1.155.000'));self.assertEqual(lines[0].index('Satım'),lines[1].index('0',lines[0].index('Satım')))
    def test_confidence_and_coordinates_never_become_factual_source_numbers(self):
        text=reader.ocr_text([{'text':'85,7056 TL','confidence':.5,'x':.125,'y':.112,'height':.03}]);self.assertEqual(text.strip(),'85,7056 TL');self.assertNotIn('0.5',text)
    def test_untrusted_page_boxes_are_bounded_before_render_allocation(self):
        self.assertLessEqual(reader.render_scale(1_000_000,1_000_000),.01)
        self.assertLessEqual(reader.render_scale(500,700),2)
        for width,height in [(0,10),(-1,10),(float('inf'),10),(10,float('nan'))]:
            with self.assertRaises(ValueError):reader.render_scale(width,height)
        with self.assertRaises(ValueError):reader.render_scale(100,100,0)
