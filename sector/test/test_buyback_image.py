import importlib.util,json,os,pathlib,sys,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import read_buyback_image as reader
from PIL import Image,ImageDraw

class BuybackImageTests(unittest.TestCase):
    def test_dimension_budget_before_decode(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as d:
            p=pathlib.Path(d)/'huge.png';Image.new('1',(12001,100)).save(p)
            with self.assertRaisesRegex(ValueError,'dimensions'):reader.read(p,'unused')
    def test_grid_required_not_free_text(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as d:
            p=pathlib.Path(d)/'empty.png';Image.new('RGB',(400,400),'white').save(p)
            with self.assertRaisesRegex(ValueError,'grid'):reader.extract(p,[])
    @unittest.skipUnless(sys.platform=='darwin' and os.getenv('SECTOR_TEST_OCR_BINARY'),'macOS Vision integration is explicit')
    def test_real_54_rows_blank_cells_and_crop_recovery(self):
        ocr=pathlib.Path(os.environ['SECTOR_TEST_OCR_BINARY'])
        if not ocr.exists():self.fail('OCR binary missing')
        actual=reader.read(ROOT/'test/fixtures/is-buyback/2026-10-23.jpg',ocr)
        expected=json.loads((ROOT/'test/fixtures/is-buyback/2026-10-23.json').read_text())
        self.assertEqual(actual['row_count'],54)
        self.assertEqual([(r['ticker'],r['day'],r['nominal'],r['price'],r['amount']) for r in actual['rows']],[(r['ticker'],r['day'],r['nominal'],r['price'],r['amount']) for r in expected['rows']])
        self.assertEqual([r for r in actual['rows'] if r['ticker']=='MASFN'][0]['price'],None)
if __name__=='__main__':unittest.main()
