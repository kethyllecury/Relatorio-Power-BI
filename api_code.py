import requests
import pandas as pd
import time
import base64
import json
import re
import os
import subprocess


CLIENT_ID = "e54144a5b51c3c931133d95ba48c1698a766afec"
CLIENT_SECRET = "d590501ad197808124178928e3e655d79554d8a9ed53861444250e25fedf"
REDIRECT_URI = "https://www.zerofuro.com.br/"
AUTHENTICATION_CODE = ""
ACCESS_TOKEN = ""
REFRESH_TOKEN = ""
DELAY = 1
TESTE = False
LOGGING = True


def log(*args, sep=' ', end='\n', file=None, flush=False):
    global LOGGING
    if not LOGGING:
        return 
    print(*args, sep=sep, end=end, file=file, flush=flush)

def logtxt(title, msg):
    with open(f'{title}.txt', 'w') as f:
        f.write(msg)
    # Abrir o arquivo no Notepad sem bloquear o programa principal
    subprocess.Popen(["notepad.exe", f"{title}.txt"], close_fds=True)

def get_keys():
    response = requests.get("https://apibling-b0db0-default-rtdb.firebaseio.com/tokens.json")
    if response.status_code == 200:
        try:
            data = response.json()
            return {
                "access": data.get("access"),
                "refresh": data.get("refresh"),
                "auth": data.get("auth"),
            }
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return None
    else:
        print("Erro ao obter dados:", response.status_code, response.text)
        return None

def update_keys(updated_values):

    response = requests.patch(
        "https://apibling-b0db0-default-rtdb.firebaseio.com/tokens.json", json=updated_values
    )
    if response.status_code == 200:
        print("Dados atualizados com sucesso.")
    else:
        print("Erro ao atualizar dados:", response.status_code, response.text)

def get_pagina(tabela):
    
    response = requests.get(
        f"https://apibling-b0db0-default-rtdb.firebaseio.com/tabelas/{tabela}.json"
    )
    if response.status_code == 200:
        data = response.json()
        if data is None:
          return 1
        if "pagina" in data:
            return data["pagina"]
        return 1
    else:
        return 1

def update_pagina(tabela, pagina):
    body = {
        "pagina" : pagina
    }
    response = requests.patch(
        f"https://apibling-b0db0-default-rtdb.firebaseio.com/tabelas/{tabela}.json", json=body
    )
    if response.status_code == 200:
        print("Dados atualizados com sucesso.")
    else:
        print("Erro ao atualizar dados:", response.status_code, response.text)

def obter_token(auth, refresh):
    url = "https://www.bling.com.br/Api/v3/oauth/token"
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    global ACCESS_TOKEN
    global REFRESH_TOKEN

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    payload = {
        "grant_type": "authorization_code",
        "code": auth,
        "redirect_uri": REDIRECT_URI,
    }

    response = requests.post(url, headers=headers, data=payload)

    if response.status_code == 200:
        token_data = response.json()
        print("Access token obtido com sucesso:", token_data)
        ACCESS_TOKEN = token_data["access_token"]
        REFRESH_TOKEN = token_data["refresh_token"]
        update_keys(
            {"access": token_data["access_token"], "refresh": token_data["refresh_token"]}
        )
    else:
        print("Erro ao obter access token:", response.text)
        get_new_access_token(refresh)

def get_new_access_token(refresh):
    global ACCESS_TOKEN
    global REFRESH_TOKEN
    global CLIENT_ID
    global CLIENT_SECRET

    url = "https://www.bling.com.br/Api/v3/oauth/token"
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    response = requests.post(url, headers=headers, data=payload)

    if response.status_code == 200:
        token_data = response.json()
        ACCESS_TOKEN = token_data["access_token"]
        REFRESH_TOKEN = token_data["refresh_token"]
        update_keys(
            {"access": token_data["access_token"], "refresh": token_data["refresh_token"]}
        )
        print("Refresh token obtido com sucesso:", token_data)
    else:
        print("Erro ao obter refresh token:", response.text)

def consultar_relatorios_pagina(pagina, url_original, nome):
    global TESTE
    global ACCESS_TOKEN

    limite  = 5 if TESTE else 100

    url = re.sub(r"pagina=\d+", f"pagina={pagina}", url_original)
    url = re.sub(r"limite=\d+", f"limite={limite}", url)

    log(f"Começando página {pagina} de {nome} ({url})")

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()

    log("Erro na pagina:", pagina, response.text)
    return None

