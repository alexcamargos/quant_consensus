"""Módulo para raspagem direta da página Carteira Valor."""

import urllib.request
import time
from bs4 import BeautifulSoup
from typing import Any, List, Dict, Union
from loguru import logger
from datetime import datetime, timezone

def _extrair_html_para_carteiras(html: bytes) -> List[Dict[str, Any]]:
    """Função auxiliar para fazer o parse do HTML e extrair as carteiras."""
    soup = BeautifulSoup(html, 'html.parser')
    corretoras_divs = soup.find_all('div', class_='bx-corretoras')
    
    if not corretoras_divs:
        return []
    
    carteiras = []
    
    for div in corretoras_divs:
        nome_corretora = div.get('data-name', 'Desconhecida').strip()
        tickers = []
        tbody = div.find('tbody')
        if tbody:
            for row in tbody.find_all('tr'):
                tds = row.find_all('td')
                if len(tds) >= 2:
                    ticker = tds[1].get_text(strip=True)
                    if ticker:
                        tickers.append(ticker)
        
        if tickers:
            carteiras.append({
                "corretora": nome_corretora,
                "tickers": tickers
            })
            
    return carteiras

def extrair_carteiras_valor(url: str, baixar_historico: bool = False, meses_ignorados: set[str] = None) -> Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """
    Acessa a URL da Carteira Valor, faz o parse do HTML e extrai
    as recomendações de cada corretora.

    Args:
        url (str): URL base da página Carteira Valor.
        baixar_historico (bool): Se verdadeiro, baixa todos os meses a partir de Jan/2022.
        meses_ignorados (set[str], optional): Conjunto de meses (ex: '2023-01') que não devem ser baixados.

    Returns:
        Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]: 
            Se baixar_historico=False, retorna a lista de carteiras do mês atual.
            Se baixar_historico=True, retorna um dicionário { 'YYYY-MM': [carteiras...] }.
    """
    url_base = url.rstrip('/')
    meses_ignorados = meses_ignorados or set()

    if not baixar_historico:
        logger.info(f"Iniciando raspagem da página: {url}")
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req) as response:
                html = response.read()
        except Exception as e:
            logger.error(f"Erro ao acessar a URL {url}: {e}")
            return []

        carteiras = _extrair_html_para_carteiras(html)
        if not carteiras:
            logger.warning("Nenhuma corretora encontrada com a classe 'bx-corretoras'.")
        else:
            logger.info(f"Extraídas carteiras de {len(carteiras)} corretoras.")
        return carteiras

    # Lógica para baixar o histórico
    logger.info("Iniciando raspagem de histórico completo a partir de 2022-01.")
    historico_resultado: Dict[str, List[Dict[str, Any]]] = {}
    
    hoje = datetime.now(timezone.utc)
    ano_atual = hoje.year
    mes_atual = hoje.month

    for ano in range(2022, ano_atual + 1):
        for mes in range(1, 13):
            if ano == ano_atual and mes > mes_atual:
                break
                
            mes_str = f"{ano}-{mes:02d}"
            
            if mes_str in meses_ignorados:
                logger.info(f"[{mes_str}] Mês já presente no cache, pulando raspagem.")
                continue
            
            # Formata URL histórica ou base para o mês atual
            # Nota: O site suporta /historico/M/YYYY até para o mês atual,
            # mas vamos usar a URL montada.
            url_historico = f"{url_base}/historico/{mes}/{ano}"
            
            logger.debug(f"Acessando histórico {mes_str} na URL: {url_historico}")
            try:
                req = urllib.request.Request(
                    url_historico,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(req) as response:
                    html = response.read()
                    carteiras = _extrair_html_para_carteiras(html)
                    if carteiras:
                        historico_resultado[mes_str] = carteiras
                        logger.info(f"[{mes_str}] Extraídas carteiras de {len(carteiras)} corretoras.")
                    else:
                        logger.warning(f"[{mes_str}] Nenhuma carteira encontrada.")
            except Exception as e:
                logger.error(f"Erro ao acessar histórico {mes_str} ({url_historico}): {e}")
            
            # Pequeno delay para não sobrecarregar o servidor
            time.sleep(0.5)

    return historico_resultado
