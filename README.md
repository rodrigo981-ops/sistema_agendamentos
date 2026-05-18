# Sistema Web de Agendamento de Serviços

Projeto Integrador desenvolvido com o objetivo de criar um sistema web para gerenciamento administrativo de agendamentos, integrando frontend, backend e banco de dados.

---

## 📌 Descrição

O sistema permite que o administrador gerencie clientes, serviços e agendamentos em uma interface web moderna e organizada.  
Os agendamentos são registrados por **cliente, serviço, data e horário**, garantindo maior controle sobre a agenda e evitando conflitos.

A aplicação foi desenvolvida para uso interno, sendo operada exclusivamente pelo administrador do sistema.

---

## 🎯 Objetivo do Projeto

Desenvolver uma aplicação web capaz de organizar e centralizar o controle de atendimentos, substituindo métodos manuais como anotações e planilhas, proporcionando mais eficiência e confiabilidade no gerenciamento da agenda.

---

## 👤 Público-alvo

O sistema é voltado para uso administrativo, podendo ser utilizado por:

- Proprietário do negócio  
- Funcionário responsável  
- Recepcionista  

---

## ⚙️ Funcionalidades Principais

- Cadastro, edição e exclusão de clientes  
- Cadastro e gerenciamento de serviços  
- Definição de duração e preço dos serviços  
- Criação e edição de agendamentos  
- Visualização da agenda completa  
- Filtros por data e status  
- Controle de status dos atendimentos:
  - Agendado  
  - Concluído  
  - Cancelado  
- Dashboard com resumo do sistema  

---

## 🧱 Estrutura do Sistema

O sistema é composto por três camadas:

- **Frontend:** Interface web desenvolvida para interação com o usuário  
- **Backend:** Responsável pelas regras de negócio e API REST  
- **Banco de Dados:** Armazenamento persistente das informações  

---

## 🛠️ Tecnologias Utilizadas

- **Frontend:** HTML, CSS e JavaScript  
- **Backend:** Python com Flask  
- **Banco de Dados:** SQLite  

---

## 📊 Modelo do Sistema

O sistema é baseado nas seguintes entidades:

- Administrador  
- Cliente  
- Serviço  
- Agendamento  

Os relacionamentos permitem que cada agendamento esteja vinculado a um cliente, um serviço e um administrador, garantindo a organização e integridade dos dados.

---

## 📄 Observações

Este projeto foi desenvolvido como parte do Projeto Integrador, com foco na aplicação prática dos conceitos de desenvolvimento web, integração entre sistemas e organização de dados.

A solução proposta atende às necessidades de pequenos negócios que buscam melhorar o controle de seus atendimentos de forma simples e eficiente.