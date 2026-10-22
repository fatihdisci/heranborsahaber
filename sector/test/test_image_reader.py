import json,pathlib,tempfile,unittest
from unittest.mock import patch
from PIL import Image,ImageDraw,ImageFont
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from read_image import market_passages,decimal_value,lot_value,read_image,recover_labels

def block(text,x,y):return {'text':text,'x':x,'y':y,'width':.08,'height':.025,'confidence':1}
def table():
    out=[block('ASELS',.02,.02)]
    for y,who,percent,lot,price in [(.2,'Ak','%55.50','766.204','348.02'),(.6,'İş','%19.19','-264.966','348.24')]:
        out += [block(t,x,y) for t,x in zip(['KURUM','ORAN','NET LOT','MALİYET'],[.02,.35,.56,.83])]
        out += [block(t,x,y+.06) for t,x in zip([who,percent,lot,price],[.02,.32,.53,.86])]
    return out

class ImageReaderTests(unittest.TestCase):
    def test_column_locale_sign_and_no_invented_date_or_currency(self):
        meta,passages=market_passages(table());self.assertEqual(meta,{'kind':'akd','ticker':'ASELS'})
        text='\n'.join(p['text'] for p in passages)
        self.assertIn('%55,50',text);self.assertIn('766.204 lot',text);self.assertIn('Maliyet: 348,02',text)
        self.assertIn('-264.966 lot',text);self.assertIn('Net satım miktarı: 264.966 lot',text)
        self.assertIn('tarihi ve saati belirtilmemiş',text);self.assertNotIn('348,02 TL',text)
    def test_missing_label_or_number_never_silently_drops_a_ranked_row(self):
        for field in ['İş','-264.966','348.24']:
            with self.assertRaisesRegex(ValueError,'image_market_table_incomplete'):market_passages([b for b in table() if b['text']!=field])
    def test_ambiguous_decimal_lot_and_incomplete_table_fail(self):
        self.assertEqual(lot_value('-264.966'),'-264.966 lot');self.assertEqual(decimal_value('%55.50',True),'%55,50')
        for value in ['264.96','264,966','26 4966']:
            with self.assertRaises(ValueError):lot_value(value)
        with self.assertRaises(ValueError):decimal_value('%155.50',True)
        with self.assertRaisesRegex(ValueError,'incomplete'):market_passages([b for b in table() if b['y']<.6])
    def test_image_parser_preserves_the_original_visual_and_every_row(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);p=root/'source.png';Image.new('RGB',(900,1080),(10,10,10)).save(p)
            response=type('Result',(),{'stdout':json.dumps(table())})
            with patch('read_image.subprocess.run',return_value=response):result=read_image(p,root/'evidence',root/'ocr')
            self.assertEqual(result['market_data']['ticker'],'ASELS');self.assertTrue(result['coverage']['complete'])
            self.assertEqual(len(result['images']),1)
            with Image.open(result['images'][0]) as stored:self.assertEqual(stored.size,(900,1080))
            self.assertTrue(any(p['id']=='image_ocr_raw' for p in result['passages']))
    def test_short_label_recovery_uses_source_pixels_and_never_guesses_when_the_retry_is_unreadable(self):
        with tempfile.TemporaryDirectory() as temp:
            p=pathlib.Path(temp)/'source.png';im=Image.new('RGB',(900,1080),(10,10,10));draw=ImageDraw.Draw(im)
            font=ImageFont.truetype(str(pathlib.Path(__file__).resolve().parents[1]/'assets/NotoSans-Bold.ttf'),26)
            draw.text((18,648),'KURUM',font=font,fill='white');draw.text((18,713),'İş',font=font,fill=(0,220,220));im.save(p)
            missing=[b for b in table() if b['text']!='İş']
            response=type('Result',(),{'stdout':json.dumps([{'text':'KURUMiş','confidence':1}])})
            with patch('read_image.subprocess.run',return_value=response):fixed=recover_labels(missing,p,pathlib.Path(temp)/'ocr')
            self.assertTrue(any(b['text']=='iş' and abs(b['y']-.66)<.01 for b in fixed));self.assertIsNotNone(market_passages(fixed))
            response.stdout=json.dumps([{'text':'KURUM','confidence':1}])
            with patch('read_image.subprocess.run',return_value=response):unread=recover_labels(missing,p,pathlib.Path(temp)/'ocr')
            with self.assertRaisesRegex(ValueError,'incomplete'):market_passages(unread)
    def test_explicit_data_dates_are_preserved_without_using_the_machine_clock(self):
        _,passages=market_passages(table()+[block('21 Ekim 2026',.2,.1)])
        self.assertIn('21 Ekim 2026',passages[0]['text']);self.assertNotIn('tarihi ve saati belirtilmemiş',passages[0]['text'])

if __name__=='__main__':unittest.main()
