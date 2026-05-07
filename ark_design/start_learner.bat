@echo off
REM PPT 设计思维自动学习引擎
REM 扫描 ppt/ 目录下的新文件，提取文字、图片，构建知识库
chcp 65001 >nul
echo ========================================
echo  PPT 设计思维自动学习引擎
echo ========================================
echo.
/c/Python314/python "f:\code\ARK Design\ppt_learner.py"
echo.
echo 按任意键退出...
pause >nul
