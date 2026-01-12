import os
import json
import gzip
from PIL import Image
import subprocess


GRID_SIZE: int = 100


blank_file = lambda: {
    'version': '0.11.0', 
    'data': {
        'engine_snapshot': {
            'document': {
                'x': 0.0, 
                'y': 0.0, 
                'width': 1024.0, 
                'height': 1024.0, 
                'format': {
                    'width': 1024.0, 
                    'height': 1024.0, 
                    'dpi': 96.0, 
                    'orientation': 'portrait', 
                    'border_color': {
                        'r': 0.0, 
                        'g': 0.0, 
                        'b': 0.0, 
                        'a': 1.0
                    }, 
                    'show_borders': False, 
                    'show_origin_indicator': False
                }, 
                'background': {
                    'color': {
                        'r': 0.0, 
                        'g': 0.0, 
                        'b': 0.0, 
                        'a': 1.0
                    },
                    'pattern': 'none',
                    'pattern_size': [
                        64.0, 
                        64.0
                    ], 
                    'pattern_color': {
                        'r': 1.0, 
                        'g': 1.0, 
                        'b': 1.0, 
                        'a': 1.0
                    }
                }, 
                'layout': 'continuous_vertical', 
                'snap_positions': False
            }, 
            'camera': {
                'offset': [
                    -96.0, 
                    -96.0
                ], 
                'size': [
                    949.0, 
                    933.0
                ], 
                'zoom': 1.0
            }, 
            'stroke_components': [
                {
                    'value': None, 
                    'version': 0
                }
            ], 
            'chrono_components': [
                {
                    'value': None, 
                    'version': 0
                }
            ], 
            'chrono_counter': 0
        }
    }
}


class RnoteParser:

    def __init__(self, fp: str) -> None:
        self.fp = fp;
        self.contents = self.load_file(self.fp)
        self.rows = int(self.contents['data']['engine_snapshot']['document']['height']) // GRID_SIZE 
        self.all_strokes = list(filter(
            lambda s: s['value'] is not None and s['value'].get('brushstroke'),
            self.contents['data']['engine_snapshot']['stroke_components']
        ))

    def export_symbols(self, path: str) -> None:
        if not os.path.exists(path):
            os.makedirs(path)
        set_index = 0
        count = 0
        sets = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        for i in range(self.rows):
            char_rect = [0, i * GRID_SIZE, GRID_SIZE, (i + 1) * GRID_SIZE]
            pinyin_rect = [GRID_SIZE, i * GRID_SIZE, 2 * GRID_SIZE, (i + 1) * GRID_SIZE]
            char = list(filter(
                lambda s: self.rect_contains(self.get_bounding_rect(s['value']['brushstroke']), char_rect),
                self.all_strokes
                ))
            pinyin = list(filter(
                lambda s: self.rect_contains(self.get_bounding_rect(s['value']['brushstroke']), pinyin_rect),
                self.all_strokes
                ))
            if not char or not pinyin:
                if not count:
                    break
                print(f'Exported set {sets[set_index]}')
                set_index += 1
                count = 0
                continue
            if not os.path.exists(os.path.join(path, sets[set_index])):
                os.makedirs(os.path.join(path, sets[set_index], 'characters'))
                os.makedirs(os.path.join(path, sets[set_index], 'pinyin'))
            self.export_to_png(char, os.path.join(path, sets[set_index], 'characters', str(count) + '.png'))
            self.export_to_png(pinyin, os.path.join(path, sets[set_index], 'pinyin', str(count) + '.png'))
            count += 1
        print('Exported all sets')

    def export_to_png(self, symbol: list[dict], output: str) -> None:
        bf = blank_file()
        bf['data']['engine_snapshot']['stroke_components'].extend(symbol)
        with open('/tmp/temp.rnote', 'wb') as f:
            f.write(gzip.compress(json.dumps(bf).encode()))
        cmd = [
            'rnote-cli', 'export', 'selection', '--output-file', output, 
            '--no-pattern', '--no-background', 'all', '/tmp/temp.rnote' 
        ]     
        subprocess.run(cmd, stdout=subprocess.DEVNULL)
        
    def load_file(self, fp: str) -> dict:
        with gzip.open(fp) as f:
            contents = json.loads(f.read())
        return contents

    def rect_contains(self, r1: list[float], r2: list[float]) -> bool:
        return r1[0] > r2[0] and r1[1] > r2[1] and r1[2] < r2[2] and r1[3] < r2[3]

    def get_bounding_rect(self, stroke: dict) -> list[float]:
        segments = stroke['path']['segments']
        coords = [segment['lineto']['end']['pos'] for segment in segments]
        x, y = [coord[0] for coord in coords], [coord[1] for coord in coords]
        return [min(x), min(y), max(x), max(y)]


if __name__ == '__main__':
    parser = RnoteParser('/home/tom/Work/Mandarin/L2/Character Sets/Set A.rnote')
    parser.export_symbols('chinese')

