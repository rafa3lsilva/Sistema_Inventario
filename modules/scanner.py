import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode
from pyzbar.pyzbar import decode
import cv2
import threading

# Usamos um lock para garantir que a variável do código de barras seja acedida de forma segura
lock = threading.Lock()
barcode_value = None

# Esta classe processa cada frame do vídeo


class BarcodeTransformer(VideoTransformerBase):
    def __init__(self):
        self.barcode_found = False

    def transform(self, frame):
        global barcode_value

        # Se um código de barras já foi encontrado, não processa mais frames
        if self.barcode_found:
            return frame

        # Converte o frame para o formato de imagem do OpenCV
        img = frame.to_ndarray(format="bgr24")

        # Converte a imagem para escala de cinza para facilitar a deteção
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Tenta descodificar códigos de barras na imagem
        barcodes = decode(gray)

        if barcodes:
            for barcode in barcodes:
                # Extrai o valor do código de barras
                barcode_data = barcode.data.decode("utf-8")

                # Armazena o valor de forma segura
                with lock:
                    barcode_value = barcode_data

                self.barcode_found = True  # Marca que encontrou para parar o processamento
                break  # Sai do loop assim que encontrar o primeiro

        return frame


def barcode_scanner_component():
    """
    Inicia o componente da câmera e retorna o valor do código de barras lido.
    """
    global barcode_value

    # Reinicia o valor do código de barras antes de iniciar
    with lock:
        barcode_value = None

    webrtc_streamer(
        key="barcode-scanner",
        mode=WebRtcMode.SENDONLY,
        video_transformer_factory=BarcodeTransformer,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
    )

    with lock:
        return barcode_value
