; AutoHotkey v2 脚本
; 按住B键时不断点击鼠标左键，松开B键时停止点击

b::
{
    While GetKeyState("b", "P")
    {
        Click  ; 点击鼠标左键
        Sleep 50  ; 延迟50毫秒，可根据需要调整点击速度
    }
}
