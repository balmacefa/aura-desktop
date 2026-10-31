# Abre (o reutiliza) una ventana de Claude Code anclada al borde derecho, siempre encima.
# Uso: pwsh -NoProfile -WindowStyle Hidden -File claude-widget.ps1 [-Dir C:\ruta] [-Width 480]
param([string]$Dir = $HOME, [int]$Width = 480)

Add-Type -AssemblyName System.Windows.Forms
Add-Type @'
using System; using System.Runtime.InteropServices;
public class WinPos {
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
}
'@

Add-Type @'
using System; using System.Text; using System.Runtime.InteropServices;
public class WinFind {
  delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc p, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  // Windows Terminal aloja todas sus ventanas en un solo proceso: se busca por clase + título exacto.
  public static IntPtr ByTitle(string title) {
    IntPtr found = IntPtr.Zero;
    EnumWindows((h, l) => {
      var t = new StringBuilder(256); var c = new StringBuilder(256);
      GetWindowText(h, t, 256); GetClassName(h, c, 256);
      if (c.ToString() == "CASCADIA_HOSTING_WINDOW_CLASS" && t.ToString().StartsWith(title)) { found = h; return false; }
      return true; }, IntPtr.Zero);
    return found;
  }
}
'@

function Find-Widget { $h = [WinFind]::ByTitle('Claude'); if ($h -ne [IntPtr]::Zero) { [pscustomobject]@{ MainWindowHandle = $h } } }

$p = Find-Widget
if (-not $p) {
  # Sesión independiente: si se lanza desde dentro de Claude Code, no heredar sus variables
  Get-ChildItem Env: | Where-Object Name -match '^CLAUDE' | ForEach-Object { Remove-Item "Env:$($_.Name)" }
  # Ventana propia de Windows Terminal, nombrada "claude-widget", con título fijo
  # Cadena única: con un array, Start-Process no entrecomilla "Claude Code" y wt lo parte en dos
  Start-Process wt -ArgumentList "-w claude-widget new-tab --title `"Claude Code`" --suppressApplicationTitle -d `"$Dir`" pwsh -NoLogo -NoExit -Command claude"
  for ($i = 0; $i -lt 40 -and -not $p; $i++) { Start-Sleep -Milliseconds 250; $p = Find-Widget }
}
if (-not $p) { return }

$area = [Windows.Forms.Screen]::PrimaryScreen.WorkingArea
$HWND_TOPMOST = [IntPtr]::new(-1)
[WinPos]::ShowWindow($p.MainWindowHandle, 9) | Out-Null          # restaurar si estaba minimizada
# x = borde derecho - ancho ; alto = área de trabajo (no tapa la barra de tareas)
[WinPos]::SetWindowPos($p.MainWindowHandle, $HWND_TOPMOST, $area.Right - $Width, $area.Top, $Width, $area.Height, 0x0040) | Out-Null
[WinPos]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
