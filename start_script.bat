
@echo on
setlocal

REM 设置环境变量

@REM python前台台运行
set PYTHON_PATH=D:\OnmyojiAutoScript\ljxun\toolkit\python.exe
@REM pythonw后台运行
@REM set PYTHON_PATH=D:\OnmyojiAutoScript\ljxun\toolkit\pythonw.exe

@REM 脚本路径
set SCRIPT_PATH=D:\OnmyojiAutoScript\ljxun\start_script.py


REM 启动第一个脚本
start   %PYTHON_PATH% "%SCRIPT_PATH%" DU
@REM start  /min %PYTHON_PATH% "%SCRIPT_PATH%" DU


REM 启动第二个脚本
start  %PYTHON_PATH% "%SCRIPT_PATH%" MI
@REM start /min %PYTHON_PATH% "%SCRIPT_PATH%" MI

endlocal

@REM python前台台运行
@REM start /mim D:\OnmyojiAutoScript\ljxun\toolkit\python.exe "D:\OnmyojiAutoScript\ljxun\start_script.py"  DU
@REM start /min D:\OnmyojiAutoScript\ljxun\toolkit\python.exe "D:\OnmyojiAutoScript\ljxun\start_script.py"  MI

@REM pythonw后台运行
@REM start D:\OnmyojiAutoScript\ljxun\toolkit\pythonw.exe "D:\OnmyojiAutoScript\ljxun\start_script.py"  DU
@REM start D:\OnmyojiAutoScript\ljxun\toolkit\pythonw.exe "D:\OnmyojiAutoScript\ljxun\start_script.py"  MI



@REM ### @REM 和 REM 的区别
@REM
@REM 1. **功能上的区别**：
@REM    - **REM**：是批处理脚本中的注释命令，用于在代码中添加注释。REM 后面的内容将被解释器忽略，不会被执行。
@REM    - **@REM**：与 REM 类似，也是用于添加注释，但前面的 `@` 符号会抑制该命令本身的回显。也就是说，使用 `@REM` 时，命令行窗口不会显示 `REM` 这个命令本身。
@REM
@REM 2. **显示效果的区别**：
@REM    - 如果在批处理脚本的第一行没有使用 `@echo off` 关闭命令回显，那么使用 `REM` 时，命令行窗口会显示 `REM` 命令及其后面的注释内容。
@REM    - 使用 `@REM` 则不会显示 `REM` 命令及其后面的注释内容，因为 `@` 抑制了命令的回显。
@REM
@REM 3. **实际使用场景**：
@REM    - **REM**：适用于不需要特别隐藏注释命令的情况，适合调试或需要查看命令执行过程的场景。
@REM    - **@REM**：适用于希望保持批处理脚本输出整洁，不希望看到注释命令的情况，特别是在正式环境中使用时。
@REM
@REM ### 示例
@REM
@REM ```batch
@REM @echo on
@REM REM 这是一条普通的注释，命令行会显示 "REM 这是一条普通的注释"
@REM @REM 这是一条带 @ 的注释，命令行不会显示这条注释
@REM ```
@REM
@REM
@REM ### 结论
@REM - 如果你希望在批处理脚本运行时不显示注释命令及其内容，建议使用 `@REM`。
@REM - 如果你不在乎命令行是否显示注释命令，或者在调试过程中希望看到所有命令的执行情况，可以使用 `REM`。
@REM
@REM 在你的 `start_script.bat` 文件中，使用 `@REM` 是合理的，因为它确保了批处理脚本运行时不会显示这些注释行，从而保持输出的整洁。


