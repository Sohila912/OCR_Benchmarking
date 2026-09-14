from pathlib import Path
import sys
sys.path.insert(0, 'c:/Users/Shrouk/Desktop/OCR_Benchmarking/runners')
from surya_runner import SuryaRunner

pdf = Path('c:/Users/Shrouk/Desktop/OCR_Benchmarking/Datasets/English/Dataset/crowd_1.pdf')
runner = SuryaRunner()
print('predictor', runner.rec_predictor)
result = runner.run(pdf)
print('result type', type(result).__name__)
print('result preview', repr(result[:400]))
print('result len', len(result))
