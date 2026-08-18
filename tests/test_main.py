"""Testes unitários para o orquestrador principal."""

import sys
from unittest import mock

import pytest
from pytest_mock import MockerFixture

from src.main import _parse_historico_period, main
import pyarrow as pa
import pandas as pd


# --------------------- Testes de _parse_historico_period --------------------- #

@mock.patch("src.main.datetime")
def test_parse_historico_all(mock_datetime: mock.MagicMock) -> None:
    """Verifica o parse de 'all'."""
    from datetime import datetime, timezone
    mock_datetime.now.return_value = datetime(2024, 5, 1, tzinfo=timezone.utc)
    
    ano, mes = _parse_historico_period("all")
    assert ano == 2022  # Valor do setting ANO_INICIO_HISTORICO
    assert mes == 1


@mock.patch("src.main.datetime")
def test_parse_historico_ano(mock_datetime: mock.MagicMock) -> None:
    """Verifica parse de string de ano (ex: '2023')."""
    from datetime import datetime, timezone
    mock_datetime.now.return_value = datetime(2024, 5, 1, tzinfo=timezone.utc)
    
    ano, mes = _parse_historico_period("2023")
    assert ano == 2023
    assert mes == 1


@mock.patch("src.main.datetime")
def test_parse_historico_ano_mes(mock_datetime: mock.MagicMock) -> None:
    """Verifica parse de string YYYY-MM (ex: '2023-05')."""
    from datetime import datetime, timezone
    mock_datetime.now.return_value = datetime(2024, 5, 1, tzinfo=timezone.utc)
    
    ano, mes = _parse_historico_period("2023-05")
    assert ano == 2023
    assert mes == 5


@mock.patch("src.main.datetime")
def test_parse_historico_formato_invalido(mock_datetime: mock.MagicMock, mocker: MockerFixture) -> None:
    """Verifica string mal formatada, ex: abc."""
    from datetime import datetime, timezone
    mock_datetime.now.return_value = datetime(2024, 5, 1, tzinfo=timezone.utc)
    mock_logger = mocker.patch("src.main.logger")
    
    with pytest.raises(SystemExit) as e:
        _parse_historico_period("abc")
    assert e.value.code == 1
    mock_logger.error.assert_called_with("Formato inválido para --historico: 'abc'. Use YYYY ou YYYY-MM.")


@mock.patch("src.main.datetime")
def test_parse_historico_formato_invalido_hifen(mock_datetime: mock.MagicMock, mocker: MockerFixture) -> None:
    """Verifica string mal formatada com hífen, ex: abc-def."""
    from datetime import datetime, timezone
    mock_datetime.now.return_value = datetime(2024, 5, 1, tzinfo=timezone.utc)
    mock_logger = mocker.patch("src.main.logger")
    
    with pytest.raises(SystemExit) as e:
        _parse_historico_period("abc-def")
    assert e.value.code == 1
    assert mock_logger.error.called


@mock.patch("src.main.datetime")
def test_parse_historico_formato_multi_hifen(mock_datetime: mock.MagicMock, mocker: MockerFixture) -> None:
    """Verifica string com hifens em excesso."""
    from datetime import datetime, timezone
    mock_datetime.now.return_value = datetime(2024, 5, 1, tzinfo=timezone.utc)
    mock_logger = mocker.patch("src.main.logger")
    
    with pytest.raises(SystemExit) as e:
        _parse_historico_period("2023-01-01")
    assert e.value.code == 1
    assert mock_logger.error.called


@mock.patch("src.main.datetime")
def test_parse_historico_mes_invalido(mock_datetime: mock.MagicMock, mocker: MockerFixture) -> None:
    """Verifica mês fora do limite 1-12."""
    from datetime import datetime, timezone
    mock_datetime.now.return_value = datetime(2024, 5, 1, tzinfo=timezone.utc)
    mock_logger = mocker.patch("src.main.logger")
    
    with pytest.raises(SystemExit) as e:
        _parse_historico_period("2023-13")
    assert e.value.code == 1
    assert mock_logger.error.called


@mock.patch("src.main.datetime")
def test_parse_historico_ano_anterior(mock_datetime: mock.MagicMock, mocker: MockerFixture) -> None:
    """Verifica ano antes do histórico (2021)."""
    from datetime import datetime, timezone
    mock_datetime.now.return_value = datetime(2024, 5, 1, tzinfo=timezone.utc)
    mock_logger = mocker.patch("src.main.logger")
    
    with pytest.raises(SystemExit) as e:
        _parse_historico_period("2021-05")
    assert e.value.code == 1
    assert mock_logger.error.called


