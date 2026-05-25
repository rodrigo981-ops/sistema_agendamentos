# 💈 Sistema Web de Agendamento para Barbearia

Projeto Integrador desenvolvido com o objetivo de criar um sistema web para gerenciamento administrativo de agendamentos em uma barbearia, integrando frontend, backend e banco de dados.

---

## 📌 Descrição

O sistema permite que o administrador gerencie clientes, serviços e agendamentos em uma interface web moderna e organizada.

Os atendimentos são registrados por cliente, serviço, data e horário, garantindo maior controle sobre a agenda e evitando conflitos de horários.

O sistema simula o funcionamento de uma barbearia, permitindo o cadastro de serviços como corte de cabelo, barba e combos, organizando o fluxo de atendimento de forma prática e eficiente.

A aplicação é de uso interno, sendo operada exclusivamente pelo administrador.

---

## 🎯 Objetivo do Projeto

Desenvolver uma aplicação web capaz de organizar e centralizar o controle de atendimentos de uma barbearia, substituindo métodos manuais como anotações e planilhas, proporcionando:

- ✅ Mais eficiência  
- ✅ Melhor organização  
- ✅ Maior confiabilidade no gerenciamento da agenda  

---

## 👤 Público-alvo

O sistema é voltado para uso administrativo em barbearias, podendo ser utilizado por:

- 🧑 Proprietário  
- ✂️ Barbeiro responsável  
- 🧾 Recepcionista  

---

## ⚙️ Funcionalidades Principais

- 📋 Cadastro, edição e exclusão de clientes  
- ✂️ Cadastro e gerenciamento de serviços  
- ⏱️ Definição de duração e preço dos serviços  
- 📅 Criação e edição de agendamentos  
- 📊 Visualização da agenda completa  
- 🔍 Filtros por data e status  
- 🔄 Controle de status dos atendimentos:
  - 🟡 Agendado  
  - 🟢 Concluído  
  - 🔴 Cancelado  
- 📌 Dashboard com resumo do sistema  

---

## 🧱 Estrutura do Sistema

O sistema é composto por três camadas:

- 💻 **Frontend**: Interface web acessada pelo navegador  
- ⚙️ **Backend**: Responsável pelas regras de negócio e API REST  
- 🗄️ **Banco de Dados**: Armazenamento das informações de clientes, serviços e agendamentos  

---

## 🛠️ Tecnologias Utilizadas

- 🌐 **Frontend**: HTML, CSS e JavaScript  
- 🐍 **Backend**: Python (Flask)  
- 🗃️ **Banco de Dados**: SQLite  

---

## 📊 Modelo do Sistema

O sistema é baseado nas seguintes entidades:

- 👤 Administrador  
- 👥 Cliente  
- ✂️ Serviço  
- 📅 Agendamento  

Cada agendamento está vinculado a um cliente, um serviço e um administrador, garantindo organização e integridade dos dados.

---

## 💡 Exemplos de Serviços

- ✂️ Corte de cabelo  
- 🧔 Barba  
- 💈 Corte + Barba  

---

## 📄 Observações

Este projeto foi desenvolvido como parte do Projeto Integrador, com foco na aplicação prática dos conceitos de:

- Desenvolvimento web  
- Integração entre sistemas  
- Organização de dados  

A solução atende às necessidades de pequenos negócios, oferecendo uma forma simples e eficiente de gerenciar atendimentos.