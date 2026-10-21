"""Optional native Vision smoke test; never uses installed service files."""
import json,os,platform,subprocess,tempfile,unittest
from pathlib import Path

@unittest.skipUnless(platform.system()=='Darwin' and os.environ.get('SECTOR_TEST_OCR_BINARY'),'Native OCR is a separate macOS CI job')
class NativeOcrTests(unittest.TestCase):
    def test_rendered_values_are_read_by_compiled_vision_binary(self):
        from PIL import Image,ImageDraw,ImageFont
        font=ImageFont.truetype(str(Path(__file__).parents[1]/'assets/NotoSans-Regular.ttf'),48)
        image=Image.new('RGB',(900,250),'white');ImageDraw.Draw(image).text((30,60),'765.000 EUR',fill='black',font=font)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'fixture.png';image.save(p)
            result=subprocess.run([os.environ['SECTOR_TEST_OCR_BINARY'],str(p)],check=True,capture_output=True,text=True,timeout=30)
            text=' '.join(row['text'] for row in json.loads(result.stdout))
            self.assertIn('765.000',text);self.assertIn('EUR',text)
