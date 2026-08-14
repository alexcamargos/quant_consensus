"""Módulo central para configuração do Loguru."""

import sys

from loguru import logger


def configure_logging() -> None:
    """Configura o logger global do Loguru aplicando as melhores práticas.

    - Remove o handler padrão para evitar logs duplicados.
    - Configura um handler para stdout com cores e um formato detalhado (thread-safe).
    - Configura um handler de arquivo para retenção, com rotação automática,
      compressão, backtraces completos de exceções (ótimo para Data Engineering).
    """
    logger.remove()  # Remove o handler padrão

    # Formato padrão otimizado e bem estruturado
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    # Handler para o Console (stdout)
    logger.add(
        sys.stdout,
        format=log_format,
        level="INFO",
        colorize=True,
        enqueue=True,  # Garante thread-safety em execuções assíncronas/multithread
    )

    # Handler para Arquivo (rotação de 10MB, mantém por 30 dias, comprime os antigos)
    logger.add(
        "logs/quant_consensus_{time:YYYY-MM-DD}.log",
        format=log_format,
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True,
        backtrace=True,  # Mostra o trace completo de erros (incluindo variáveis)
        diagnose=True,  # Expande o escopo de diagnóstico em exceptions
    )
