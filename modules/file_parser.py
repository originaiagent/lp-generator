import pandas as pd
import os
from typing import Dict, Any

class FileParser:
    
    def __init__(self):
        pass
    
    def parse(self, file_path: str) -> Dict[str, Any]:
        filename = os.path.basename(file_path)
        
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
            content = df.to_dict('records')
            return {
                "type": "csv",
                "content": content,
                "metadata": {"filename": filename}
            }
        
        elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            df = pd.read_excel(file_path)
            content = df.to_dict('records')
            return {
                "type": "excel",
                "content": content,
                "metadata": {"filename": filename}
            }
        
        elif file_path.endswith('.pdf'):
            # PDFはテキスト抽出
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
                return {
                    "type": "pdf",
                    "content": text,
                    "metadata": {"filename": filename}
                }
            except ImportError:
                # PyMuPDFがない場合はpdfplumberを試す
                try:
                    import pdfplumber
                    text = ""
                    with pdfplumber.open(file_path) as pdf:
                        for page in pdf.pages:
                            text += page.extract_text() or ""
                    return {
                        "type": "pdf",
                        "content": text,
                        "metadata": {"filename": filename}
                    }
                except ImportError:
                    return {
                        "type": "pdf",
                        "content": "PDFライブラリがインストールされていません",
                        "metadata": {"filename": filename}
                    }
        
        else:
            # テキストファイルとして読む
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return {
                "type": "text",
                "content": content,
                "metadata": {"filename": filename}
            }
    
    def extract_product_info(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        return {}