def consultar_todas_as_paginas(url, nome):
    pagina = 1
    relatorios_acumulados = []
    global DELAY
    while True:
        
        relatorios = consultar_relatorios_pagina(pagina, url, nome)
        time.sleep(DELAY)

        if relatorios is None or "data" not in relatorios or not relatorios["data"]:
            break
    
        relatorios_acumulados.extend(relatorios["data"])
        log(f"Terminando página {pagina} de {nome}, tamanho = {len(relatorios["data"])}")

        if len(relatorios["data"]) < 100:
            break

        pagina += 1
        if TESTE:
            break

    return relatorios_acumulados

def check_update(bling, planilha, colunas):

    elementos_novos = []
    elementos_alterados = []

    for i, elemento_bling in bling.iterrows():
        elemento_planilha = planilha[planilha["id"] == elemento_bling["id"]]
        if elemento_planilha.empty:
            elementos_novos.append(bling.iloc[i])
            log("elemento", elemento_bling["id"], "é novo")
            continue

        elemento_planilha = elemento_planilha.iloc[0]
    
        for coluna in colunas:
            if elemento_bling[coluna] != elemento_planilha[coluna]:
                try: 
                    lhs = int(elemento_bling[coluna])
                    rhs = int(elemento_planilha[coluna])
                    if lhs == rhs:
                        continue
                except:
                    pass
            
                log("elemento", elemento_bling["id"], "foi alterado em:", coluna, "antes:", elemento_planilha[coluna], "depois:", elemento_bling[coluna])
                #log(elemento_bling)
                #log(processar_dados([elemento_bling], "https://api.bling.com.br/Api/v3/nfe", "notas").iloc[0])
                #return []
                elementos_alterados.append(bling.iloc[i])
                
                break
                
    if len(elementos_alterados) == 0 and len(elementos_novos) == 0:
        return (pd.DataFrame(), pd.DataFrame())
    if len(elementos_alterados) == 0:
        return (pd.DataFrame(elementos_novos), pd.DataFrame())
    if len(elementos_novos) == 0:
        return (pd.DataFrame(), pd.DataFrame(elementos_alterados))

    return (pd.DataFrame(elementos_novos), pd.DataFrame(elementos_alterados))

def find_id(relatorios, id):
    for i in range(len(relatorios)):
        if relatorios[i]["id"] == id:
            return i
    return -1

def processar_dados(relatorios, url, nome):
    relatorios_acumulados = []
    i = 1

    global DELAY

    if len(relatorios) == 0:
        return pd.DataFrame()
   
    for id in relatorios["id"]:

        log(f"[{i}]Consultando detalhes de {nome} {id}")
        i += 1
        
        url_id = f"{url}/{id}"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        response = requests.get(url_id, headers=headers)

        if response.status_code == 200:
            linha_detalhada = response.json()
            
            relatorios_acumulados.append(linha_detalhada["data"])  # Supondo que 'data' contenha as informações relevantes
        else:
            log(f"Erro ao consultar detalhes de {nome} {id}: {response.status_code} {response.text} {response}")

        # Adiciona um pequeno delay entre as requisições
        time.sleep(DELAY)

    if relatorios_acumulados:
    #    relatorios_acumulados = pd.concat(relatorios_acumulados, ignore_index=True)
    #   return relatorios_acumulados 
        return pd.json_normalize(relatorios_acumulados)

    return pd.DataFrame()

def is_json(val):
    try:
        json.loads(val)  # Tenta carregar como JSON
        return True
    except (TypeError, json.JSONDecodeError):
        return False

def tratar_dados(df_final_completo, ignore_items=False):

    if ignore_items:
        colunas_json = [col for col in df_final_completo.columns if df_final_completo[col].apply(is_json).all()]
        colunas_explodidas = []
        for coluna in colunas_json:
            df_final_completo[coluna] == df_final_completo[coluna].apply(json.loads)
            df_explodido = pd.json_normalize(df_final_completo[coluna])
            df_explodido.columns = [f"{coluna}.{subcol}" for subcol in df_explodido.columns]
            colunas_explodidas.append(df_explodido)
        

        df_final = pd.concat([df_final_completo.drop(columns=colunas_json)] + colunas_explodidas, axis=1)
        return df_final

    if 'itens' not in df_final_completo.columns:
        return pd.DataFrame()

    df_explodido = df_final_completo.explode('itens', ignore_index=True)
    df_itens_explodido = pd.json_normalize(df_explodido['itens'])
    df_itens_explodido = df_itens_explodido[['codigo', 'valor', 'descricao', 'quantidade']]
    df_final = pd.concat([df_explodido.reset_index(drop=True), df_itens_explodido], axis=1)
    
    return df_final


tokens = get_keys()
obter_token(tokens["auth"], tokens["refresh"])
log(ACCESS_TOKEN, REFRESH_TOKEN)


