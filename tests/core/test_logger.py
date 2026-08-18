"""Testes unitários para o módulo core.logger."""

import sys

from loguru import logger
from pytest_mock import MockerFixture

from src.core.logger import configure_logging


def test_configure_logging(mocker: MockerFixture) -> None:
    """Verifica se a configuração de log limpa handlers padrão e adiciona os novos."""
    # Mock para verificar as chamadas de logger.remove e logger.add
    mock_remove = mocker.patch.object(logger, "remove")
    mock_add = mocker.patch.object(logger, "add")
    
    configure_logging()
    
    # Verifica se o handler padrão foi removido
    mock_remove.assert_called_once_with()
    
    # Verifica se adicionou handlers (stdout e arquivo)
    assert mock_add.call_count == 2
    
    # Verifica parâmetros principais da primeira chamada (stdout)
    args_stdout, kwargs_stdout = mock_add.call_args_list[0]
    assert args_stdout[0] == sys.stdout
    assert kwargs_stdout["level"] == "INFO"
    assert kwargs_stdout["enqueue"] is True
    
    # Verifica parâmetros principais da segunda chamada (arquivo)
    args_file, kwargs_file = mock_add.call_args_list[1]
    assert "logs/quant_consensus_{time:YYYY-MM-DD}.log" in args_file[0]
    assert kwargs_file["level"] == "DEBUG"
    assert kwargs_file["rotation"] == "10 MB"
    assert kwargs_file["retention"] == "30 days"
    assert kwargs_file["compression"] == "zip"
    assert kwargs_file["backtrace"] is True
