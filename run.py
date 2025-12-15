# run.py
from app import create_app

# 调用工厂函数创建 Flask 应用实例
app = create_app()

if __name__ == '__main__':
    # debug=True 模式下，修改代码会自动重启，方便开发
    # port=5000 是 Flask 默认端口
    app.run(debug=True, host='127.0.0.1', port=5000)