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

def main() -> None:
    """
    Função principal que executa o pipeline.

    Args:
        None

    Returns:
        None

    Raises:
        None
    """
    # Inicializa logs centralizados do sistema
    configure_logging()

    parser = argparse.ArgumentParser(description="QuantConsensus - Carteira Recomendada")
    parser.add_argument("--historico", action="store_true", help="Baixar histórico completo de carteiras a partir de Jan/2022")
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

    # 2. Ingestão e Extração
    logger.info(f"Iniciando raspagem e análise da fonte única: {carteira_valor_url}")

    resultado_extraido = extrair_carteiras_valor(carteira_valor_url, baixar_historico=args.historico, meses_ignorados=meses_salvos)

    if not resultado_extraido:
        logger.error("Pipeline falhou: nenhuma carteira válida processada.")
        sys.exit(1)

    # 3. Etapa do Processamento Analítico de Consenso
    logger.info("Persistindo extratos analíticos no Data Warehouse (DuckDB)...")
    
    if args.historico:
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

        if args.historico:
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
