# Em modules/scanner.py

import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode
from pyzbar.pyzbar import decode
import cv2
import threading
from PIL import Image

# Usamos um lock para garantir que a variável do código de barras seja acedida de forma segura
lock = threading.Lock()
barcode_value = None

# Esta classe processa cada frame do vídeo


class BarcodeTransformer(VideoTransformerBase):
    def recv(self, frame):
        global barcode_value

        # Converte o frame para o formato de imagem do OpenCV
        img = frame.to_ndarray(format="bgr24")

        # Tenta descodificar códigos de barras na imagem
        # Aumentamos os tipos de códigos de barras que ele pode procurar
        barcodes = decode(img)

        if barcodes:
            for barcode in barcodes:
                # Extrai o valor do código de barras
                barcode_data = barcode.data.decode("utf-8")

                # Armazena o valor de forma segura
                with lock:
                    barcode_value = barcode_data

                # --- INÍCIO DO FEEDBACK VISUAL ---
                # Desenha um retângulo verde à volta do código de barras detetado
                (x, y, w, h) = barcode.rect
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # Escreve o valor do código de barras no vídeo
                cv2.putText(img, barcode_data, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                # --- FIM DO FEEDBACK VISUAL ---

        # Retorna a imagem com as anotações (ou a original se nada for encontrado)
        return img


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
        media_stream_constraints={
            "video": {"facingMode": "environment"}, "audio": False},
        async_processing=True,
    )

    with lock:
        return barcode_value
