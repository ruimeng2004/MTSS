#!/bin/bash

# D4J 修复评估系统安装脚本
# 此脚本将安装所有必需的依赖并验证环境配置

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印函数
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "\n${GREEN}==>${NC} $1"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查 Python 版本
check_python() {
    print_step "检查 Python 版本..."
    
    if ! command_exists python3; then
        print_error "Python 3 未安装"
        print_info "请安装 Python 3.8 或更高版本"
        exit 1
    fi
    
    python_version=$(python3 --version | cut -d' ' -f2)
    print_info "Python 版本: $python_version"
    
    # 检查版本是否 >= 3.8
    major=$(echo $python_version | cut -d'.' -f1)
    minor=$(echo $python_version | cut -d'.' -f2)
    
    if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 8 ]); then
        print_error "Python 版本过低，需要 3.8 或更高版本"
        exit 1
    fi
    
    print_info "Python 版本检查通过"
}

# 检查 pip
check_pip() {
    print_step "检查 pip..."
    
    if ! command_exists pip3; then
        print_error "pip3 未安装"
        print_info "请安装 pip3"
        exit 1
    fi
    
    print_info "pip3 已安装"
}

# 创建虚拟环境
create_venv() {
    print_step "创建虚拟环境..."
    
    if [ -d "venv" ]; then
        print_warning "虚拟环境已存在，跳过创建"
    else
        python3 -m venv venv
        print_info "虚拟环境创建成功"
    fi
}

# 激活虚拟环境
activate_venv() {
    print_step "激活虚拟环境..."
    
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        print_info "虚拟环境已激活"
    else
        print_error "虚拟环境激活脚本不存在"
        exit 1
    fi
}

# 安装 Python 依赖
install_python_deps() {
    print_step "安装 Python 依赖..."
    
    if [ -f "requirements.txt" ]; then
        pip install --upgrade pip
        pip install -r requirements.txt
        print_info "主依赖安装完成"
    else
        print_warning "requirements.txt 不存在，跳过"
    fi
    
    if [ -f "evaluation/requirements.txt" ]; then
        pip install -r evaluation/requirements.txt
        print_info "评估系统依赖安装完成"
    else
        print_warning "evaluation/requirements.txt 不存在，跳过"
    fi
}

# 安装 tree-sitter
install_treesitter() {
    print_step "安装 tree-sitter..."
    
    pip install tree-sitter tree-sitter-java
    print_info "tree-sitter 安装完成"
}

# 检查 Defects4J
check_defects4j() {
    print_step "检查 Defects4J..."
    
    if ! command_exists defects4j; then
        print_warning "Defects4J 未安装或未在 PATH 中"
        print_info "请按照以下步骤安装 Defects4J:"
        print_info "1. git clone https://github.com/rjust/defects4j"
        print_info "2. cd defects4j"
        print_info "3. ./init.sh"
        print_info "4. 将 defects4j/framework/bin 添加到 PATH"
        return 1
    fi
    
    print_info "Defects4J 已安装"
    defects4j_version=$(defects4j info -p Lang | head -n 1)
    print_info "Defects4J 版本: $defects4j_version"
    
    return 0
}

# 检查 Git
check_git() {
    print_step "检查 Git..."
    
    if ! command_exists git; then
        print_error "Git 未安装"
        print_info "请安装 Git"
        exit 1
    fi
    
    git_version=$(git --version)
    print_info "$git_version"
}

# 创建配置文件
create_config() {
    print_step "创建配置文件..."
    
    if [ -f "evaluation/config.yaml" ]; then
        print_warning "配置文件已存在，跳过创建"
    else
        if [ -f "evaluation/config.example.yaml" ]; then
            cp evaluation/config.example.yaml evaluation/config.yaml
            print_info "配置文件已从示例创建"
            print_warning "请编辑 evaluation/config.yaml 配置 Defects4J 路径"
        else
            print_warning "示例配置文件不存在，跳过"
        fi
    fi
}

# 运行验证脚本
run_verification() {
    print_step "运行环境验证..."
    
    if [ -f "evaluation/verify_setup.py" ]; then
        python evaluation/verify_setup.py
        if [ $? -eq 0 ]; then
            print_info "环境验证通过"
        else
            print_warning "环境验证失败，请检查配置"
        fi
    else
        print_warning "验证脚本不存在，跳过"
    fi
}

# 运行测试
run_tests() {
    print_step "运行测试..."
    
    if [ -d "evaluation/tests" ]; then
        python -m pytest evaluation/tests/ -v
        if [ $? -eq 0 ]; then
            print_info "所有测试通过"
        else
            print_warning "部分测试失败"
        fi
    else
        print_warning "测试目录不存在，跳过"
    fi
}

# 主函数
main() {
    echo "========================================"
    echo "D4J 修复评估系统安装脚本"
    echo "========================================"
    
    # 检查基础环境
    check_python
    check_pip
    check_git
    
    # 创建和激活虚拟环境
    create_venv
    activate_venv
    
    # 安装依赖
    install_python_deps
    install_treesitter
    
    # 检查 Defects4J
    d4j_installed=0
    check_defects4j && d4j_installed=1
    
    # 创建配置
    create_config
    
    # 运行验证
    if [ $d4j_installed -eq 1 ]; then
        run_verification
    else
        print_warning "跳过环境验证（Defects4J 未安装）"
    fi
    
    # 询问是否运行测试
    echo ""
    read -p "是否运行测试？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        run_tests
    fi
    
    # 完成
    echo ""
    print_step "安装完成！"
    echo ""
    print_info "下一步："
    print_info "1. 激活虚拟环境: source venv/bin/activate"
    
    if [ $d4j_installed -eq 0 ]; then
        print_info "2. 安装 Defects4J（如果尚未安装）"
        print_info "3. 配置 evaluation/config.yaml"
    else
        print_info "2. 配置 evaluation/config.yaml（如果需要）"
    fi
    
    print_info "3. 运行评估: python -m evaluation --help"
    echo ""
}

# 运行主函数
main
