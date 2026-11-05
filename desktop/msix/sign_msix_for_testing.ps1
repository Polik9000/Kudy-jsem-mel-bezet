param(
    [Parameter(Mandatory = $true)]
    [string]$PackagePath,
    [Parameter(Mandatory = $true)]
    [string]$CertificatePath
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$publisher = $env:MSIX_PUBLISHER
if ([string]::IsNullOrWhiteSpace($publisher)) {
    $publisher = "CN=KudyJsemMelBezet.TestOnly"
}

$package = (Resolve-Path -LiteralPath $PackagePath).Path
$certificate = $null
$pfxPath = Join-Path $env:TEMP ("kudy-msix-" + [guid]::NewGuid().ToString("N") + ".pfx")

try {
    $certificate = New-SelfSignedCertificate `
        -Type Custom `
        -Subject $publisher `
        -FriendlyName "Kudy jsem mel bezet - CI test only" `
        -KeyAlgorithm RSA `
        -KeyLength 2048 `
        -HashAlgorithm SHA256 `
        -KeyUsage DigitalSignature `
        -KeyExportPolicy Exportable `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3")

    $passwordPlain = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
    $password = ConvertTo-SecureString -String $passwordPlain -AsPlainText -Force

    Export-PfxCertificate -Cert $certificate -FilePath $pfxPath -Password $password | Out-Null
    Export-Certificate -Cert $certificate -FilePath $CertificatePath -Type CERT | Out-Null

    $programFilesX86 = [Environment]::GetFolderPath("ProgramFilesX86")
    $kitsRoot = Join-Path $programFilesX86 "Windows Kits\10\bin"
    $signTool = Get-ChildItem -Path $kitsRoot -Filter signtool.exe -Recurse -File |
        Where-Object { $_.FullName -match "\\x64\\signtool\.exe$" } |
        Sort-Object -Property FullName -Descending |
        Select-Object -First 1

    if (-not $signTool) {
        throw "SignTool.exe nebyl nalezen v Windows SDK."
    }

    & $signTool.FullName sign /fd SHA256 /f $pfxPath /p $passwordPlain $package
    if ($LASTEXITCODE -ne 0) {
        throw "SignTool nedokázal podepsat testovací MSIX (exit code $LASTEXITCODE)."
    }

    & $signTool.FullName verify /pa /v $package
    if ($LASTEXITCODE -ne 0) {
        throw "Ověření podpisu testovacího MSIX selhalo (exit code $LASTEXITCODE)."
    }

    if (-not (Test-Path -LiteralPath $CertificatePath) -or (Get-Item -LiteralPath $package).Length -eq 0) {
        throw "Testovací MSIX nebo veřejný certifikát nebyl vytvořen."
    }

    Write-Host "Testovací MSIX byl podepsán certifikátem s Publisher: $publisher"
}
finally {
    if (Test-Path -LiteralPath $pfxPath) {
        Remove-Item -LiteralPath $pfxPath -Force
    }
    if ($certificate) {
        Remove-Item -LiteralPath ("Cert:\CurrentUser\My\" + $certificate.Thumbprint) -Force -ErrorAction SilentlyContinue
    }
}
