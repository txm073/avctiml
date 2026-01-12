import os
import sys
import json
import gzip
from PIL import Image
import subprocess
import zipfile

import pinyin


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


def compress_chars(char_dir: str, output_dir: str) -> None:
    with zipfile.ZipFile(os.path.join(output_dir, 'sets.zip'), 'w') as zf:
        for s in os.listdir(char_dir):
            info_path = os.path.join(char_dir, s, 'info.json')
            if not os.path.exists(info_path):
                continue
            info = json.load(open(info_path))
            name = info['name']
            zf.write(info_path, f'{name}/info.json')
            for item in info['set']:
                char_path = os.path.join(char_dir, s, "characters", f'{item['index']}.png')
                zf.write(char_path, f'{name}/characters/{item['index']}.png')


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


class SetAnnotator:
    
    def __init__(self, set_path: str) -> None:
        self.set_path = set_path
        self.info_file = os.path.join(set_path, 'info.json')
    
    def run(self) -> None:
        data = []
        name = input('Enter character set name: ').strip() or os.path.basename(self.set_path)
        for i in range(len(os.listdir(os.path.join(self.set_path, 'characters')))):
            char_img = Image.open(os.path.join(self.set_path, 'characters', f'{i}.png'))
            pinyin_img = Image.open(os.path.join(self.set_path, "pinyin", f'{i}.png'))
            char_img.show()
            pinyin_img.show()
            done = False
            while not done:
                chars = input('Enter chinese character: ')
                english = input('Enter english translation: ')
                done = input('Next? (Y/n)').strip().lower() != 'n'
            data.append({'chars': chars, 'pinyin': pinyin.get(chars), 'english': english, 'index': i})
            os.system('taskkill /IM photos.exe /F')
        info = {'name': name, 'set': data}
        with open(self.info_file, 'w') as f:
            f.write(json.dumps(info, indent=2))

def main(argv: list[str]) -> None:
    if len(argv) == 1:
        print('usage: set_creator {create,annotate} [args...]')
        return
    cmd = argv[1].lower().strip()
    if cmd == 'create':
        if len(argv) < 4:
            print('usage: set_creator create <document-path> <output-dir>')
            return
        parser = RnoteParser(argv[2])
        parser.export_symbols(argv[3])
    elif cmd == 'annotate':
        if len(argv) < 3:
            print('usage: set_creator annotate <set>')
            return
        SetAnnotator(argv[2]).run()
    elif cmd == "zip":
        if len(argv) < 4:
            print('usage: set_creator zip <path> <output>')
            return
        compress_chars(argv[2], argv[3])


if __name__ == '__main__':
    main(sys.argv)