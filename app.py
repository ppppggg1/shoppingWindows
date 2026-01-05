from flask import Flask, render_template, request, jsonify
from dbutils.pooled_db import PooledDB
import pymysql
app = Flask(__name__)
#定义数据库连接池
pool = PooledDB(
    creator=pymysql,
    maxconnections=10,
    mincached=3,
    maxcached=3,
    blocking=True,
    setsession=[],
    ping=0,
    host='192.168.203.131',port=3306,user='root',passwd='1234', charset='utf8', db='itcast'
)
#登录页面
@app.route('/')
def login():
    return render_template("login.html")

#注册页面
@app.route('/signup')
def signup():
    return render_template("signup.html")
#忘记密码页面
@app.route('/forgetpass')
def forgetpass():
    return render_template("forgetpass.html")


#主页面
@app.route('/dataview')
def dataview():
    return render_template("root.html")




#比对user与传输过来的区别
@app.route('/api/verify-user',methods=['POST', 'GET'])
def verifyuser():
    try:
        # 问题1修正：获取JSON格式的请求数据（匹配前端发送格式）
        # 方式1：直接获取JSON对象（推荐，前端传JSON时使用）
        request_data = request.get_json()
        if not request_data:  # 判断是否获取到JSON数据
            return jsonify({
                'success': False,
                'message': '请求数据格式错误，请使用JSON格式'
            })

        username = request_data.get('username')
        passwd = request_data.get('password')

        # 可选：若你坚持使用表单格式提交，前端需调整，后端可保留 request.form.get（注释上方JSON代码，启用下方）
        # username = request.form.get("username")
        # passwd = request.form.get("password")
        # if not username or not passwd:
        #     return jsonify({'success': False, 'message': '账号或密码不能为空'})

        print("获取到的账号：", username, "密码：", passwd)
        # 1. 非空校验
        if not username or not passwd:
            return jsonify({
                'success': False,
                'message': '账号和密码不能为空'
            })

        # 2. 连接数据库，查询用户表
        # 创建数据库连接
        conn = pool.connection()
        cursor = conn.cursor()  # 返回字典格式数据

        try:
            # 查询sys_user表中是否存在该用户（状态为1：正常账号）
            sql = "SELECT id, username, password FROM sys_user WHERE username = %s AND status = 1"
            cursor.execute(sql, (username,))  # 使用参数化查询，防止SQL注入
            user = cursor.fetchone()  # 获取单个用户记录

            if not user:
                # 无该用户（或账号被禁用）
                return jsonify({
                    'success': False,
                    'message': '账号不存在或已被禁用'
                })

            # 3. 密码匹配校验（注意：此处假设数据库存储的是明文密码，仅作演示！）
            # 生产环境必须使用加密校验（如Bcrypt/SHA256），后续会补充

            db_password = user[2]
            if passwd != db_password:
                return jsonify({
                    'success': False,
                    'message': '密码错误，请重新输入'
                })

            # 4. 验证通过，返回成功结果（可携带用户ID等信息）
            return jsonify({
                'success': True,
                'message': '验证通过',
                'userId': user[0],
                'username': user[1]
            })

        finally:
            # 关闭游标和连接，释放资源
            cursor.close()
            conn.close()

    except Exception as e:
        # 捕获异常，返回错误信息
        print("验证异常：", str(e))
        return jsonify({
            'success': False,
            'message': '服务器内部错误，请稍后重试'
        })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
