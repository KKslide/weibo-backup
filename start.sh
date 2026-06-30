#!/bin/bash

echo "=================================="
echo "微博数据备份系统启动脚本"
echo "=================================="

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "错误: 未找到 .env 配置文件"
    echo "请先复制 .env.example 为 .env 并填入你的 Cookie"
    exit 1
fi

# 检查 Cookie 是否配置
if grep -q "WEIBO_COOKIE=$" .env; then
    echo "错误: 请在 .env 文件中配置 WEIBO_COOKIE"
    echo ""
    echo "获取方法:"
    echo "1. 打开 Chrome，登录 weibo.com"
    echo "2. 按 F12 打开开发者工具"
    echo "3. 切换到 Network 标签"
    echo "4. 刷新页面，点击任意请求"
    echo "5. 复制 Request Headers 中的 Cookie 值"
    exit 1
fi

echo ""
echo "请选择操作:"
echo "1. 运行爬虫（完整爬取）"
echo "2. 运行爬虫（只爬取评论）"
echo "3. 启动后端服务"
echo "4. 启动前端"
echo "5. 启动全部服务"
echo ""
read -p "请输入选项 (1-5): " choice

case $choice in
    1)
        echo "开始爬取微博数据..."
        python crawler/main.py
        ;;
    2)
        echo "开始爬取评论..."
        python crawler/main.py --comments-only
        ;;
    3)
        echo "启动后端服务..."
        cd server && python main.py
        ;;
    4)
        echo "启动前端..."
        cd frontend && npm run dev
        ;;
    5)
        echo "启动全部服务..."
        echo ""
        echo "1. 启动后端服务 (端口 8000)..."
        cd server && python main.py &
        BACKEND_PID=$!

        echo "2. 启动前端服务 (端口 5173)..."
        cd ../frontend && npm run dev &
        FRONTEND_PID=$!

        echo ""
        echo "服务已启动:"
        echo "  后端: http://localhost:8000"
        echo "  前端: http://localhost:5173"
        echo ""
        echo "按 Ctrl+C 停止服务"

        # 等待子进程
        wait $BACKEND_PID $FRONTEND_PID
        ;;
    *)
        echo "无效选项"
        exit 1
        ;;
esac
