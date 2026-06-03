from streamlit_qrcode_scanner import qrcode_scanner
from pyzbar.pyzbar import decode
from PIL import Image

def get_barcode():
    """
    Mostra o widget da câmera e espera por um código de barras.
    Retorna o valor do código de barras lido ou None.
    """
    # A chamada da função para ativar a câmera
    barcode_data = qrcode_scanner()

    if barcode_data:
        return str(barcode_data)

    return None

import cv2
import numpy as np

def get_barcode_from_image(image_file):
    """
    Lê um código de barras a partir de um arquivo de imagem.
    Aplica técnicas de visão computacional (OpenCV) para melhorar a leitura.
    """
    try:
        # Abrir imagem com Pillow e converter para array do Numpy
        img = Image.open(image_file)
        
        # Garantir que a imagem esteja em modo RGB (Pillow pode abrir como RGBA)
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        img_array = np.array(img)
        
        # 1. Tentar ler a imagem original primeiro
        decoded_objects = decode(img)
        if decoded_objects:
            return str(decoded_objects[0].data.decode('utf-8'))
            
        # 2. Se falhar, converter para Tons de Cinza (Grayscale)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        decoded_objects = decode(gray)
        if decoded_objects:
            return str(decoded_objects[0].data.decode('utf-8'))
            
        # 3. Aplicar equalização de histograma (melhora muito o contraste em fotos escuras como de webcams)
        equalized = cv2.equalizeHist(gray)
        decoded_objects = decode(equalized)
        if decoded_objects:
            return str(decoded_objects[0].data.decode('utf-8'))
            
        # 4. Aplicar Filtro de Nitidez (Sharpening) para focar as barras
        kernel_sharpening = np.array([[-1,-1,-1], [-1, 9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(gray, -1, kernel_sharpening)
        decoded_objects = decode(sharpened)
        if decoded_objects:
            return str(decoded_objects[0].data.decode('utf-8'))

        # 5. Aplicar limiarização (Thresholding) para aumentar o contraste do preto/branco
        # Útil para fotos com sombras ou iluminação desigual
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        decoded_objects = decode(thresh)
        if decoded_objects:
            return str(decoded_objects[0].data.decode('utf-8'))
            
        # 6. Tentar redimensionar a imagem (fotos de celular às vezes são grandes demais)
        scale_percent = 50 # reduz pela metade
        width = int(gray.shape[1] * scale_percent / 100)
        height = int(gray.shape[0] * scale_percent / 100)
        resized = cv2.resize(gray, (width, height), interpolation = cv2.INTER_AREA)
        decoded_objects = decode(resized)
        if decoded_objects:
            return str(decoded_objects[0].data.decode('utf-8'))
            
        # 7. Tentar redimensionar aumentando a imagem (fotos de PC às vezes são pequenas/borradas)
        scale_up = 150
        width_up = int(gray.shape[1] * scale_up / 100)
        height_up = int(gray.shape[0] * scale_up / 100)
        resized_up = cv2.resize(gray, (width_up, height_up), interpolation = cv2.INTER_CUBIC)
        decoded_objects = decode(resized_up)
        if decoded_objects:
            return str(decoded_objects[0].data.decode('utf-8'))

        return None
    except Exception as e:
        print(f"Erro ao processar a imagem do código de barras: {e}")
        return None
