# Presença

## Configurar o MySQL local

1. Inicie o serviço do MySQL.
2. Importe o modelo do banco:

   ```bash
   mysql -u root -p < BD_PRESENCA.sql
   ```

3. Instale as dependências da API:

   ```bash
   python3 -m pip install -r requirements.txt
   ```

4. Copie `.env.example` para `.env` e informe a senha do MySQL em `MYSQL_PASSWORD`.

5. Inicie a API:

   ```bash
   python3 app.py
   ```

6. Abra `index.html` no navegador. O site enviará os cadastros para `http://127.0.0.1:5000`, e a API salvará os dados no banco `PRESENCA_ALUNOS`.

As variáveis `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD` e `MYSQL_DATABASE` podem ser ajustadas no `.env` para qualquer instalação local do MySQL.

## Publicar no Render

1. Envie este projeto para um repositório no GitHub.
2. No Render, escolha **New > Blueprint** e selecione o repositório.
3. O arquivo `render.yaml` criará o serviço Flask automaticamente.
4. Preencha no Render as variáveis `MYSQL_HOST`, `MYSQL_USER` e `MYSQL_PASSWORD` de um MySQL hospedado.

O MySQL instalado apenas no seu computador não é acessível pelo Render. Depois da publicação, o endereço do próprio serviço Render servirá a página e a API.