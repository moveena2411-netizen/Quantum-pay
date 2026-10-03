@echo off
setlocal
set ROOT=D:\Quantum\QuantumPay

if not exist "%ROOT%\backend" (
  echo ERROR: %ROOT%\backend not found.
  pause
  exit /b 1
)

if not exist "%ROOT%\frontend\lib\services" (
  echo ERROR: Flutter frontend path not found.
  pause
  exit /b 1
)

if not exist "%ROOT%\backend\backup_before_final_risk_fix" mkdir "%ROOT%\backend\backup_before_final_risk_fix"
if not exist "%ROOT%\frontend\lib\screens\payment" mkdir "%ROOT%\frontend\lib\screens\payment"

copy /Y "%~dp0backend\main.py" "%ROOT%\backend\main.py"
copy /Y "%~dp0backend\risk_engine.py" "%ROOT%\backend\risk_engine.py"
copy /Y "%~dp0backend\identifier_analyzer.py" "%ROOT%\backend\identifier_analyzer.py"
copy /Y "%~dp0backend\schemas.py" "%ROOT%\backend\schemas.py"
copy /Y "%~dp0backend\challenge_engine.py" "%ROOT%\backend\challenge_engine.py"
copy /Y "%~dp0backend\security_message_service.py" "%ROOT%\backend\security_message_service.py"
copy /Y "%~dp0frontend\lib\services\api_service.dart" "%ROOT%\frontend\lib\services\api_service.dart"
copy /Y "%~dp0frontend\lib\screens\payment\send_money_screen.dart" "%ROOT%\frontend\lib\screens\payment\send_money_screen.dart"

echo.
echo QuantumPay corrected files copied.
echo Keep your existing dataset\identifier_dataset_500.csv and existing database/ML-DSA/passkey files.
echo.
pause
