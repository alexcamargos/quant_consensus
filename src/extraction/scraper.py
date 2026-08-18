"""Módulo para raspagem direta da página Carteira Valor."""

import time
from typing import Any, Dict, List, Union

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from loguru import logger

from src.core.config import settings

def _extrair_html_para_carteiras(html: bytes) -> List[Dict[str, Any]]:
    """Função auxiliar para fazer o parse do HTML e extrair as carteiras.

    Args:
        html: Conteúdo HTML em bytes da página raspada.

    Returns:
        Lista de dicionários com chaves ``corretora`` e ``tickers``.
    """
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


def extrair_carteiras_valor(
    url: str,
    baixar_historico: bool = False,
    meses_ignorados: set[str] | None = None,
    ano_inicio: int | None = None,
    mes_inicio: int | None = None,
) -> Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """Acessa a URL da Carteira Valor, faz o parse do HTML e extrai
    as recomendações de cada corretora.

    Utiliza ``requests.Session`` para reutilizar conexões TCP/TLS
    (keep-alive), reduzindo significativamente a latência ao fazer
    múltiplas requisições sequenciais ao mesmo host.

    Args:
        url: URL base da página Carteira Valor.
        baixar_historico: Se verdadeiro, baixa meses históricos.
        meses_ignorados: Conjunto de meses (ex: ``'2023-01'``) que não
            devem ser baixados (cache).
        ano_inicio: Ano a partir do qual baixar o histórico.
            Padrão: ``2022``.
        mes_inicio: Mês a partir do qual baixar o histórico (1-12).
            Padrão: ``1`` (janeiro).

    Returns:
        Se ``baixar_historico=False``, retorna a lista de carteiras do
        mês atual.  Se ``baixar_historico=True``, retorna um dicionário
        ``{ 'YYYY-MM': [carteiras...] }``.
    """
    url_base = url.rstrip('/')
    meses_ignorados = meses_ignorados or set()

    with requests.Session() as session:
        session.headers.update(settings.DEFAULT_HEADERS)

        if not baixar_historico:
            logger.info(f"Iniciando raspagem da página: {url}")
            try:
                response = session.get(url, timeout=settings.REQUEST_TIMEOUT)
                response.raise_for_status()
            except requests.RequestException as e:
                logger.error(f"Erro ao acessar a URL {url}: {e}")
                return []

            carteiras = _extrair_html_para_carteiras(response.content)
            if not carteiras:
                logger.warning("Nenhuma corretora encontrada com a classe 'bx-corretoras'.")
            else:
                logger.info(f"Extraídas carteiras de {len(carteiras)} corretoras.")
            return carteiras

        # Lógica para baixar o histórico
        ano_ini = ano_inicio if ano_inicio is not None else settings.ANO_INICIO_HISTORICO
        mes_ini = mes_inicio if mes_inicio is not None else 1

        logger.info(
            f"Iniciando raspagem de histórico a partir de {ano_ini}-{mes_ini:02d}."
        )
        historico_resultado: Dict[str, List[Dict[str, Any]]] = {}

        hoje = datetime.now(timezone.utc)
        ano_atual = hoje.year
        mes_atual = hoje.month

        for ano in range(ano_ini, ano_atual + 1):
            primeiro_mes = mes_ini if ano == ano_ini else 1
            for mes in range(primeiro_mes, 13):
                if ano == ano_atual and mes > mes_atual:
                    break

                mes_str = f"{ano}-{mes:02d}"

                if mes_str in meses_ignorados:
                    logger.info(f"[{mes_str}] Mês já presente no cache, pulando raspagem.")
                    continue

                # Formata URL histórica
                url_historico = f"{url_base}/historico/{mes}/{ano}"

                logger.debug(f"Acessando histórico {mes_str} na URL: {url_historico}")
                try:
                    response = session.get(url_historico, timeout=settings.REQUEST_TIMEOUT)
                    response.raise_for_status()
                    carteiras = _extrair_html_para_carteiras(response.content)
                    if carteiras:
                        historico_resultado[mes_str] = carteiras
                        logger.info(f"[{mes_str}] Extraídas carteiras de {len(carteiras)} corretoras.")
                    else:
                        logger.warning(f"[{mes_str}] Nenhuma carteira encontrada.")
                except requests.RequestException as e:
                    logger.error(f"Erro ao acessar histórico {mes_str} ({url_historico}): {e}")

                # Pequeno delay para não sobrecarregar o servidor
                time.sleep(0.5)

    return historico_resultado


