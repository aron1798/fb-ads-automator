import os
import json
import gspread
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN DESDE GITHUB SECRETS ---
# El código busca las llaves en la "Caja Fuerte" de GitHub
FB_ACCESS_TOKEN = os.environ["FB_ACCESS_TOKEN"]
FB_AD_ACCOUNT_ID = os.environ["FB_AD_ACCOUNT_ID"]
GOOGLE_CREDENTIALS = json.loads(os.environ["GCP_CREDENTIALS"])

# TUS NOMBRES EXACTOS
NOMBRE_ARCHIVO_SHEET = "FacebookAdds"
NOMBRE_PESTAÑA = "ReporteDiario"

# --- 2. CONECTAR A GOOGLE SHEETS ---
print("Conectando a Google Sheets...")
try:
    gc = gspread.service_account_from_dict(GOOGLE_CREDENTIALS)
    # Abre el archivo y la hoja específica
    sh = gc.open(NOMBRE_ARCHIVO_SHEET).worksheet(NOMBRE_PESTAÑA)
except Exception as e:
    print(f"Error crítico conectando al Excel: {e}")
    exit(1)

# --- 3. CONECTAR A FACEBOOK ---
print("Conectando a Facebook...")
FacebookAdsApi.init(access_token=FB_ACCESS_TOKEN)

# FECHA = AYER (para cerrar el día completo)
yesterday = datetime.now() - timedelta(days=1)
yesterday_str = yesterday.strftime('%Y-%m-%d')
print(f"Buscando datos del: {yesterday_str}")

# --- 4. PEDIR DATOS A FACEBOOK ---
fields = ['campaign_name', 'spend', 'impressions', 'clicks', 'ctr', 'actions']
params = {
    'level': 'campaign',
    'time_range': {'since': yesterday_str, 'until': yesterday_str},
}

try:
    account = AdAccount(FB_AD_ACCOUNT_ID)
    insights = account.get_insights(fields=fields, params=params)
except Exception as e:
    print(f"Error en API Facebook: {e}")
    exit(1)

if not insights:
    print("No hubo campañas activas ayer. Fin del proceso.")
    exit(0)

# --- 5. PROCESAR DATOS ---
nuevas_filas = []

for item in insights:
    mensajes_totales = 0
    mensajes_nuevos = 0
    
    if 'actions' in item:
        for action in item['actions']:
            # Resultados (Conversaciones iniciadas)
            if action['action_type'] == 'onsite_conversion.messaging_conversation_started_7d':
                mensajes_totales = int(action['value'])
            # Nuevos Contactos
            if action['action_type'] == 'onsite_conversion.messaging_first_reply':
                mensajes_nuevos = int(action['value'])

    # Fila lista: Fecha | Campaña | Gasto | Impresiones | Clics | Resultados | Nuevos | CTR
    fila = [
        yesterday_str,
        item.get('campaign_name'),
        float(item.get('spend', 0)),
        int(item.get('impressions', 0)),
        int(item.get('clicks', 0)),
        mensajes_totales,
        mensajes_nuevos,
        float(item.get('ctr', 0))
    ]
    nuevas_filas.append(fila)

# --- 6. GUARDAR ---
if nuevas_filas:
    sh.append_rows(nuevas_filas)
    print(f"¡Éxito! Se guardaron {len(nuevas_filas)} filas.")
else:
    print("Datos vacíos.")