tabelas = [
    {
        "nome" : "vendedores",
        "url" : ["https://api.bling.com.br/Api/v3/vendedores?pagina=0&limite=0"],
        "url_detalhada" : "https://api.bling.com.br/Api/v3/vendedores",
        "colunas_verificar" : []
    },
    {
        "nome" : "notas",
        "url" : [
            "https://api.bling.com.br/Api/v3/nfe?pagina=0&limite=0&situacao=2",
            "https://api.bling.com.br/Api/v3/nfe?pagina=0&limite=0"

        ],

        "url_detalhada" : "https://api.bling.com.br/Api/v3/nfe",
        "colunas_verificar" : ["situacao"]

    },
    {
        "nome" : "vendas",
        "url" : ["https://api.bling.com.br/Api/v3/pedidos/vendas?pagina=0&limite=0"],
        "url_detalhada" : "https://api.bling.com.br/Api/v3/pedidos/vendas",
        "tratar" : True,
        "colunas_verificar" : ["situacao.valor"]
    },
    {
        "nome" : "contas_pagar",
        "url" : ["https://api.bling.com.br/Api/v3/contas/pagar?pagina=0&limite=0"],
        "url_detalhada" : "https://api.bling.com.br/Api/v3/contas/pagar",
        "colunas_verificar" : ["situacao"]
    },
    {
        "nome" : "contas_receber",
        "url" : ["https://api.bling.com.br/Api/v3/contas/receber?pagina=0&limite=0"],
        "url_detalhada" : "https://api.bling.com.br/Api/v3/contas/receber",
        "colunas_verificar" : ["situacao"]
    },
    {
        "nome" : "produtos",
        "url" : ["https://api.bling.com.br/Api/v3/produtos?pagina=0&limite=0"],
        "url_detalhada" : "https://api.bling.com.br/Api/v3/produtos",
        "colunas_verificar" : []
    },
    {
        "nome" : "clientes",
        "url" : ["https://api.bling.com.br/Api/v3/contatos?pagina=0&limite=0"],
        "url_detalhada" : "https://api.bling.com.br/Api/v3/contatos",
        "colunas_verificar" : []
    }
]

num_tabelas = len(tabelas)

for i in range(num_tabelas): #1

    tabela = tabelas[i] #tabela que quer para gerar separadamente
    temp_file = f"C:/Users/sigab/OneDrive - Siga Financeiro e Controladoria/API/API_ZEROFURO/Excel/{tabela["nome"]}.xlsx" # garantir que a pasta q isso vai ser salvo e visivel

    if not os.path.exists(temp_file):

        relatorios = []
        for url in tabela["url"]:
            relatorios.extend(consultar_todas_as_paginas(url, tabela["nome"]))
        
        relatorios = pd.json_normalize(relatorios)
        relatorios_detalhados = processar_dados(relatorios, tabela["url_detalhada"], tabela["nome"])

        if "tratar" in tabela:
            relatorios_detalhados = tratar_dados(relatorios_detalhados)

        relatorios_detalhados.to_excel(temp_file, index=False, engine='openpyxl')

    else: 
        df = pd.read_excel(temp_file)
        relatorios = []
        for url in tabela["url"]:
            relatorios.extend(consultar_todas_as_paginas(url, tabela["nome"]))

        relatorios = pd.json_normalize(relatorios)
    
        if "tratar" in tabela:
            relatorios = tratar_dados(relatorios, True)
      
      
        (novos, alterados) = check_update(relatorios, df, tabela["colunas_verificar"])
    
        relatorios_detalhados = processar_dados(novos, tabela["url_detalhada"], tabela["nome"])

        if "tratar" in tabela:
            relatorios_detalhados = tratar_dados(relatorios_detalhados)

        relatorios_detalhados = pd.concat([df, relatorios_detalhados])

        for i, alterado in alterados.iterrows():
            if "colunas_verificar" in tabela:
                for coluna in tabela["colunas_verificar"]:
                    relatorios_detalhados.loc[relatorios_detalhados['id'] == alterado["id"], coluna] = alterado[coluna]

        relatorios_detalhados.to_excel(temp_file, index=False, engine='openpyxl')


path = f"C:/Users/sigab/OneDrive - Siga Financeiro e Controladoria/API/API_ZEROFURO/Excel" 
dfs = []

for tabela in tabelas:
    tabela_path = f'{path}/{tabela["nome"]}.xlsx'
    dfs.append(pd.read_excel(tabela_path))

vendedores, notas, vendas, contas_pagar, contas_receber, produtos, clientes = dfs

vendedores
notas
vendas
contas_pagar
contas_receber
produtos
clientes

