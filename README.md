
# 💬 Sistema de Chat Assíncrono com Grupos e Envio de Arquivos

📄 **[Documentação Completa do Projeto](https://docs.google.com/document/d/1SYe64iOag_qjpesbO73uhAK-sUzhPDZX0D0CKHrULmM/edit?usp=sharing)**


## 📌 Introdução

A comunicação evoluiu da linguagem gestual à digital, tornando-se essencial em nossa sociedade. Neste projeto, foi desenvolvido um **sistema de chat assíncrono em Python**, inspirado em aplicativos como WhatsApp e Telegram, com foco em mensagens privadas, em grupo e envio de arquivos via terminal.

---

## 🎯 Objetivos

### Objetivo Geral
Desenvolver um sistema de chat estilo WhatsApp, aplicando conceitos de **sistemas distribuídos e comunicação em rede**.

### Objetivos Específicos
- Enviar mensagens privadas e em grupo
- Criar e gerenciar grupos de usuários
- Enviar arquivos (imagens, vídeos, documentos) entre usuários ou grupos

---

## 🏗️ Arquitetura do Sistema

- Comunicação via protocolo **TCP** para garantir confiabilidade
- Baseado em **cliente-servidor** com múltiplos clientes assíncronos
- Troca de mensagens no formato **JSON + newline (`\n`)**
- Transmissão de arquivos via **Base64**

---

## 👤 Histórias de Usuário

- **US01 - Mensagens Privadas:** Comunicação direta entre usuários.
- **US02 - Mensagens em Grupo:** Envio de mensagens para múltiplos usuários simultaneamente.
- **US03 - Envio de Arquivos:** Compartilhamento de arquivos via terminal.

---

## 🔄 Casos de Uso

### UC01 - Enviar Mensagens Privadas
- Envio de mensagens via comando:
/pm <nome_do_destinatário> <mensagem>


### UC02 - Enviar Mensagens em Grupo
- Criação e entrada em grupos:


/criargrupo <nome>
/entrargrupo <nome>

- Envio de mensagens para grupo:


/g <nome_do_grupo> <mensagem>


### UC03 - Enviar Arquivos
- Envio para todos:


/enviar <caminho_arquivo>

- Envio privado:


/pmfile <nome_destinatário> <caminho_arquivo>

- Envio para grupo:


/gfile <nome_grupo> <caminho_arquivo>


---

## 🧠 Decisões Técnicas

- **TCP** escolhido por confiabilidade (diferente de UDP)
- **Python** pela produtividade e riqueza de bibliotecas
- **Asyncio** para concorrência assíncrona eficiente
- **Base64** para envio seguro de arquivos
- **Radmin VPN** usada para testes remotos entre os membros da equipe

---

## 📦 Bibliotecas Utilizadas

| Biblioteca | Função |
|------------|--------|
| `asyncio`  | Conexões e tarefas assíncronas |
| `json`     | Serialização das mensagens |
| `sys`      | Entrada do usuário via terminal |
| `base64`   | Codificação segura de arquivos |
| `os`       | Manipulação de arquivos locais |

---

## 🧪 Testes Realizados

- **12/09/2025**: Teste de conectividade (localhost e rede local)
- **15/09/2025**: Teste de envio de arquivos com Base64
- **19/09/2025**: Teste com múltiplos clientes em rede local
- **22/09/2025**: Teste final com criação de grupos e validação com professor orientador

---

## ⚠️ Limitações e Melhorias Futuras

### 🔒 Limitações
- Sem persistência de mensagens (não ficam salvas)
- Sem interface gráfica

### 🚀 Melhorias Futuras
- Adição de **banco de dados** para armazenar mensagens
- Criação de uma **interface gráfica (GUI)**
- Suporte a chamadas de voz (uso de UDP)
- Maior **escalabilidade** e segurança

---

## 👥 Equipe & Agradecimentos

Projeto realizado como atividade prática em disciplina de Redes de Computadores, sob orientação do professor **Vagner Sacramento**.  
Agradecimentos à turma da **Sala 154 - INF**, e à equipe que participou dos testes e desenvolvimento.

---
