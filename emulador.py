# Samara Cristina da Costa Batista
# 22554382

# pra rodar no terminal use python emulador.py codigo.s

import re
import sys

# Leitura do arquivo de entrada

entrada = sys.argv[1]

with open(entrada, "r", encoding="utf-8") as arquivo:
    linhas = arquivo.readlines()


# Estruturas de dados

# Registradores x0 ate x31
registradores = {f"x{i}": 0 for i in range(32)}

# Memoria de dados, byte a byte
memoria = {}

# Tabela de rotulos
rotulos = {}

# Tabela de instrucoes
instrucoes = {}

# Program Counter
pc = 0

# Bases dos segmentos
TEXTO_BASE = 0x00000000
DADOS_BASE = 0x00200000

# Nomes ABI
nomes_registradores = {
    "zero": "x0",
    "ra": "x1",
    "sp": "x2",
    "gp": "x3",
    "tp": "x4",

    "t0": "x5",
    "t1": "x6",
    "t2": "x7",

    "s0": "x8",
    "fp": "x8",
    "s1": "x9",

    "a0": "x10",
    "a1": "x11",
    "a2": "x12",
    "a3": "x13",
    "a4": "x14",
    "a5": "x15",
    "a6": "x16",
    "a7": "x17",

    "s2": "x18",
    "s3": "x19",
    "s4": "x20",
    "s5": "x21",
    "s6": "x22",
    "s7": "x23",
    "s8": "x24",
    "s9": "x25",
    "s10": "x26",
    "s11": "x27",

    "t3": "x28",
    "t4": "x29",
    "t5": "x30",
    "t6": "x31"
}

# Funcoes auxiliares: inteiros e registradores

def inteiro_32(valor):
    #Converte para int de 32 bits em complemento de 2
    valor = valor & 0xFFFFFFFF

    if valor >= 0x80000000:
        valor -= 0x100000000

    return valor


def com_sinal(valor, bits):
    # Interpreta valor como inteiro com sinal de bits.
    limite = 1 << (bits - 1)

    if valor >= limite:
        valor -= 1 << bits

    return valor


def nome_registrador(nome):
    # Converte nome ABI (t0, a0, sp...) para o nome canonico (x5, x10...).
    if nome in nomes_registradores:
        return nomes_registradores[nome]

    return nome


def ler_registrador(nome):
    # Le o valor de um registrador (aceita nome ABI ou numerico).
    nome = nome_registrador(nome)

    return registradores[nome]


def escrever_registrador(nome, valor):
    # Escreve em um registrador, escritas em x0 sao descartadas.
    nome = nome_registrador(nome)

    if nome == "x0":
        return

    registradores[nome] = inteiro_32(valor)


# Funcoes auxiliares: leitura do texto assembly

def limpar_linha(linha):
    # Remove comentarios (tudo depois de #) e espacos nas pontas.
    linha = linha.split("#", 1)[0]
    return linha.strip()


def separar_valores(linha):
    # Retorna os valores de uma diretiva .word, .half ou .byte.
    conteudo = linha.split(None, 1)

    if len(conteudo) < 2:
        return []

    return [valor.strip() for valor in conteudo[1].split(",") if valor.strip()]

def separar_campos(linha):
    # Separa uma instrucao em [mnemonico, operando1, operando2, ...].
    # Espacos extras sao aceitos em qualquer posicao, inclusive dentro de operandos de memoria: "lw t3, 0 (t0)" -> ["lw", "t3", "0(t0)"].

    linha = re.sub(r"\s*\(\s*", "(", linha)
    linha = re.sub(r"\s*\)", ")", linha)

    return linha.replace(",", " ").split()