@mock.patch("src.main.datetime")
def test_parse_historico_futuro(mock_datetime: mock.MagicMock, mocker: MockerFixture) -> None:
    """Verifica período futuro."""
    from datetime import datetime, timezone
    mock_datetime.now.return_value = datetime(2024, 5, 1, tzinfo=timezone.utc)
    mock_logger = mocker.patch("src.main.logger")
    
    with pytest.raises(SystemExit) as e:
        _parse_historico_period("2024-06")
    assert e.value.code == 1
    assert mock_logger.error.called


# --------------------- Testes de main() --------------------- #

def create_mock_arrow_table(empty=False, no_volume=False):
    """Cria tabela dummy no formato pyarrow."""
    if empty:
        return pa.Table.from_pandas(pd.DataFrame())
    
    if no_volume:
        data = {
            "ticker": ["VALE3"],
            "votos": [1],
            "volume_desempate": [0]
        }
    else:
        data = {
            "ticker": ["PETR4", "VALE3"],
            "votos": [2, 1],
            "volume_desempate": [1500000000, 1200000000]
        }
    return pa.Table.from_pandas(pd.DataFrame(data))


@mock.patch("src.main.datetime")
def test_main_sem_historico(mock_datetime: mock.MagicMock, mocker: MockerFixture) -> None:
    """Testa a execução padrão (sem flag --historico)."""
    from datetime import datetime, timezone
    mock_datetime.now.return_value = datetime(2024, 5, 1, tzinfo=timezone.utc)
    
    mocker.patch("src.main.argparse.ArgumentParser.parse_args", return_value=mock.MagicMock(historico=None))
    mocker.patch("src.main.configure_logging")
    mocker.patch("src.main.obter_meses_salvos", return_value=set())
    
    mock_extrair = mocker.patch("src.main.extrair_carteiras_valor")
    mock_extrair.return_value = [{"corretora": "XP", "tickers": ["PETR4"]}]
    
    mock_salvar = mocker.patch("src.main.salvar_resultados_parciais")
    
    mock_gerar = mocker.patch("src.main.gerar_carteira_consenso")
    mock_gerar.return_value = create_mock_arrow_table()
    
    main()
    
    # Verifica chamadas corretas
    mock_extrair.assert_called_once_with(
        mock.ANY, baixar_historico=False, meses_ignorados=set(), ano_inicio=None, mes_inicio=None
    )
    mock_salvar.assert_called_once_with(
        [{"corretora": "XP", "tickers": ["PETR4"]}], "2024-05", mock.ANY, append=True
    )
    mock_gerar.assert_called_once_with(mock.ANY, mes_ref="2024-05")


@mock.patch("src.main.datetime")
def test_main_com_historico(mock_datetime: mock.MagicMock, mocker: MockerFixture) -> None:
    """Testa a execução com flag --historico."""
    from datetime import datetime, timezone
    mock_datetime.now.return_value = datetime(2024, 5, 1, tzinfo=timezone.utc)
    
    mocker.patch("src.main.argparse.ArgumentParser.parse_args", return_value=mock.MagicMock(historico="all"))
    mocker.patch("src.main.configure_logging")
    mocker.patch("src.main.obter_meses_salvos", return_value=set())
    
    mock_extrair = mocker.patch("src.main.extrair_carteiras_valor")
    mock_extrair.return_value = {"2024-05": [{"corretora": "XP", "tickers": ["PETR4"]}]}
    
    mock_salvar = mocker.patch("src.main.salvar_resultados_parciais")
    
    mock_gerar = mocker.patch("src.main.gerar_carteira_consenso")
    mock_gerar.return_value = create_mock_arrow_table()
    
    main()
    
    # Verifica chamadas para o modo histórico
    mock_extrair.assert_called_once()
    assert mock_salvar.call_count == 1
    mock_gerar.assert_called_once_with(mock.ANY, mes_ref="2024-05")


