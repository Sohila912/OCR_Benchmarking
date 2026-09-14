from pathlib import Path
import sys
sys.path.insert(0, 'c:/Users/Shrouk/Desktop/OCR_Benchmarking/runners')
from surya_runner import SuryaRunner
from pdf2image import convert_from_path

pdf = Path('c:/Users/Shrouk/Desktop/OCR_Benchmarking/Datasets/English/Dataset/crowd_1.pdf')
pages = convert_from_path(str(pdf), dpi=300)
print('pages', len(pages))
runner = SuryaRunner()
print('predictor', runner.rec_predictor)
try:
    res = runner._predict(pages)
    print('predict result type', type(res))
    print('predict result', res)
except Exception as e:
    import traceback
    print('predict error', type(e).__name__, e)
    traceback.print_exc()
