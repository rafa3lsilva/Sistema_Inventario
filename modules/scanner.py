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

def get_barcode_from_image(image_file):
    """
    Lê um código de barras a partir de um arquivo de imagem.
    Retorna o valor do código lido ou None se não for encontrado.
    """
    try:
        img = Image.open(image_file)
        decoded_objects = decode(img)
        if decoded_objects:
            # Pega o primeiro código encontrado
            barcode_data = decoded_objects[0].data.decode('utf-8')
            return str(barcode_data)
        return None
    except Exception as e:
        print(f"Erro ao ler imagem do código de barras: {e}")
        return None
