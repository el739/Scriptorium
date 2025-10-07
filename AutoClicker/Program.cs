using System;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;

namespace AutoClickerApp
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            ApplicationConfiguration.Initialize();
            Application.Run(new AutoClickerForm());
        }
    }

    public class AutoClickerForm : Form
    {
        // PInvoke for SendInput
        [StructLayout(LayoutKind.Sequential)]
        struct INPUT
        {
            public uint type;
            public InputUnion U;
        }

        [StructLayout(LayoutKind.Explicit)]
        struct InputUnion
        {
            [FieldOffset(0)]
            public MOUSEINPUT mi;
            // keyboard/hard not needed for this app
        }

        [StructLayout(LayoutKind.Sequential)]
        struct MOUSEINPUT
        {
            public int dx;
            public int dy;
            public uint mouseData;
            public uint dwFlags;
            public uint time;
            public IntPtr dwExtraInfo;
        }

        const uint INPUT_MOUSE = 0;
        const uint MOUSEEVENTF_LEFTDOWN = 0x0002;
        const uint MOUSEEVENTF_LEFTUP = 0x0004;

        [DllImport("user32.dll", SetLastError = true)]
        static extern uint SendInput(uint nInputs, [MarshalAs(UnmanagedType.LPArray), In] INPUT[] pInputs, int cbSize);

        // PInvoke for GetAsyncKeyState
        [DllImport("user32.dll")]
        static extern short GetAsyncKeyState(int vKey);

        // UI Elements
        Label statusLabel;
        Label currentKeyLabel;
        Button setKeyButton;
        Button startButton;
        Button stopButton;

        // State
        Keys? selectedKey = null;
        Thread clickThread = null;
        volatile bool runThread = false;

        public AutoClickerForm()
        {
            Text = "自动点击器";
            Size = new Size(360, 200);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;

            InitializeComponents();

            this.FormClosing += AutoClickerForm_FormClosing;
            // enable form to receive key events even if child controls focused
            this.KeyPreview = true;
        }

        void InitializeComponents()
        {
            statusLabel = new Label()
            {
                Text = "请先设置一个热键",
                AutoSize = false,
                TextAlign = ContentAlignment.MiddleCenter,
                Dock = DockStyle.Top,
                Height = 40
            };

            var keyPanel = new Panel() { Height = 30, Dock = DockStyle.Top, Padding = new Padding(10) };
            var keyLabel = new Label() { Text = "当前热键:", AutoSize = true, Location = new Point(10, 5) };
            currentKeyLabel = new Label() { Text = "未设置", AutoSize = true, Location = new Point(90, 5) };
            keyPanel.Controls.Add(keyLabel);
            keyPanel.Controls.Add(currentKeyLabel);

            setKeyButton = new Button() { Text = "设置热键", Width = 100, Height = 30, Location = new Point(120, 70) };
            startButton = new Button() { Text = "开始", Width = 100, Height = 30, Location = new Point(30, 110) };
            stopButton = new Button() { Text = "停止", Width = 100, Height = 30, Location = new Point(200, 110) };

            startButton.Enabled = false;
            stopButton.Enabled = false;

            Controls.Add(statusLabel);
            Controls.Add(keyPanel);
            Controls.Add(setKeyButton);
            Controls.Add(startButton);
            Controls.Add(stopButton);

            setKeyButton.Click += SetKeyButton_Click;
            startButton.Click += StartButton_Click;
            stopButton.Click += StopButton_Click;
            this.KeyDown += AutoClickerForm_KeyDown;
        }

        // 进入等待按键模式
        private bool waitingForKey = false;
        private void SetKeyButton_Click(object sender, EventArgs e)
        {
            waitingForKey = true;
            setKeyButton.Text = "请按下一个键...";
            setKeyButton.Enabled = false;
            statusLabel.Text = "等待按键：请按下你想设置的热键";
        }

        // 捕获按键设为热键
        private void AutoClickerForm_KeyDown(object sender, KeyEventArgs e)
        {
            if (!waitingForKey) return;

            // 保存 Keys
            selectedKey = e.KeyCode;
            string name = KeyToFriendlyName(selectedKey.Value);
            currentKeyLabel.Text = $"'{name}'";
            statusLabel.Text = "热键已设置，可以开始了";
            startButton.Enabled = true;

            waitingForKey = false;
            setKeyButton.Text = "设置热键";
            setKeyButton.Enabled = true;

            // 阻止事件进一步处理（可选）
            e.Handled = true;
        }

        // friendly name for display
        private string KeyToFriendlyName(Keys k)
        {
            // 一些特殊键显示更友好
            switch (k)
            {
                case Keys.Space: return "Space";
                case Keys.ControlKey: return "Ctrl";
                case Keys.Menu: return "Alt";
                case Keys.ShiftKey: return "Shift";
                case Keys.LWin:
                case Keys.RWin:
                case Keys.LShiftKey:
                case Keys.RShiftKey:
                case Keys.LControlKey:
                case Keys.RControlKey:
                case Keys.LMenu:
                case Keys.RMenu:
                    return k.ToString();
                default:
                    return k.ToString();
            }
        }

        // 启动后台点击线程
        private void StartButton_Click(object sender, EventArgs e)
        {
            if (selectedKey == null)
            {
                statusLabel.Text = "错误：请先设置一个有效的热键";
                return;
            }

            runThread = true;
            clickThread = new Thread(() => ClickLoop(selectedKey.Value));
            clickThread.IsBackground = true;
            clickThread.Start();

            startButton.Enabled = false;
            stopButton.Enabled = true;
            setKeyButton.Enabled = false;
        }

        // 停止线程
        private void StopButton_Click(object sender, EventArgs e)
        {
            StopClicking();
            statusLabel.Text = "已停止。可以重新开始或设置新热键。";
        }

        private void StopClicking()
        {
            runThread = false;
            if (clickThread != null && clickThread.IsAlive)
            {
                // 等待线程结束（短时间）
                if (!clickThread.Join(500))
                {
                    try { clickThread.Abort(); } catch { /* 不推荐，但作为兜底（.NET Framework） */ }
                }
            }
            clickThread = null;
            startButton.Enabled = true;
            stopButton.Enabled = false;
            setKeyButton.Enabled = true;
        }

        // 实际点击循环（检测按键按下并连续点击）
        private void ClickLoop(Keys keyToWatch)
        {
            Int32 vKey = (Int32)keyToWatch;
            this.InvokeIfRequired(() => statusLabel.Text = $"正在运行... 按住 '{KeyToFriendlyName(keyToWatch)}' 开始点击");

            try
            {
                while (runThread)
                {
                    // 检查键是否按下（高位为1表示当前按下）
                    short state = GetAsyncKeyState(vKey);
                    bool isPressed = ((state & 0x8000) != 0);

                    if (isPressed)
                    {
                        // 发送鼠标左键按下和抬起（一次点击）
                        INPUT[] inputs = new INPUT[2];

                        inputs[0].type = INPUT_MOUSE;
                        inputs[0].U.mi = new MOUSEINPUT { dx = 0, dy = 0, mouseData = 0, dwFlags = MOUSEEVENTF_LEFTDOWN, time = 0, dwExtraInfo = IntPtr.Zero };

                        inputs[1].type = INPUT_MOUSE;
                        inputs[1].U.mi = new MOUSEINPUT { dx = 0, dy = 0, mouseData = 0, dwFlags = MOUSEEVENTF_LEFTUP, time = 0, dwExtraInfo = IntPtr.Zero };

                        SendInput((uint)inputs.Length, inputs, Marshal.SizeOf(typeof(INPUT)));

                        Thread.Sleep(10); // 控制点击速度，和原脚本一致（可根据需要调整）
                    }
                    else
                    {
                        Thread.Sleep(10); // 键未按下，短暂等待以减少 CPU 占用
                    }
                }
            }
            catch (ThreadAbortException) { /* 线程被强制结束 */ }
            finally
            {
                this.InvokeIfRequired(() =>
                {
                    statusLabel.Text = "已停止";
                    startButton.Enabled = true;
                    stopButton.Enabled = false;
                    setKeyButton.Enabled = true;
                });
            }
        }

        private void AutoClickerForm_FormClosing(object sender, FormClosingEventArgs e)
        {
            StopClicking();
        }
    }

    // 辅助扩展：在非 UI 线程安全调用控件
    static class ControlExtensions
    {
        public static void InvokeIfRequired(this Control control, Action action)
        {
            if (control == null || control.IsDisposed) return;
            if (control.InvokeRequired)
            {
                try { control.Invoke(action); }
                catch { /* 忽略已关闭窗口引发的异常 */ }
            }
            else
            {
                action();
            }
        }
    }
}
