"""Testes unitários para o módulo extraction.scraper."""

from unittest import mock

import pytest
import requests
from pytest_mock import MockerFixture

from src.extraction.scraper import _extrair_html_para_carteiras, extrair_carteiras_valor

# HTMLs de teste
HTML_VALIDO = b"""
<html>
  <body>
    <div class="bx-corretoras" data-name="XP">
      <table>
        <tbody>
          <tr>
            <td>Acao</td>
            <td>PETR4</td>
          </tr>
          <tr>
            <td>Acao</td>
            <td>VALE3</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="bx-corretoras" data-name="BTG">
      <table>
        <tbody>
          <tr>
            <td>Acao</td>
            <td>WEGE3</td>
          </tr>
        </tbody>
      </table>
    </div>
  </body>
</html>
"""

HTML_SEM_CORRETORAS = b"<html><body><div>Sem carteira aqui</div></body></html>"

HTML_SEM_TBODY = b"""
<html>
  <body>
    <div class="bx-corretoras" data-name="XP">
      <table></table>
    </div>
  </body>
</html>
"""

HTML_TD_INSUFICIENTE = b"""
<html>
  <body>
    <div class="bx-corretoras" data-name="XP">
      <table>
        <tbody>
          <tr>
            <td>Acao</td>
          </tr>
        </tbody>
      </table>
    </div>
  </body>
</html>
"""

HTML_TICKER_VAZIO = b"""
<html>
  <body>
    <div class="bx-corretoras" data-name="XP">
      <table>
        <tbody>
          <tr>
            <td>Acao</td>
            <td>   </td>
          </tr>
        </tbody>
      </table>
    </div>
  </body>
</html>
"""


def test_extrair_html_para_carteiras_sucesso() -> None:
    """Verifica a extração correta de carteiras e corretoras do HTML."""
    carteiras = _extrair_html_para_carteiras(HTML_VALIDO)
    
    assert len(carteiras) == 2
    assert carteiras[0]["corretora"] == "XP"
    assert carteiras[0]["tickers"] == ["PETR4", "VALE3"]
    assert carteiras[1]["corretora"] == "BTG"
    assert carteiras[1]["tickers"] == ["WEGE3"]


def test_extrair_html_para_carteiras_sem_divs() -> None:
    """Verifica comportamento quando não há divs com classe bx-corretoras."""
    carteiras = _extrair_html_para_carteiras(HTML_SEM_CORRETORAS)
    assert carteiras == []


def test_extrair_html_para_carteiras_sem_tbody() -> None:
    """Verifica comportamento quando a div bx-corretoras não tem tbody."""
    carteiras = _extrair_html_para_carteiras(HTML_SEM_TBODY)
    assert carteiras == []


def test_extrair_html_para_carteiras_td_insuficiente() -> None:
    """Verifica comportamento quando há menos de 2 tds na linha."""
    carteiras = _extrair_html_para_carteiras(HTML_TD_INSUFICIENTE)
    assert carteiras == []


def test_extrair_html_para_carteiras_ticker_vazio() -> None:
    """Verifica comportamento quando o texto do ticker é vazio."""
    carteiras = _extrair_html_para_carteiras(HTML_TICKER_VAZIO)
    assert carteiras == []


def test_extrair_html_para_carteiras_sem_data_name() -> None:
    """Verifica fallback para 'Desconhecida' quando data-name está ausente."""
    html = b"""<div class="bx-corretoras"><tbody><tr><td>A</td><td>PETR4</td></tr></tbody></div>"""
    carteiras = _extrair_html_para_carteiras(html)
    assert carteiras[0]["corretora"] == "Desconhecida"


@pytest.fixture
def mock_session(mocker: MockerFixture) -> mock.MagicMock:
    """Cria um mock para o requests.Session()."""
    session_mock = mocker.MagicMock()
    mocker.patch("src.extraction.scraper.requests.Session", return_value=session_mock)
    session_mock.__enter__.return_value = session_mock
    return session_mock


def test_extrair_carteiras_valor_sucesso(mock_session: mock.MagicMock) -> None:
    """Verifica download bem sucedido de um mês único (não-histórico)."""
    response_mock = mock.MagicMock()
    response_mock.content = HTML_VALIDO
    mock_session.get.return_value = response_mock
    
    res = extrair_carteiras_valor("http://test.com")
    assert len(res) == 2
    assert res[0]["corretora"] == "XP"