def alinhar_endereco(endereco, n):
#Alinha o endereco para o proximo múltiplo de 2**n.
    alinhamento = 2 ** n
    return ((endereco + alinhamento - 1) // alinhamento) * alinhamento

# Primeira passagem: monta a tabela de rotulos e a de instrucoes

def primeira_passagem():
    segmento = None

    endereco_texto = TEXTO_BASE
    endereco_dados = DADOS_BASE

    for linha in linhas:
        linha = limpar_linha(linha)

        # ignora linhas vazias
        if linha == "":
            continue

        if linha == ".text":
            segmento = "text"
            continue

        if linha == ".data":
            segmento = "data"
            continue

        # Rotulo (sozinho na linha ou seguido de instrucao/diretiva)
        if ":" in linha:
            partes = linha.split(":", 1)

            nome_rotulo = partes[0].strip()

            if segmento == "text":
                rotulos[nome_rotulo] = endereco_texto
            elif segmento == "data":
                rotulos[nome_rotulo] = endereco_dados

            linha = partes[1].strip()

            if linha == "":
                continue

        # Segmento de dados: apenas avanca o endereco corrente
        if segmento == "data":
            if linha.startswith(".word"):
                endereco_dados += 4 * len(separar_valores(linha))

            elif linha.startswith(".half"):
                endereco_dados += 2 * len(separar_valores(linha))

            elif linha.startswith(".byte"):
                endereco_dados += len(separar_valores(linha))

            elif linha.startswith(".zero") or linha.startswith(".space"):
                partes = linha.split()
                tamanho = int(partes[1], 0)
                endereco_dados += tamanho

            elif linha.startswith(".align"):
                partes = linha.split()
                endereco_dados = alinhar_endereco(endereco_dados, int(partes[1], 0))

            continue

        # Segmento de texto: cada instrucao ocupa 4 bytes
        if segmento == "text":
            # diretivas (.globl etc.) nao geram instrucao
            if linha.startswith("."):
                continue

            instrucoes[endereco_texto] = separar_campos(linha)

            endereco_texto += 4

    return rotulos, instrucoes


# Memoria (little-endian, byte a byte)

def escrever_memoria(endereco, valor, quantidade):
#Escreve 'quantidade' bytes a partir de 'endereco' em little-endian.
    valor = valor & ((1 << (quantidade * 8)) - 1)

    for i in range(quantidade):
        memoria[endereco + i] = (valor >> (8 * i)) & 0xFF


def ler_memoria(endereco, quantidade):
#Le 'quantidade' bytes (little-endian). Endereco nunca escrito vale 0
    valor = 0

    for i in range(quantidade):
        byte = memoria.get(endereco + i, 0)
        valor |= byte << (8 * i)

    return valor

def inicializar_memoria():
# Preenche a memoria com os dados declarados no segmento .data
    segmento = None
    endereco_dados = DADOS_BASE

    for linha in linhas:
        linha = limpar_linha(linha)

        if linha == "":
            continue

        if linha == ".data":
            segmento = "data"
            continue

        if linha == ".text":
            segmento = "text"
            continue

        if segmento != "data":
            continue

        if ":" in linha:
            partes = linha.split(":", 1)
            linha = partes[1].strip()

            if linha == "":
                continue

        if linha.startswith(".word"):
            for texto_valor in separar_valores(linha):
                escrever_memoria(endereco_dados, int(texto_valor, 0), 4)
                endereco_dados += 4

        elif linha.startswith(".half"):
            for texto_valor in separar_valores(linha):
                escrever_memoria(endereco_dados, int(texto_valor, 0), 2)
                endereco_dados += 2

        elif linha.startswith(".byte"):
            for texto_valor in separar_valores(linha):
                escrever_memoria(endereco_dados, int(texto_valor, 0), 1)
                endereco_dados += 1

        elif linha.startswith(".zero") or linha.startswith(".space"):
            partes = linha.split()
            tamanho = int(partes[1], 0)

            for i in range(tamanho):
                memoria[endereco_dados + i] = 0

            endereco_dados += tamanho

        elif linha.startswith(".align"):
            partes = linha.split()
            endereco_dados = alinhar_endereco(endereco_dados, int(partes[1], 0))

def carregar_lb(endereco):
    return com_sinal(ler_memoria(endereco, 1), 8)

def carregar_lbu(endereco):
    return ler_memoria(endereco, 1)

def carregar_lh(endereco):
    return com_sinal(ler_memoria(endereco, 2), 16)

def carregar_lhu(endereco):
    return ler_memoria(endereco, 2)

def carregar_lw(endereco):
    return com_sinal(ler_memoria(endereco, 4), 32)

def armazenar_sb(endereco, valor):
    escrever_memoria(endereco, valor, 1)

def armazenar_sh(endereco, valor):
    escrever_memoria(endereco, valor, 2)

def armazenar_sw(endereco, valor):
    escrever_memoria(endereco, valor, 4)


# A primeira passagem e a inicializacao da memoria ocorrem ANTES da execucao
rotulos, instrucoes = primeira_passagem()
inicializar_memoria()

# Execucao das instrucoes:

def executar_pseudo(campos):
# Pseudoinstrucoes li, la e mv (apenas o efeito final)
    instrucao = campos[0]

    if instrucao == "li":
        rd = campos[1]
        imediato = int(campos[2], 0)

        escrever_registrador(rd, imediato)

    elif instrucao == "la":
        rd = campos[1]
        rotulo = campos[2]

        endereco = rotulos[rotulo]
        escrever_registrador(rd, endereco)

    elif instrucao == "mv":
        rd = campos[1]
        rs = campos[2]

        valor = ler_registrador(rs)
        escrever_registrador(rd, valor)


def dividir(a, b):
# Divisao inteira com sinal, truncando em direcao a zero
    if b == 0:
        return -1

    if a == -2147483648 and b == -1:
        return -2147483648

    resultado = abs(a) // abs(b)

    if (a < 0) != (b < 0):
        resultado = -resultado

    return resultado


def obter_endereco_memoria(operando):
# Calcula o endereco de um operando 'deslocamento(base)', ex: 4(t0)
    operando = operando.replace(" ", "")

    partes = operando.split("(", 1)

    # deslocamento omitido, como em "(t0)", vale 0
    deslocamento = int(partes[0], 0) if partes[0] != "" else 0
    registrador_base = partes[1].replace(")", "")

    endereco_base = ler_registrador(registrador_base)

    return (endereco_base + deslocamento) & 0xFFFFFFFF


def executar_instrucao(campos):

    # Executa uma instrucao.
    # Retorna (terminou, novo_pc):
    #     terminou -> True quando o programa executa ecall com a7 = 10
    #     novo_pc  -> endereco de destino se houve desvio/salto, senao None

    instrucao = campos[0]

    # Pseudoinstrucoes
    if instrucao in ["li", "la", "mv"]:
        executar_pseudo(campos)

    # Saltos incondicionais
    elif instrucao == "j":
        return False, rotulos[campos[1]]

    elif instrucao == "jr":
        return False, ler_registrador(campos[1]) & 0xFFFFFFFF

    # Desvios condicionais
    elif instrucao in ["beq", "bne", "blt", "bge", "bltu", "bgeu"]:
        a = ler_registrador(campos[1])
        b = ler_registrador(campos[2])
        rotulo = campos[3]

        if instrucao == "beq":
            condicao = a == b

        elif instrucao == "bne":
            condicao = a != b

        elif instrucao == "blt":
            condicao = a < b

        elif instrucao == "bge":
            condicao = a >= b

        elif instrucao == "bltu":
            condicao = (a & 0xFFFFFFFF) < (b & 0xFFFFFFFF)

        elif instrucao == "bgeu":
            condicao = (a & 0xFFFFFFFF) >= (b & 0xFFFFFFFF)

        if condicao:
            return False, rotulos[rotulo]

    # Instrucoes aritmeticas e logicas
    elif instrucao in [
        "add", "sub", "mul", "div", "rem",
        "sll", "slt", "sltu", "xor", "srl",
        "sra", "or", "and",
        "addi", "slti", "sltiu", "ori", "andi",
        "slli", "srli", "srai"
    ]:
        rd = campos[1]
        a = ler_registrador(campos[2])

        instrucoes_tres_registradores = [
            "add", "sub", "mul", "div", "rem",
            "sll", "slt", "sltu", "xor", "srl",
            "sra", "or", "and"
        ]

        if instrucao in instrucoes_tres_registradores:
            b = ler_registrador(campos[3])
        else:
            b = int(campos[3], 0)

        if instrucao in ["add", "addi"]:
            resultado = a + b

        elif instrucao == "sub":
            resultado = a - b

        elif instrucao == "mul":
            resultado = a * b

        elif instrucao == "div":
            resultado = dividir(a, b)

        elif instrucao == "rem":
            if b == 0:
                resultado = a
            else:
                resultado = a - dividir(a, b) * b

        elif instrucao in ["sll", "slli"]:
            resultado = a << (b & 31)

        elif instrucao in ["slt", "slti"]:
            resultado = int(a < b)

        elif instrucao in ["sltu", "sltiu"]:
            resultado = int(
                (a & 0xFFFFFFFF) < (b & 0xFFFFFFFF)
            )

        elif instrucao == "xor":
            resultado = a ^ b

        elif instrucao in ["srl", "srli"]:
            resultado = (a & 0xFFFFFFFF) >> (b & 31)

        elif instrucao in ["sra", "srai"]:
            resultado = a >> (b & 31)

        elif instrucao in ["or", "ori"]:
            resultado = a | b

        elif instrucao in ["and", "andi"]:
            resultado = a & b

        escrever_registrador(rd, resultado)

    # Loads: ler da memoria
    elif instrucao in ["lb", "lh", "lw", "lbu", "lhu"]:
        rd = campos[1]
        endereco = obter_endereco_memoria(campos[2])

        if instrucao == "lb":
            valor = carregar_lb(endereco)

        elif instrucao == "lh":
            valor = carregar_lh(endereco)

        elif instrucao == "lw":
            valor = carregar_lw(endereco)

        elif instrucao == "lbu":
            valor = carregar_lbu(endereco)

        elif instrucao == "lhu":
            valor = carregar_lhu(endereco)

        escrever_registrador(rd, valor)

    # Stores: gravar na memoria
    elif instrucao in ["sb", "sh", "sw"]:
        rs = campos[1]
        endereco = obter_endereco_memoria(campos[2])
        valor = ler_registrador(rs)

        if instrucao == "sb":
            armazenar_sb(endereco, valor)

        elif instrucao == "sh":
            armazenar_sh(endereco, valor)

        elif instrucao == "sw":
            armazenar_sw(endereco, valor)

    # Chamada ao sistema
    elif instrucao == "ecall":
        codigo = ler_registrador("a7")

        if codigo == 1:
            # imprime o inteiro em a0
            print(ler_registrador("a0"))

        elif codigo == 10:
            # encerra o programa
            return True, None

    # Instrucao desconhecida: avisa em stderr e interrompe
    else:
        sys.exit(f"Erro: instrucao nao suportada no endereco "
                 f"0x{pc:08X}: {' '.join(campos)}")

    return False, None


def executar():
#Laco principal: busca, executa e atualiza o pc
    global pc

    pc = rotulos["main"]

    while pc in instrucoes:
        campos = instrucoes[pc]

        terminou, novo_pc = executar_instrucao(campos)

        if terminou:
            break

        if novo_pc is not None:
            pc = novo_pc
        else:
            pc += 4

executar()