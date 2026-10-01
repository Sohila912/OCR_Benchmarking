from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'benchmarks/legacy/runners'))
from surya_runner import SuryaRunner

pdf = Path(__file__).resolve().parents[1] / 'benchmarks/datasets/English/Dataset/crowd_1.pdf'
runner = SuryaRunner()
print('predictor', runner.rec_predictor)
result = runner.run(pdf)
print('result type', type(result).__name__)
print('result preview', repr(result[:400]))
print('result len', len(result))