def test_extrair_carteiras_valor_sem_carteiras(mock_session: mock.MagicMock) -> None:
    """Verifica comportamento quando o HTML da página não tem carteiras."""
    response_mock = mock.MagicMock()
    response_mock.content = HTML_SEM_CORRETORAS
    mock_session.get.return_value = response_mock
    
    res = extrair_carteiras_valor("http://test.com")
    assert res == []


def test_extrair_carteiras_valor_erro_http(mock_session: mock.MagicMock) -> None:
    """Verifica tratamento de exceção RequestException."""
    mock_session.get.side_effect = requests.RequestException("Timeout")
    
    res = extrair_carteiras_valor("http://test.com")
    assert res == []


@mock.patch("src.extraction.scraper.time.sleep", return_value=None)
@mock.patch("src.extraction.scraper.datetime")
def test_extrair_carteiras_valor_historico(
    mock_datetime: mock.MagicMock, mock_sleep: mock.MagicMock, mock_session: mock.MagicMock
) -> None:
    """Verifica download histórico (iterando meses)."""
    from datetime import datetime, timezone
    
    # Mock date to be Jan 2023, downloading from 2023-01 to 2023-01
    mock_now = datetime(2023, 1, 15, tzinfo=timezone.utc)
    mock_datetime.now.return_value = mock_now
    
    response_mock = mock.MagicMock()
    response_mock.content = HTML_VALIDO
    mock_session.get.return_value = response_mock
    
    res = extrair_carteiras_valor(
        "http://test.com", baixar_historico=True, ano_inicio=2023, mes_inicio=1
    )
    
    # Deve conter a chave '2023-01'
    assert "2023-01" in res
    assert len(res["2023-01"]) == 2
    
    # Verifica a url chamada
    mock_session.get.assert_called_once_with("http://test.com/historico/1/2023", timeout=15)


@mock.patch("src.extraction.scraper.datetime")
def test_extrair_carteiras_valor_historico_com_cache(
    mock_datetime: mock.MagicMock, mock_session: mock.MagicMock
) -> None:
    """Verifica que pula meses ignorados."""
    from datetime import datetime, timezone
    mock_now = datetime(2023, 1, 15, tzinfo=timezone.utc)
    mock_datetime.now.return_value = mock_now
    
    res = extrair_carteiras_valor(
        "http://test.com", 
        baixar_historico=True, 
        meses_ignorados={"2023-01"},
        ano_inicio=2023, 
        mes_inicio=1
    )
    
    # Deve retornar dicionário vazio pois 2023-01 estava no cache (ignorado)
    assert res == {}
    mock_session.get.assert_not_called()


@mock.patch("src.extraction.scraper.time.sleep", return_value=None)
@mock.patch("src.extraction.scraper.datetime")
def test_extrair_carteiras_valor_historico_erro(
    mock_datetime: mock.MagicMock, mock_sleep: mock.MagicMock, mock_session: mock.MagicMock
) -> None:
    """Verifica que ignora erros de HTTP durante o download do histórico e continua."""
    from datetime import datetime, timezone
    mock_now = datetime(2023, 1, 15, tzinfo=timezone.utc)
    mock_datetime.now.return_value = mock_now
    
    mock_session.get.side_effect = requests.RequestException("Erro HTTP")
    
    res = extrair_carteiras_valor(
        "http://test.com", baixar_historico=True, ano_inicio=2023, mes_inicio=1
    )
    
    # O mês não foi adicionado pois deu erro
    assert "2023-01" not in res
    assert res == {}


@mock.patch("src.extraction.scraper.time.sleep", return_value=None)
@mock.patch("src.extraction.scraper.datetime")
def test_extrair_carteiras_valor_historico_sem_carteiras(
    mock_datetime: mock.MagicMock, mock_sleep: mock.MagicMock, mock_session: mock.MagicMock
) -> None:
    """Verifica quando HTML histórico não possui carteiras."""
    from datetime import datetime, timezone
    mock_now = datetime(2023, 1, 15, tzinfo=timezone.utc)
    mock_datetime.now.return_value = mock_now
    
    response_mock = mock.MagicMock()
    response_mock.content = HTML_SEM_CORRETORAS
    mock_session.get.return_value = response_mock
    
    res = extrair_carteiras_valor(
        "http://test.com", baixar_historico=True, ano_inicio=2023, mes_inicio=1
    )
    
    assert "2023-01" not in res
