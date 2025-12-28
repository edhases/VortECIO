@echo off
echo Building LHM Plugin (VortSensors)...

:: Navigate to the C# project directory
cd plugins/lhm

:: Build and publish the project in-place
dotnet publish -c Release -r win-x64 --self-contained false /p:PublishSingleFile=false -o .

:: Check for success
if %errorlevel% neq 0 (
    echo.
    echo LHM Plugin build failed.
    exit /b %errorlevel%
)

echo.
echo LHM Plugin build successful.
cd ../..
