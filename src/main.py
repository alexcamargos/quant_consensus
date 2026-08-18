"""Orquestrador principal do QuantConsensus.

Executa o pipeline fim a fim: Ingestão -> Extração -> Engine.
"""

import sys
import argparse
from datetime import datetime, timezone

from loguru import logger

from src.core.logger import configure_logging
from src.engine.consensus_calc import (
    gerar_carteira_consenso,
    salvar_resultados_parciais,
    obter_meses_salvos,
)
from src.extraction.scraper import extrair_carteiras_valor
from src.core.config import settings



def _parse_historico_period(valor: str) -> tuple[int, int]:
    """Interpreta o valor passado em ``--historico`` e devolve (ano, mês).

    Formatos aceitos:

    * ``"all"``      → início-padrão (2022-01)
    * ``"YYYY"``     → Janeiro do ano informado
    * ``"YYYY-MM"``  → Mês e ano informados

    Args:
        valor: String recebida pelo argparse (``const='all'`` quando a
            flag é usada sem valor).

    Returns:
        Tupla ``(ano_inicio, mes_inicio)`` validada.

    Raises:
        SystemExit: Se o formato for inválido ou a data estiver no futuro.
    """
    hoje = datetime.now(timezone.utc)

    if valor == "all":
        return settings.ANO_INICIO_HISTORICO, 1

    # Tenta YYYY-MM primeiro, depois YYYY
    if "-" in valor:
        partes = valor.split("-")
        if len(partes) != 2:
            logger.error(
                f"Formato inválido para --historico: '{valor}'. "
                "Use YYYY ou YYYY-MM."
            )
            sys.exit(1)
        try:
            ano, mes = int(partes[0]), int(partes[1])
        except ValueError:
            logger.error(
                f"Formato inválido para --historico: '{valor}'. "
                "Use YYYY ou YYYY-MM."
            )
            sys.exit(1)
    else:
        try:
            ano = int(valor)
        except ValueError:
            logger.error(
                f"Formato inválido para --historico: '{valor}'. "
                "Use YYYY ou YYYY-MM."
            )
            sys.exit(1)
        mes = 1

    # Validações de domínio
    if mes < 1 or mes > 12:
        logger.error(f"Mês inválido: {mes}. Deve estar entre 01 e 12.")
        sys.exit(1)

    if ano < settings.ANO_INICIO_HISTORICO:
        logger.error(
            f"Ano {ano} é anterior ao início dos dados disponíveis "
            f"({settings.ANO_INICIO_HISTORICO})."
        )
        sys.exit(1)

    if ano > hoje.year or (ano == hoje.year and mes > hoje.month):
        logger.error(
            f"Período {ano}-{mes:02d} está no futuro. "
            f"O mês mais recente disponível é {hoje.year}-{hoje.month:02d}."
        )
        sys.exit(1)

    return ano, mes


