import streamlit.components.v1 as components
import streamlit as st


def mostrar_scanner_ean(largura="100%", altura=300, tempo_limite=10):
    st.subheader("📷 Leitor de código de barras (EAN)")

    components.html(
        f"""
        <script src="https://unpkg.com/html5-qrcode" type="text/javascript"></script>
        <div id="reader" style="width:{largura}; margin-bottom: 10px;"></div>
        <script>
            function onScanSuccess(decodedText, decodedResult) {{
                const inputField = window.parent.document.querySelector('[data-testid="stTextInput"] input');
                if (inputField) {{
                    inputField.value = decodedText;
                    inputField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
                html5QrcodeScanner.clear();
            }}

            const html5QrcodeScanner = new Html5QrcodeScanner("reader", {{
                fps: 10,
                qrbox: {{ width: 250, height: 100 }},
                disableFlip: true
            }});
            html5QrcodeScanner.render(onScanSuccess);

            // Encerramento automático após {tempo_limite} segundos
            setTimeout(() => {{
                html5QrcodeScanner.clear();
                document.getElementById("reader").innerHTML = "<p style='text-align:center;'>⏱️ Scanner encerrado automaticamente.</p>";
            }}, {tempo_limite * 1000});
        </script>
        """,
        height=altura
    )
