# helpers/excel_loader.py
import pandas as pd

def cargar_agenda_excel(ruta: str) -> list[dict]:
    df = pd.read_excel(ruta)
    
    # Normalizamos nombres de columnas
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    
    # Rellenamos valores faltantes con cadenas vacías
    df = df.fillna("")
    
    return df.to_dict(orient="records")
