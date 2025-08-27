from streamlit_qrcode_scanner import qrcode_scanner

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
