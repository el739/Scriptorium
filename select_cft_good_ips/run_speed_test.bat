@echo off

REM Set the project directory
set "PROJECT_DIR=%~dp0"

REM Navigate to the ping_test directory
cd "%PROJECT_DIR%ping_test"

REM Compile and run the Go program
echo "Running Go ping test..."
go run main.go

REM Navigate back to the project root
cd "%PROJECT_DIR%"

REM Run the Python speed test script
echo "Running Python speed test..."
python speed_test.py

echo "Speed test complete."
pause
