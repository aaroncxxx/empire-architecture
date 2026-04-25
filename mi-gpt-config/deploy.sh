#!/bin/bash
# Mi-GPT 部署脚本 - L05B (小爱音箱 Play) + OpenClaw

echo "🦞 Mi-GPT 部署脚本"
echo "===================="

# 1. 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 未安装 Node.js，请先安装 Node.js 18+"
    exit 1
fi
echo "✅ Node.js $(node -v)"

# 2. 克隆 mi-gpt
if [ ! -d "mi-gpt" ]; then
    echo "📦 克隆 mi-gpt..."
    git clone https://github.com/idootop/mi-gpt.git
fi

# 3. 复制配置文件
echo "📝 写入配置..."
cp .env mi-gpt/.env
cp .migpt.js mi-gpt/.migpt.js

# 4. 安装依赖
echo "📦 安装依赖..."
cd mi-gpt && npm install

echo ""
echo "✅ 部署完成！"
echo ""
echo "⚠️  请先编辑 .env 文件，填入你的小米账号密码："
echo "   MI_PASS=你的小米账号密码"
echo ""
echo "启动命令："
echo "   cd mi-gpt && npm start"
echo ""
echo "保持运行（推荐用 pm2 或 screen）："
echo "   npm install -g pm2"
echo "   pm2 start npm --name migpt -- start"
