import base64
import os
def create(i,o):
    try:
        with open(i,"rb") as f:
            b64=base64.b64encode(f.read()).decode('utf-8')
            e=i.split('.')[-1]
            print(e);
            with open(f"{o}.bat","w") as w:
                w.write('@echo off\n')
                w.write(f'set v="%appdata%\\extracted.{e}"\n')
                w.write('del %v% >NUL 2>NUL\n')
                w.write('certutil -decode "%~f0" %v% >NUL 2>NUL\n')
                w.write('start "" %v%\n')
                w.write('exit\n\n')
                w.write('-----BEGIN CERTIFICATE-----\n')
                w.write(b64 + "\n")
                w.write('-----END CERTIFICATE-----\n')
        print(f"{o}.bat 文件创建成功")
        os.system("pause")
    except FileNotFoundError:
        print("错误：无法找到指定的文件："+str(i))
        os.system("pause")
os.system("title 任意文件转bat")
print("输入要求：不带引号，避免特殊字符")
i=input("请输入源文件路径：")
o=input("请输入成品bat文件路径（最后无需扩展名.bat）：")
create(i,o)
