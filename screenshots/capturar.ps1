Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$screenshot = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$image = New-Object System.Drawing.Bitmap($screenshot.Width, $screenshot.Height)
$graphics = [System.Drawing.Graphics]::FromImage($image)
$graphics.CopyFromScreen($screenshot.Location, [System.Drawing.Point]::Empty, $screenshot.Size)

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$path = "C:\Users\Z\Desktop\plataforma\screenshots\$timestamp.png"
$image.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$image.Dispose()

Write-Host "Captura guardada: $path"
