using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

[assembly: AssemblyTitle("铁底湾的回响 IV · 一键启动")]
[assembly: AssemblyDescription("调用同目录项目的安全启动脚本，不包含游戏或存档。")]
[assembly: AssemblyVersion("1.0.0.0")]

namespace IronBottomSoundLauncher
{
    internal sealed class LaunchResult
    {
        public int Code;
        public string Message;
    }

    internal static class Program
    {
        [STAThread]
        private static int Main(string[] args)
        {
            // A GUI executable has no console code page. Setting OutputEncoding
            // would throw even with redirected pipes; use UTF-8 writers instead.
            Console.SetOut(new StreamWriter(Console.OpenStandardOutput(), new UTF8Encoding(false)) { AutoFlush = true });
            Console.SetError(new StreamWriter(Console.OpenStandardError(), new UTF8Encoding(false)) { AutoFlush = true });
            bool quiet = false, noBrowser = false, restartBackend = false;
            foreach (string arg in args)
            {
                if (arg == "--quiet") quiet = true;
                else if (arg == "--no-browser") noBrowser = true;
                else if (arg == "--restart-backend") restartBackend = true;
                else if (arg == "--help")
                {
                    Console.WriteLine("一键启动游戏.exe [--quiet] [--no-browser] [--restart-backend]");
                    return 0;
                }
                else
                {
                    Console.Error.WriteLine("不支持的参数：" + arg);
                    return 2;
                }
            }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            string root = Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory);
            string missing = ValidateProject(root);
            if (missing != null)
            {
                if (quiet) Console.Error.WriteLine(missing);
                else MessageBox.Show(missing, "找不到游戏项目", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return 2;
            }
            bool acquired = false;
            using (var mutex = new Mutex(false, MutexName(root)))
            {
                try
                {
                    try { acquired = mutex.WaitOne(0); }
                    catch (AbandonedMutexException) { acquired = true; }
                    if (!acquired)
                    {
                        string message = "游戏正在启动，请等待已有启动窗口完成。";
                        if (quiet) Console.WriteLine(message);
                        else MessageBox.Show(message, "正在启动", MessageBoxButtons.OK, MessageBoxIcon.Information);
                        return 0;
                    }
                    if (quiet)
                    {
                        LaunchResult result = Launch(root, noBrowser, restartBackend);
                        if (result.Code == 0) Console.WriteLine(result.Message);
                        else Console.Error.WriteLine(result.Message);
                        return result.Code;
                    }
                    using (var window = new StartupWindow(root, noBrowser, restartBackend))
                    {
                        Application.Run(window);
                        return window.ExitCode;
                    }
                }
                finally { if (acquired) mutex.ReleaseMutex(); }
            }
        }

        private static string ValidateProject(string root)
        {
            foreach (string file in new[] { "scripts/start-game.ps1", "scripts/game-runtime.ps1", "backend/src/iron_bottom_sound/api.py", "frontend/package.json" })
            {
                if (!File.Exists(Path.Combine(root, file)))
                    return "请将 EXE 留在游戏项目根目录，与 start-game.bat 放在一起。\n缺少文件：" + file + "\n\n它是启动器，不是独立游戏安装包。";
            }
            return null;
        }

