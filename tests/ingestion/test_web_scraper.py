"""Testes unitários para o módulo ingestion.web_scraper."""

from pytest_mock import MockerFixture

from src.ingestion.web_scraper import extrair_texto


def test_extrair_texto_download_sucesso(mocker: MockerFixture) -> None:
    """Verifica fluxo principal de sucesso com o trafilatura."""
    mock_fetch = mocker.patch("src.ingestion.web_scraper.trafilatura.fetch_url")
    mock_extract = mocker.patch("src.ingestion.web_scraper.trafilatura.extract")
    
    mock_fetch.return_value = "<html>dados brutos</html>"
    mock_extract.return_value = "Texto extraído corretamente"
    
    resultado = extrair_texto("http://site.com")
    
    assert resultado == "Texto extraído corretamente"
    mock_fetch.assert_called_once_with("http://site.com")
    mock_extract.assert_called_once_with(
        "<html>dados brutos</html>", 
        include_links=False, 
        include_images=False, 
        include_comments=False
    )


def test_extrair_texto_download_falha(mocker: MockerFixture) -> None:
    """Verifica se retorna o mock quando falha o download."""
    mock_fetch = mocker.patch("src.ingestion.web_scraper.trafilatura.fetch_url")
    mock_extract = mocker.patch("src.ingestion.web_scraper.trafilatura.extract")
    
    # fetch falha
    mock_fetch.return_value = None
    
    resultado = extrair_texto("http://site-falho.com")
    
    # Deve retornar o texto de mock fixo contendo os nomes das corretoras
    assert resultado is not None
    assert "XP Investimentos" in resultado
    assert "VALE3" in resultado
    
    # Não deve chamar o extract
    mock_extract.assert_not_called()


def test_extrair_texto_sem_conteudo(mocker: MockerFixture) -> None:
    """Verifica se retorna None quando não consegue extrair texto da página."""
    mock_fetch = mocker.patch("src.ingestion.web_scraper.trafilatura.fetch_url")
    mock_extract = mocker.patch("src.ingestion.web_scraper.trafilatura.extract")
    
    mock_fetch.return_value = "<html><!-- nada útil --></html>"
    # extract falha
    mock_extract.return_value = None
    
    resultado = extrair_texto("http://site-vazio.com")
    
    assert resultado is None
