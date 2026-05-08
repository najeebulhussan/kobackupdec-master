import sys
from PIL import Image

def create_ico(input_path, output_path):
    img = Image.open(input_path)
    # Crop to square if necessary
    width, height = img.size
    if width != height:
        min_dim = min(width, height)
        left = (width - min_dim) / 2
        top = (height - min_dim) / 2
        right = (width + min_dim) / 2
        bottom = (height + min_dim) / 2
        img = img.crop((left, top, right, bottom))
    
    img.save(output_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])

if __name__ == "__main__":
    create_ico(sys.argv[1], sys.argv[2])