        private static string MutexName(string root)
        {
            using (var hash = SHA256.Create())
                return "Local\\IronBottomSoundLauncher-" + BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(root.ToUpperInvariant()))).Replace("-", "");
        }

        private static string Quote(string value)
        {
            // A Windows path cannot contain a quote; this argument is always a file,
            // so it also cannot end in a directory separator.
            if (value.IndexOf('"') >= 0) throw new ArgumentException("路径含不支持的双引号。");
            return "\"" + value + "\"";
        }

        internal static LaunchResult Launch(string root, bool noBrowser, bool restartBackend)
        {
            string logs = Path.Combine(root, "tmp", "runtime");
            try
            {
                Directory.CreateDirectory(logs);
                var info = new ProcessStartInfo
                {
                    FileName = Path.Combine(Environment.SystemDirectory, "WindowsPowerShell", "v1.0", "powershell.exe"),
                    Arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File " + Quote(Path.Combine(root, "scripts", "start-game.ps1"))
                        + (noBrowser ? " -NoBrowser" : "") + (restartBackend ? " -RestartBackend" : ""),
                    WorkingDirectory = root,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    StandardOutputEncoding = Encoding.UTF8,
                    StandardErrorEncoding = Encoding.UTF8
                };
                // Windows PowerShell's inherited console code page can vary.
                // The script explicitly configures UTF-8 when running for this EXE.
                info.EnvironmentVariables["IBS_LAUNCHER_UTF8"] = "1";
                // Do not pass PowerShell 7's module search paths into Windows
                // PowerShell 5.1; let it restore its own standard module paths.
                info.EnvironmentVariables.Remove("PSModulePath");
                using (var process = Process.Start(info))
                {
                    Task<string> output = process.StandardOutput.ReadToEndAsync();
                    Task<string> error = process.StandardError.ReadToEndAsync();
                    if (!process.WaitForExit(180000))
                    {
                        // Stop only our PowerShell wrapper, never kill a process tree.
                        process.Kill();
                        process.WaitForExit();
                        File.WriteAllText(Path.Combine(logs, "launcher.log"), "启动超时。请检查服务日志后重试。", new UTF8Encoding(false));
                        return new LaunchResult { Code = 1, Message = "启动超过 3 分钟。请打开日志目录检查；已经启动的游戏服务不会被强制关闭。" };
                    }
                    Task.WaitAll(output, error);
                    string details = output.Result + Environment.NewLine + error.Result;
                    File.WriteAllText(Path.Combine(logs, "launcher.log"), details, new UTF8Encoding(false));
                    return new LaunchResult
                    {
                        Code = process.ExitCode,
                        Message = process.ExitCode == 0 ? "游戏已就绪：http://127.0.0.1:5173/" :
                            "游戏未能启动。\n\n" + FailureHint(details) + "\n\n详情见 tmp\\runtime\\launcher.log。"
                    };
                }
            }
            catch (Exception error)
            {
                return new LaunchResult { Code = 1, Message = "无法启动游戏：" + error.Message + "\n请确认 Python、前端依赖已安装，并检查日志目录。" };
            }
        }

        private static string FailureHint(string details)
        {
            if (details.Contains("left untouched") || details.Contains("No project process record"))
                return "8000 或 5173 端口被未确认归属的服务占用。请关闭之前手动启动的服务，再双击启动器；它们未被强行停止。";
            if (details.Contains("Node.js not found")) return "未找到 Node.js。请安装 Node.js 20 或更高版本。";
            return "请检查 Python 与前端依赖，以及 backend-error.log / frontend-error.log；修正后再次双击 EXE。";
        }
    }

    public sealed class StartupWindow : Form
    {
        private readonly string root;
        private readonly bool noBrowser, restartBackend;
        private readonly Label status, detail;
        private readonly ProgressBar progress;
        private readonly Button logs, close;
        private bool running = true;
        public int ExitCode { get; private set; }

        public StartupWindow(string projectRoot, bool suppressBrowser, bool restart)
        {
            root = projectRoot;
            noBrowser = suppressBrowser;
            restartBackend = restart;
            ExitCode = 1;
            Text = "铁底湾的回响 IV · 一键启动";
            ClientSize = new Size(500, 246);
            AutoScaleMode = AutoScaleMode.Dpi;
            Font = new Font("Microsoft YaHei UI", 10);
            BackColor = ColorTranslator.FromHtml("#152123");
            ForeColor = ColorTranslator.FromHtml("#e9e2d0");
            FormBorderStyle = FormBorderStyle.FixedDialog;
            StartPosition = FormStartPosition.CenterScreen;
            MaximizeBox = false;
            MinimizeBox = false;
            var title = new Label { Text = "铁底湾的回响 IV", Left = 24, Top = 22, Width = 452, Height = 36, Font = new Font(Font.FontFamily, 16, FontStyle.Bold), ForeColor = ColorTranslator.FromHtml("#c6a766") };
            status = new Label { Text = "正在检查并启动本地服务…", Left = 24, Top = 72, Width = 452, Height = 32 };
            progress = new ProgressBar { Left = 24, Top = 112, Width = 452, Height = 8, Style = ProgressBarStyle.Marquee };
            detail = new Label { Text = "就绪后自动打开游戏。存档和战报保持不变。", Left = 24, Top = 137, Width = 452, Height = 40 };
            logs = new Button { Text = "打开日志目录", Left = 24, Top = 196, Width = 150, Height = 34, Visible = false };
            close = new Button { Text = "关闭", Left = 376, Top = 196, Width = 100, Height = 34, Visible = false };
            Controls.AddRange(new Control[] { title, status, progress, detail, logs, close });
            logs.Click += delegate
            {
                try { Process.Start(new ProcessStartInfo { FileName = Path.Combine(root, "tmp", "runtime"), UseShellExecute = true }); }
                catch (Exception error) { MessageBox.Show(this, error.Message, "无法打开日志目录"); }
            };
            close.Click += delegate { Close(); };
            FormClosing += delegate(object sender, FormClosingEventArgs e) { if (running) e.Cancel = true; };
            Shown += async delegate
            {
                LaunchResult result = await Task.Run(() => Program.Launch(root, noBrowser, restartBackend));
                ExitCode = result.Code;
                running = false;
                if (result.Code == 0) { Close(); return; }
                progress.Visible = false;
                status.Text = "启动未完成";
                status.ForeColor = ColorTranslator.FromHtml("#ef9c90");
                detail.Text = result.Message;
                detail.Top = 110;
                detail.Height = 132;
                ClientSize = new Size(500, 306);
                logs.Top = close.Top = 254;
                logs.Visible = close.Visible = true;
            };
        }
    }
}
