import cv2
import numpy as np
from pyzbar.pyzbar import decode
from PIL import Image

def test():
    print("Testing cv2.barcode presence")
    print(hasattr(cv2, 'barcode'))
test()
