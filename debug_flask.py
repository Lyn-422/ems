import os
from app import create_app

app = create_app()

print("="*50)
print("Flask 路径诊断报告")
print("="*50)
print(f"1. 项目根路径 (root_path): {app.root_path}")
print(f"2. 模板文件夹名 (template_folder): {app.template_folder}")

# 拼接出 Flask 认为的绝对模板路径
expected_template_path = os.path.join(app.root_path, app.template_folder)
print(f"3. Flask 正在寻找模板的绝对路径: \n   {expected_template_path}")

print("-" * 30)
print("4. 检查该路径是否存在:", os.path.exists(expected_template_path))

if os.path.exists(expected_template_path):
    print("5. 该文件夹下的文件列表:")
    for root, dirs, files in os.walk(expected_template_path):
        level = root.replace(expected_template_path, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print(f"{subindent}{f}")
else:
    print("❌ 严重错误：Flask 指向了一个不存在的文件夹！")

print("="*50)