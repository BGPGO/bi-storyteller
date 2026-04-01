@echo off
echo === BI Storyteller - Setup Local ===
echo.

set TARGET=C:\Dev\bi-storyteller

echo Clonando repo em %TARGET%...
if exist %TARGET% (
    echo Pasta ja existe, fazendo git pull...
    cd %TARGET%
    git pull
) else (
    git clone https://github.com/BGPGO/bi-storyteller.git %TARGET%
    cd %TARGET%
)

echo.
echo === Configurando Backend ===
cd %TARGET%\backend

if not exist .env (
    copy .env.example .env
    echo.
    echo ATENCAO: Abra %TARGET%\backend\.env e adicione sua ANTHROPIC_API_KEY
    echo Pressione qualquer tecla apos configurar o .env...
    pause
)

pip install -r requirements.txt
playwright install chromium

echo.
echo === Instalando Frontend ===
cd %TARGET%\frontend
npm install

echo.
echo === Setup concluido! ===
echo.
echo Para rodar o projeto, abra 2 terminais:
echo.
echo   Terminal 1 (Backend):
echo     cd %TARGET%\backend
echo     uvicorn main:app --reload
echo.
echo   Terminal 2 (Frontend):
echo     cd %TARGET%\frontend
echo     npm run dev
echo.
echo Acesse: http://localhost:5173
echo.
pause
