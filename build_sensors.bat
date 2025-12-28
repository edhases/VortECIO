@echo off
echo Building VortSensors C# project...

:: Navigate to the C# project directory
cd sensors/VortSensors

:: Restore dependencies
dotnet restore

:: Build and publish the project
:: -r win-x64 specifies the target runtime
:: --self-contained false means it will rely on .NET being installed on the user's machine
:: /p:PublishSingleFile=false ensures DLLs are kept separate
:: -o specifies the output directory
dotnet publish -c Release -r win-x64 --self-contained false /p:PublishSingleFile=false -o ../../build/bin/

:: Check for success
if %errorlevel% neq 0 (
    echo.
    echo C# build failed.
    exit /b %errorlevel%
)

echo.
echo C# build successful. Output is in build/bin/
cd ../..