@mock.patch("src.main.datetime")
def test_main_com_meses_salvos(mock_datetime: mock.MagicMock, mocker: MockerFixture) -> None:
    """Testa quando já existem meses salvos (testando log e exclusão do mês atual)."""
    from datetime import datetime, timezone
    mock_datetime.now.return_value = datetime(2024, 5, 1, tzinfo=timezone.utc)
    
    mocker.patch("src.main.argparse.ArgumentParser.parse_args", return_value=mock.MagicMock(historico="all"))
    mocker.patch("src.main.configure_logging")
    # Retorna o mês corrente também. O main deve remover o mês corrente do set
    mocker.patch("src.main.obter_meses_salvos", return_value={"2024-04", "2024-05"})
    
    mock_extrair = mocker.patch("src.main.extrair_carteiras_valor")
    mock_extrair.return_value = {"2024-05": [{"corretora": "XP", "tickers": ["PETR4"]}]}
    
    mock_salvar = mocker.patch("src.main.salvar_resultados_parciais")
    mock_gerar = mocker.patch("src.main.gerar_carteira_consenso")
    mock_gerar.return_value = create_mock_arrow_table()
    
    main()
    
    # O mock extrair deve ser chamado passando meses ignorados apenas com "2024-04" 
    # (porque 2024-05 foi removido localmente)
    mock_extrair.assert_called_once_with(
        mock.ANY, baixar_historico=True, meses_ignorados={"2024-04"}, ano_inicio=2022, mes_inicio=1
    )


@mock.patch("src.main.datetime")
def test_main_sem_resultado(mock_datetime: mock.MagicMock, mocker: MockerFixture) -> None:
    """Testa encerramento precoce quando a extração falha/retorna vazio."""
    from datetime import datetime, timezone
    mock_datetime.now.return_value = datetime(2024, 5, 1, tzinfo=timezone.utc)
    
    mocker.patch("src.main.argparse.ArgumentParser.parse_args", return_value=mock.MagicMock(historico=None))
    mocker.patch("src.main.configure_logging")
    mocker.patch("src.main.obter_meses_salvos", return_value=set())
    mock_logger = mocker.patch("src.main.logger")
    
    # Extração não retornou dados
    mock_extrair = mocker.patch("src.main.extrair_carteiras_valor")
    mock_extrair.return_value = []
    
    with pytest.raises(SystemExit) as e:
        main()
        
    assert e.value.code == 1
    mock_logger.error.assert_called_with("Pipeline falhou: nenhuma carteira válida processada.")


@mock.patch("src.main.datetime")
def test_main_consenso_vazio(mock_datetime: mock.MagicMock, mocker: MockerFixture, capsys: pytest.CaptureFixture) -> None:
    """Verifica a visualização via terminal quando a engine retorna uma tabela vazia."""
    from datetime import datetime, timezone
    mock_datetime.now.return_value = datetime(2024, 5, 1, tzinfo=timezone.utc)
    
    mocker.patch("src.main.argparse.ArgumentParser.parse_args", return_value=mock.MagicMock(historico=None))
    mocker.patch("src.main.configure_logging")
    mocker.patch("src.main.obter_meses_salvos", return_value=set())
    mocker.patch("src.main.extrair_carteiras_valor", return_value=[{"corretora": "XP", "tickers": ["PETR4"]}])
    mocker.patch("src.main.salvar_resultados_parciais")
    
    # Retorna DataFrame vazio
    mock_gerar = mocker.patch("src.main.gerar_carteira_consenso")
    mock_gerar.return_value = create_mock_arrow_table(empty=True)
    
    main()
    
    captured = capsys.readouterr()
    assert "Nenhum dado de consenso foi computado" in captured.out


@mock.patch("src.main.datetime")
def test_main_com_volume_zero(mock_datetime: mock.MagicMock, mocker: MockerFixture, capsys: pytest.CaptureFixture) -> None:
    """Verifica a visualização no terminal de um ativo que não possui volume no DB."""
    from datetime import datetime, timezone
    mock_datetime.now.return_value = datetime(2024, 5, 1, tzinfo=timezone.utc)
    
    mocker.patch("src.main.argparse.ArgumentParser.parse_args", return_value=mock.MagicMock(historico=None))
    mocker.patch("src.main.configure_logging")
    mocker.patch("src.main.obter_meses_salvos", return_value=set())
    mocker.patch("src.main.extrair_carteiras_valor", return_value=[{"corretora": "XP", "tickers": ["VALE3"]}])
    mocker.patch("src.main.salvar_resultados_parciais")
    
    mock_gerar = mocker.patch("src.main.gerar_carteira_consenso")
    mock_gerar.return_value = create_mock_arrow_table(no_volume=True)
    
    main()
    
    captured = capsys.readouterr()
    assert "VALE3" in captured.out
    assert "(UNANIMIDADE)" in captured.out
