# Gera o APK de release do DuoCash no Windows (sem precisar do Android Studio).
# Pré-requisitos: JDK 17, Android SDK e a chave de assinatura configurada em
# ~/.gradle/gradle.properties (veja docs/deploy.md).
# Uso: powershell -ExecutionPolicy Bypass -File scripts/build-apk.ps1 [-ApiUrl https://seu-servidor]
param([string]$ApiUrl = "")

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

# O Gradle/autolinking quebram com acentos no caminho (ex.: "Repositórios").
# Nesse caso o build é feito numa cópia espelhada em um caminho curto e só ASCII
# (curto também por causa do limite de 260 caracteres do ninja/CMake no Windows).
$realRoot = $root
if ($root -match '[^\x00-\x7F]') {
  $buildDir = "$env:SystemDrive\dcb"
  if (-not (Test-Path $buildDir)) {
    New-Item -ItemType Directory $buildDir | Out-Null
    # Só o usuário atual, SYSTEM e Administradores podem mexer (evita injeção de código no APK).
    icacls $buildDir /inheritance:r /grant:r "${env:USERNAME}:(OI)(CI)F" "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" | Out-Null
  }
  $root = "$buildDir\m"
  robocopy $realRoot $root /MIR /XD "$realRoot\android" "$realRoot\dist" "$realRoot\.expo" /NFL /NDL /NJH /NJS /NP | Out-Null
  if ($LASTEXITCODE -ge 8) { throw "falha ao copiar o projeto para $root" }
}

if (-not $env:JAVA_HOME) {
  $jdk = Get-ChildItem "C:\Program Files\Microsoft" -Directory -Filter "jdk-17*" -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $jdk) { throw "JDK 17 não encontrado. Instale com: winget install Microsoft.OpenJDK.17" }
  $env:JAVA_HOME = $jdk.FullName
}
if (-not $env:ANDROID_HOME) { $env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk" }
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"
$env:NODE_ENV = "production"
if ($ApiUrl) {
  if ($ApiUrl -notmatch '^https://[A-Za-z0-9.-]+(:\d{1,5})?$') { throw "ApiUrl deve ser https://dominio (sem caminho)" }
  $env:EXPO_PUBLIC_API_URL = $ApiUrl
}

# Nunca gerar APK de release com a chave pública de debug.
$gradleProps = "$env:USERPROFILE\.gradle\gradle.properties"
if (-not ((Test-Path $gradleProps) -and (Select-String -Path $gradleProps -Pattern '^DUOCASH_STORE_FILE=' -Quiet))) {
  throw "Chave de assinatura não configurada em $gradleProps (veja docs/deploy.md)."
}

Push-Location $root
try {
  npx expo prebuild --platform android --clean --no-install
  if ($LASTEXITCODE -ne 0) { throw "expo prebuild falhou" }
  Push-Location android
  try {
    .\gradlew.bat assembleRelease --no-daemon "-PreactNativeArchitectures=arm64-v8a,armeabi-v7a"
    if ($LASTEXITCODE -ne 0) { throw "gradle falhou" }
  } finally { Pop-Location }

  $apk = "android\app\build\outputs\apk\release\app-release.apk"
  New-Item -ItemType Directory -Force "$realRoot\dist" | Out-Null
  $out = "$realRoot\dist\DuoCash.apk"
  Copy-Item $apk $out -Force
  $hash = (Get-FileHash $out -Algorithm SHA256).Hash
  Write-Host "APK gerado: $out"
  Write-Host "SHA-256: $hash"
  $apksigner = Get-ChildItem "$env:ANDROID_HOME\build-tools" -Recurse -Filter apksigner.bat | Select-Object -Last 1
  if ($apksigner) { & $apksigner.FullName verify --print-certs $out | Select-String "SHA-256" }
} finally { Pop-Location }
