"""Contratos HTTP. Tipos de entrada são Any de propósito (ver ClassifyRequest)."""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ClassifyRequest(BaseModel):
    """Exige as quatro chaves e nega extras, sem coagir valores.

    Pydantic em modo normal converteria "5" em 5, contornando o contrato. Os
    valores seguem intactos para ``InputValidator``, única fonte das regras.
    """
    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra={'examples': [
            {'mes': 5, 'dia_semana': 2, 'tipo_local': 'VIA PÚBLICA', 'bairro': 'BELA VISTA'},
        ]},
    )
    mes: Any = Field(description='Inteiro de 1 a 12.')
    dia_semana: Any = Field(description='Inteiro de 0 (segunda) a 6 (domingo).')
    tipo_local: Any = Field(description='Valor de /api/options ou null para ausência explícita.')
    bairro: Any = Field(description='Valor de /api/options ou null para ausência explícita.')


class Mensagem(BaseModel):
    campo: str
    codigo: str
    mensagem: str


class Scores(BaseModel):
    furto: float = Field(ge=0, le=1)
    roubo: float = Field(ge=0, le=1)


class ClassificacaoOk(BaseModel):
    status: Literal['ok']
    classe_estimada: Literal['FURTO', 'ROUBO']
    codigo_classe: Literal[0, 1]
    scores_sigmoid: Scores
    versao_modelo: str
    versao_contrato: str
    probabilidades_calibradas: Literal[False]
    avisos: list[Mensagem]
    erros: list[Mensagem]
    grupos: dict[str, str]
    interpretacao_scores: str


class ClassificacaoErro(BaseModel):
    status: Literal['erro_validacao']
    versao_modelo: str
    versao_contrato: str
    probabilidades_calibradas: Literal[False]
    erros: list[Mensagem]
    avisos: list[Mensagem]
    grupos: dict[str, str]


class ErroServico(BaseModel):
    status: Literal['servico_indisponivel', 'limite_excedido', 'requisicao_grande']
    mensagem: str


class Saude(BaseModel):
    status: Literal['ok', 'indisponivel']
    modelo_carregado: bool
    estatisticas_carregadas: bool
    versao_api: str


class OpcaoNumerica(BaseModel):
    valor: int
    rotulo: str


class OpcaoBairro(BaseModel):
    valor: str
    grupo: Literal['frequente', 'raro']


class Opcoes(BaseModel):
    versao_contrato: str
    versao_modelo: str
    meses: list[OpcaoNumerica]
    dias_semana: list[OpcaoNumerica]
    tipos_local: list[str]
    bairros: list[OpcaoBairro]
    ausencia_permitida: list[str]


class Arquitetura(BaseModel):
    entradas: int
    camadas_ocultas: list[int]
    ativacoes: list[str]
    parametros_treinaveis: int


class ModeloPublico(BaseModel):
    versao_modelo: str
    versao_contrato: str
    arquitetura: Arquitetura
    limiar: float
    probabilidades_calibradas: Literal[False]
    rotulos: dict[str, str]
    atributos: list[str]
    colunas_por_atributo: dict[str, int]
    funcao_perda: str
    otimizador: str
    taxa_aprendizado: float
    epocas: int
    tamanho_lote: int
    linhas_ajuste_2023: int
    frequencia_minima_bairro: int
    bairros_com_coluna_propria: int
    limitacoes: list[str]


class _Fechado(BaseModel):
    """Campos desconhecidos nos agregados são erro: nada além do previsto é servido."""
    model_config = ConfigDict(extra='forbid')


class Contagem(_Fechado):
    furtos: int = Field(ge=0)
    roubos: int = Field(ge=0)


class ContagemAno(Contagem):
    ano: int


class ContagemMes(Contagem):
    ano: int
    mes: int = Field(ge=1, le=12)


class ContagemDiaMes(ContagemMes):
    dia_semana: int = Field(ge=0, le=6)


class CategoriaLocal(Contagem):
    categoria: str
    tipo: Literal['categoria', 'outros', 'ausente', 'demais']


class LocalAno(_Fechado):
    ano: int
    categorias: list[CategoriaLocal]


class Fonte(_Fechado):
    nome: str
    url: str
    recorte: str


class Periodo(_Fechado):
    inicio: str
    fim: str


class Estatisticas(_Fechado):
    fonte: Fonte
    periodo: Periodo
    total: Contagem
    por_ano: list[ContagemAno]
    por_mes: list[ContagemMes]
    por_dia_mes: list[ContagemDiaMes]
    por_tipo_local: list[LocalAno]
    limiar_demais_categorias: int
