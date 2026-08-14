import json

import pytest
from pytest_mock import MockerFixture

from src.extraction.llm_parser import estruturar_carteira


def test_estruturar_carteira_sucesso(mocker: MockerFixture) -> None:
    """Testa a função estruturar_carteira_sucesso.

    Args:
        mocker: Parâmetro de teste.

    Returns:
        None

    Raises:
        None
    """
    mock_post = mocker.patch("src.extraction.llm_parser.requests.post")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {
        "response": json.dumps([{"corretora": "XP", "tickers": ["PETR4"]}])
    }
    mock_post.return_value = mock_response
    res = estruturar_carteira("texto")
    assert len(res) == 1


def test_estruturar_carteira_formato_inesperado(mocker: MockerFixture) -> None:
    """Testa a função estruturar_carteira_formato_inesperado.

    Args:
        mocker: Parâmetro de teste.

    Returns:
        None

    Raises:
        None
    """
    mock_post = mocker.patch("src.extraction.llm_parser.requests.post")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"response": json.dumps(12345)}
    mock_post.return_value = mock_response
    res = estruturar_carteira("texto")
    assert res == []


def test_estruturar_carteira_api_timeout(mocker: MockerFixture) -> None:
    """Testa a função estruturar_carteira_api_timeout.

    Args:
        mocker: Parâmetro de teste.

    Returns:
        None

    Raises:
        None
    """
    import requests

    mocker.patch(
        "src.extraction.llm_parser.requests.post",
        side_effect=requests.exceptions.Timeout,
    )
    with pytest.raises(requests.exceptions.Timeout):
        estruturar_carteira("texto")


def test_estruturar_carteira_falha_json(mocker: MockerFixture) -> None:
    """Testa a função estruturar_carteira_falha_json.

    Args:
        mocker: Parâmetro de teste.

    Returns:
        None

    Raises:
        None
    """
    mock_post = mocker.patch("src.extraction.llm_parser.requests.post")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"response": "invalid json"}
    mock_post.return_value = mock_response
    with pytest.raises(json.JSONDecodeError):
        estruturar_carteira("texto")


def test_estruturar_carteira_texto_vazio(mocker: MockerFixture) -> None:
    """Testa a função estruturar_carteira_texto_vazio.

    Args:
        mocker: Parâmetro de teste.

    Returns:
        None

    Raises:
        None
    """
    mock_post = mocker.patch("src.extraction.llm_parser.requests.post")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"response": ""}
    mock_post.return_value = mock_response
    with pytest.raises(json.JSONDecodeError):
        estruturar_carteira("")


def test_estruturar_carteira_erro_conectar_ollama(mocker: MockerFixture) -> None:
    """Testa a função estruturar_carteira_erro_conectar_ollama.

    Args:
        mocker: Parâmetro de teste.

    Returns:
        None

    Raises:
        None
    """
    import requests

    mocker.patch(
        "src.extraction.llm_parser.requests.post",
        side_effect=requests.exceptions.ConnectionError,
    )
    with pytest.raises(requests.exceptions.ConnectionError):
        estruturar_carteira("texto")
