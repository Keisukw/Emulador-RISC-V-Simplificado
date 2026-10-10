# Emulador RISC-V Simplificado

Trabalho prático 2 (TP2) da disciplina **ICC062 – Arquitetura de Computadores (2026/2)**.

**Autora:** Samara Cristina da Costa Batista
**Matrícula:** 22554382

## O que é isso?

Um emulador de RISC-V de 32 bits escrito em Python 3. Você entrega um arquivo em Assembly RISC-V (`codigo.s`) e ele executa o programa instrução por instrução, mexendo nos registradores e na memória como um processador de verdade faria. Desvios condicionais e chamadas de sistema (`ecall`) também funcionam.

Cada instrução é interpretada direto do texto do assembly. Também não usei nenhuma biblioteca externa nem simulador pronto. Só a biblioteca padrão do Python (`sys` e `re`).

## O que você precisa

- Python 3 instalado (qualquer versão recente serve)

## Como executar

Na pasta do projeto, rode:

```bash
python emulador.py codigo.s
```

Em alguns sistemas (Linux e macOS, principalmente) o comando pode ser `python3`:

```bash
python3 emulador.py codigo.s
```

O caminho do arquivo `.s` vem sempre pela linha de comando. O programa não pede nada pelo teclado e não gera arquivo de saída: tudo o que aparece na tela vem das `ecall` do próprio programa assembly.

## Exemplo de execução

Salve o código abaixo como `codigo.s`. Ele soma os números de 0 a 9 e imprime o resultado:

```asm
.data
max: .byte 10

.text
main:
    la   t0, max          # t0 = endereço de max
    lb   t0, 0(t0)        # t0 = 10
    li   t1, 0            # contador
    li   a0, 0            # acumulador
while: bge t1, t0, end_while
    add  a0, a0, t1
    addi t1, t1, 1
    beq  zero, zero, while
end_while: li a7, 1       # ecall 1: imprime o inteiro em a0
    ecall
    li   a7, 10           # ecall 10: encerra o programa
    ecall
```

Executando:

```bash
python emulador.py codigo.s
```

Saída:

```
45
```

## O que o emulador entende

**Instruções**

| Tipo | Instruções |
|---|---|
| Aritmética (R) | `add sub sll slt sltu xor srl sra or and mul div rem` |
| Aritmética com imediato (I) | `addi slti sltiu ori andi slli srli srai` |
| Carga (I) | `lb lh lw lbu lhu` |
| Armazenamento (S) | `sb sh sw` |
| Desvio condicional (B) | `beq bne blt bge bltu bgeu` |
| Sistema | `ecall` |

**Pseudoinstruções:** `li`, `la`, `mv`, `j`, `jr`

**Diretivas:** `.text`, `.data`, `.word`, `.half`, `.byte`, `.zero` / `.space`, `.align` e `.globl` (esta última é aceita, mas não faz nada na execução)

**Registradores:** tanto os nomes numéricos (`x0` a `x31`) quanto os nomes ABI (`zero`, `ra`, `sp`, `gp`, `tp`, `t0`–`t6`, `s0`–`s11`, `fp`, `a0`–`a7`).

**Chamadas de sistema (`ecall`):** o valor de `a7` escolhe o serviço.

| `a7` | O que faz |
|---|---|
| 1 | Imprime o inteiro que está em `a0` |
| 10 | Encerra o programa |

## Como ele funciona por dentro

O estado do emulador fica em quatro estruturas:

- **`registradores`**: dicionário de `x0` a `x31` com inteiros de 32 bits em complemento de dois. Todos começam em 0 e o `x0` é sempre 0, então qualquer escrita nele é descartada.
- **`memoria`**: dicionário `endereço → byte`, separado dos registradores. Palavras e meias-palavras são gravadas em *little-endian*, e um endereço que nunca foi escrito é lido como 0.
- **`pc`**: o endereço da instrução atual. Começa no rótulo `main`, avança de 4 em 4 e é substituído diretamente quando um desvio é tomado ou quando acontece um `j` / `jr`.
- **`rotulos` e `instrucoes`**: montados numa primeira passagem pelo arquivo, antes de executar qualquer coisa. `rotulos` guarda o endereço de cada rótulo (texto ou dados) e `instrucoes` guarda, para cada endereço, a lista com o mnemônico e os operandos já sem comentários.

Os segmentos começam em `0x00000000` (texto) e `0x00200000` (dados). A execução termina quando o programa chama `ecall` com `a7 = 10`.

## Observações

- **Alinhamento:** não existe alinhamento automático. Um dado só é alinhado se o código tiver um `.align n` explícito.
- **Espaços e comentários:** comentários começam com `#` e vão até o fim da linha. Espaços extras são aceitos em qualquer lugar, inclusive em `0 (t2)`. Um rótulo pode ficar sozinho na linha ou vir seguido de uma instrução, como em `while: bge t1, t0, end_while`.
- **Impressão:** o `ecall` 1 imprime o número seguido de quebra de linha.
- **Divisão:** `div` trunca em direção a zero, como no RISC-V. Divisão por zero retorna `-1` e `rem` por zero retorna o próprio dividendo.
- **Instrução desconhecida:** se o assembly tiver uma instrução que o emulador não conhece, ele para e mostra uma mensagem de erro no `stderr`, com o endereço e a instrução, para facilitar achar o problema.
- **Fim do programa:** a execução também para se o `pc` chegar a um endereço sem instrução.

## Arquivos do repositório

```
├── emulador.py   # o emulador
└── README.md     # este arquivo
```