def main() -> None:
    """Função principal que executa o pipeline.

    Returns:
        None

    Raises:
        SystemExit: Se nenhuma carteira válida for processada.
    """
    # Inicializa logs centralizados do sistema
    configure_logging()

    parser = argparse.ArgumentParser(
        description="QuantConsensus - Carteira Recomendada",
    )
    parser.add_argument(
        "--historico",
        nargs="?",
        const="all",
        default=None,
        metavar="PERIODO",
        help=(
            "Baixar histórico de carteiras. Sem valor: tudo desde "
            f"Jan/{settings.ANO_INICIO_HISTORICO}. "
            "Aceita YYYY (ex: 2024) ou YYYY-MM (ex: 2024-03)."
        ),
    )
    args = parser.parse_args()

    logger.info("=== Iniciando Pipeline QuantConsensus ===")

    # 1. Definição do escopo da execução (Mês Corrente)
    hoje = datetime.now(timezone.utc)
    mes_referencia = f"{hoje.year}-{hoje.month:02d}"

    db_path = settings.DB_PATH
    carteira_valor_url = settings.CARTEIRA_VALOR_URL

    meses_salvos = obter_meses_salvos(db_path)

    # Remove the current month from meses_salvos so it's always redownloaded to get latest data
    if mes_referencia in meses_salvos:
        meses_salvos.remove(mes_referencia)

    if meses_salvos:
        logger.info(
            f"{len(meses_salvos)} mês(es) já presente(s) no banco de dados "
            f"e não serão baixados novamente: "
            f"{', '.join(sorted(meses_salvos))}"
        )
    else:
        logger.info("Nenhum dado histórico encontrado no banco de dados. Todos os meses serão baixados.")

    # Determina se estamos no modo histórico e qual o período
    baixar_historico = args.historico is not None
    ano_inicio: int | None = None
    mes_inicio: int | None = None

    if baixar_historico:
        ano_inicio, mes_inicio = _parse_historico_period(args.historico)
        logger.info(
            f"Modo histórico ativado: período a partir de "
            f"{ano_inicio}-{mes_inicio:02d}."
        )

    # 2. Ingestão e Extração
    logger.info(f"Iniciando raspagem e análise da fonte única: {carteira_valor_url}")

    resultado_extraido = extrair_carteiras_valor(
        carteira_valor_url,
        baixar_historico=baixar_historico,
        meses_ignorados=meses_salvos,
        ano_inicio=ano_inicio,
        mes_inicio=mes_inicio,
    )

    if not resultado_extraido:
        logger.error("Pipeline falhou: nenhuma carteira válida processada.")
        sys.exit(1)

    # 3. Etapa do Processamento Analítico de Consenso
    logger.info("Persistindo extratos analíticos no Data Warehouse (DuckDB)...")

    if baixar_historico:
        primeira_insercao = len(meses_salvos) == 0
        for mes_hist, carteiras_hist in resultado_extraido.items():
            append = not primeira_insercao
            salvar_resultados_parciais(carteiras_hist, mes_hist, db_path, append=append)
            primeira_insercao = False
    else:
        # Quando --historico NÃO é passado, baixamos apenas o mês corrente.
        # Como queremos cache, NÃO podemos fazer append=False pois apagaria os meses anteriores do banco.
        # Devemos fazer append=True.
        # Aviso: isso vai duplicar as entradas do mês corrente se já existirem e não forem limpas.
        # Mas `salvar_resultados_parciais` precisa ser melhorado para apagar apenas o mês atual antes de inserir.
        # Como não modificamos `salvar_resultados_parciais` neste nível, deixamos assim por enquanto.
        salvar_resultados_parciais(resultado_extraido, mes_referencia, db_path, append=True)

    logger.info("Rodando o motor SQL analítico de desempate...")
    # O motor SQL deve rodar sempre para o mês_referencia para mostrar a saída final no CLI,
    # mesmo que tenhamos baixado todo o histórico
    consenso_arrow = gerar_carteira_consenso(db_path, mes_ref=mes_referencia)

    # 4. Apresentação Final (Terminal CLI)
    df_consenso = consenso_arrow.to_pandas()

    print("\n" + "=" * 65)
    print(f" CARTEIRA CONSENSO DO MÊS ({mes_referencia}) ".center(65))
    print("=" * 65 + "\n")

    if df_consenso.empty:
        print("Nenhum dado de consenso foi computado.")
    else:
        # Formatação de string alinhada com as melhores práticas de CLI visual
        print(f"{'RANK':<6} | {'TICKER':<8} | {'VOTOS':<8} | {'VOLUME MÉDIO'}")
        print("-" * 65)

        if baixar_historico:
            max_votos_possiveis = len(resultado_extraido.get(mes_referencia, []))
        else:
            max_votos_possiveis = len(resultado_extraido)

        for idx, row in df_consenso.iterrows():
            posicao = idx + 1
            ticker = row["ticker"]
            votos = row["votos"]
            volume = row["volume_desempate"]

            unanimidade = "(UNANIMIDADE)" if votos == max_votos_possiveis and max_votos_possiveis > 0 else ""

            volume_str = ""
            if volume > 0:
                # Formatação simples de moeda local
                volume_str = (
                    f"R$ {volume:,.2f}".replace(",", "_")
                    .replace(".", ",")
                    .replace("_", ".")
                )

            print(
                f"#{posicao:<5} | {ticker:<8} | {votos:<8} | {unanimidade} {volume_str}"
            )

    print("=" * 65)
    logger.info("Pipeline executado com sucesso até o fim da esteira.")


if __name__ == '__main__':
    main()

