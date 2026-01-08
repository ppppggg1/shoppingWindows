from flask import Flask, render_template, request, jsonify
from flask_cors import CORS  # 新增
from dbutils.pooled_db import PooledDB
import pymysql
from datetime import datetime
app = Flask(__name__)
CORS(app)
pool = PooledDB(
    creator=pymysql,
    maxconnections=10,
    mincached=3,
    maxcached=3,
    blocking=True,
    setsession=[],
    ping=0,
    host='192.168.203.131',
    port=3306,
    user='root',
    passwd='1234',
    charset='utf8',
    db='itcast'
)


# 通用数据库查询函数（封装重复逻辑）
def query_db(sql, params=None):
    """
    通用数据库查询函数
    :param sql: 查询SQL语句
    :param params: SQL参数
    :return: 查询结果列表
    """
    conn = None
    cursor = None
    try:
        # 获取数据库连接
        conn = pool.connection()
        # 使用字典游标，返回的结果是字典格式，更易处理
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 执行SQL
        cursor.execute(sql, params or ())
        # 获取查询结果
        results = cursor.fetchall()

        return {
            'success': True,
            'data': results,
            'message': '查询成功'
        }
    except Exception as e:
        print(f"数据库查询异常: {str(e)}")
        return {
            'success': False,
            'data': [],
            'message': f'查询失败: {str(e)}'
        }
    finally:
        # 确保游标和连接关闭
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# 登录页面
@app.route('/')
def login():
    return render_template("login.html")


# 注册页面
@app.route('/signup')
def signup():
    return render_template("signup.html")


# 忘记密码页面
@app.route('/forgetpass')
def forgetpass():
    return render_template("forgetpass.html")


# 主页面
@app.route('/root')
def root():
    return render_template("root.html")


# 比对user与传输过来的区别
@app.route('/api/verify-user', methods=['POST', 'GET'])
def verifyuser():
    try:
        # 获取JSON格式的请求数据
        request_data = request.get_json()
        if not request_data:
            return jsonify({
                'success': False,
                'message': '请求数据格式错误，请使用JSON格式'
            })

        username = request_data.get('username')
        passwd = request_data.get('password')

        print("获取到的账号：", username, "密码：", passwd)

        # 非空校验
        if not username or not passwd:
            return jsonify({
                'success': False,
                'message': '账号和密码不能为空'
            })

        # 连接数据库，查询用户表
        result = query_db(
            "SELECT id, username, password FROM sys_user WHERE username = %s AND status = 1",
            (username,)
        )

        if not result['success']:
            return jsonify({
                'success': False,
                'message': '数据库查询失败'
            })

        user = result['data'][0] if result['data'] else None

        if not user:
            return jsonify({
                'success': False,
                'message': '账号不存在或已被禁用'
            })

        # 密码匹配校验（生产环境请使用加密方式！）
        if passwd != user['password']:
            return jsonify({
                'success': False,
                'message': '密码错误，请重新输入'
            })

        # 验证通过
        return jsonify({
            'success': True,
            'message': '验证通过',
            'userId': user['id'],
            'username': user['username']
        })

    except Exception as e:
        print("验证异常：", str(e))
        return jsonify({
            'success': False,
            'message': '服务器内部错误，请稍后重试'
        })


# ===================== 新增：购物深度分析接口 =====================

# 接口1：购物深度-行为分布
@app.route('/api/shoppingLevel/behavior', methods=['GET'])
def shopping_level_behavior():
    """
    获取不同购物深度用户的行为分布数据
    返回格式适配前端ECharts展示
    """
    # 执行查询
    sql = """
    SELECT 
        shopping_level,
        count(CASE WHEN btag = 'pv' THEN 1 END) as pv_count,
        count(CASE WHEN btag = 'cart' THEN 1 END) as cart_count,
        count(CASE WHEN btag = 'fav' THEN 1 END) as fav_count,
        count(CASE WHEN btag = 'buy' THEN 1 END) as buy_count
    FROM shopping_clk 
    GROUP BY shopping_level;
    """

    result = query_db(sql)

    if not result['success']:
        return jsonify({
            'code': 500,
            'data': {},
            'msg': result['message']
        })

    # 格式化数据适配前端ECharts
    x_axis = []  # 购物深度
    pv_data = []  # 浏览数据
    cart_data = []  # 加购数据
    fav_data = []  # 收藏数据
    buy_data = []  # 购买数据

    for item in result['data']:
        x_axis.append(f"购物深度{item['shopping_level']}")
        pv_data.append(item['pv_count'] or 0)
        cart_data.append(item['cart_count'] or 0)
        fav_data.append(item['fav_count'] or 0)
        buy_data.append(item['buy_count'] or 0)

    # 构造前端需要的格式
    response_data = {
        'xAxis': x_axis,
        'series': [
            {'name': '浏览(pv)', 'data': pv_data},
            {'name': '加购(cart)', 'data': cart_data},
            {'name': '收藏(fav)', 'data': fav_data},
            {'name': '购买(buy)', 'data': buy_data}
        ]
    }
    print(response_data)
    return jsonify({
        'code': 200,
        'data': response_data,
        'msg': '查询成功'
    })


# 接口2：购物深度-时间趋势
@app.route('/api/shoppingLevel/trend', methods=['GET'])
def shopping_level_trend():
    """
    获取不同购物深度用户的时间趋势数据
    """
    # 执行查询
    sql = """
    SELECT 
        time_stamp,
        shopping_level,
        count(CASE WHEN btag = 'pv' THEN 1 END) as pv_count
    FROM shopping_clk 
    GROUP BY time_stamp, shopping_level
    ORDER BY time_stamp;
    """

    result = query_db(sql)

    if not result['success']:
        return jsonify({
            'code': 500,
            'data': {},
            'msg': result['message']
        })

    # 整理数据：先获取所有时间戳和购物深度
    time_stamps = sorted(list(set([item['time_stamp'] for item in result['data']])))
    shopping_levels = sorted(list(set([item['shopping_level'] for item in result['data']])))

    # 格式化时间戳（如果是datetime类型，转换为HH:MM格式）
    x_axis = []
    for ts in time_stamps:
        if isinstance(ts, datetime):
            x_axis.append(ts.strftime('%H:%M'))
        else:
            # 如果是字符串，直接使用（建议数据库中time_stamp存储为时间格式）
            x_axis.append(str(ts)[:5] if len(str(ts)) >= 5 else str(ts))

    # 构造各购物深度的趋势数据
    series = []
    for level in shopping_levels:
        level_data = []
        for ts in time_stamps:
            # 查找对应时间戳和购物深度的数据
            item = next((i for i in result['data'] if i['time_stamp'] == ts and i['shopping_level'] == level), None)
            level_data.append(item['pv_count'] or 0 if item else 0)

        series.append({
            'name': f'购物深度{level}',
            'data': level_data
        })

    # 构造响应数据
    response_data = {
        'xAxis': x_axis,
        'series': series
    }

    return jsonify({
        'code': 200,
        'data': response_data,
        'msg': '查询成功'
    })


# 接口3：购物深度-转化率
@app.route('/api/shoppingLevel/convert', methods=['GET'])
def shopping_level_convert():
    """
    获取不同购物深度用户的转化率数据
    """
    # 执行查询
    sql = """
    SELECT 
        shopping_level,
        SUM(clk) as total_clk,
        COUNT(clk) as total_count,
        ROUND(SUM(clk) / COUNT(clk) * 100, 2) as click_conversion_rate,
        # 补充购买转化率（假设buy标识为1表示购买）
        SUM(CASE WHEN btag = 'buy' THEN 1 ELSE 0 END) as total_buy,
        ROUND(SUM(CASE WHEN btag = 'buy' THEN 1 ELSE 0 END) / COUNT(clk) * 100, 2) as buy_conversion_rate
    FROM shopping_clk 
    GROUP BY shopping_level;
    """

    result = query_db(sql)

    if not result['success']:
        return jsonify({
            'code': 500,
            'data': {},
            'msg': result['message']
        })

    # 格式化数据
    x_axis = []
    click_conversion_data = []
    buy_conversion_data = []

    for item in result['data']:
        x_axis.append(f"购物深度{item['shopping_level']}")
        # 处理空值和异常值
        click_rate = item['click_conversion_rate'] if item['click_conversion_rate'] else 0.0
        buy_rate = item['buy_conversion_rate'] if item['buy_conversion_rate'] else 0.0

        click_conversion_data.append(click_rate)
        buy_conversion_data.append(buy_rate)

    # 构造响应数据
    response_data = {
        'xAxis': x_axis,
        'series': [
            {'name': '点击转化率', 'data': click_conversion_data},
            {'name': '购买转化率', 'data': buy_conversion_data}
        ]
    }

    return jsonify({
        'code': 200,
        'data': response_data,
        'msg': '查询成功'
    })

@app.route("/pidclkany")
def pidclkany():
    """
    获取各个资源位的点击率
    :return: json
    """
    sql = "select pid, clk_percent from pid_clk"

    result = query_db(sql)
    if  not result['success']:
        return jsonify({
            'code' : 500,
             'data' : {},
            'msg' : result['message']
        })
    print(result)
    xAxis = []
    yAxis = []
    for i in result['data']:
        xAxis.append(i['pid'])
        yAxis.append(i['clk_percent'])
    response_data = {
        'xAxis': xAxis,
        'series': [
            {'name': '点击转化率', 'data': yAxis}

        ]
    }
    return jsonify({
        'code': 200,
        'data': response_data,
        'msg': '查询成功'
    })

@app.route('/hour_click_rate')
def hour_click_rate():
    """
        获取每小时的点击率
        :return: json
        """
    sql = "select hour, click_rate from hourly_click_rate"

    result = query_db(sql)
    if not result['success']:
        return jsonify({
            'code': 500,
            'data': {},
            'msg': result['message']
        })

    xAxis = []
    yAxis = []
    for i in result['data']:
        xAxis.append(i['hour'])
        yAxis.append(float(i['click_rate']))
    response_data = {
        'xAxis': xAxis,
        'series': [
            {'name': '点击转化率', 'data': yAxis}

        ]
    }
    return jsonify({
        'code': 200,
        'data': response_data,
        'msg': '查询成功'
    })
@app.route("/citybrandclick")
def citybrandclick():
    """
    获取分组柱状图数据（按城市等级分组，品牌为系列）
    :return: json
    """
    # 查询所有城市等级-品牌-点击率数据
    sql = "select city_level, brand, click_rate from city_brand_preference"
    result = query_db(sql)

    if not result['success']:
        return jsonify({
            'code': 500,
            'data': {},
            'msg': result['message']
        })

    # 数据重组：适配分组柱状图
    # 1. 提取所有唯一的城市等级（X轴）和品牌（系列）
    city_levels = sorted(list(set([item['city_level'] for item in result['data']])))
    brands = sorted(list(set([item['brand'] for item in result['data']])))

    # 2. 构建系列数据：每个品牌对应各城市等级的点击率
    series = []
    for brand in brands:
        brand_data = []
        for level in city_levels:
            # 查找该品牌在该城市等级的点击率，无数据则填0
            click_rate = 0
            for item in result['data']:
                if item['city_level'] == level and item['brand'] == brand:
                    click_rate = item['click_rate']
                    break
            brand_data.append(click_rate)
        series.append({
            "name": f"品牌{brand}",  # 系列名称（如品牌1、品牌2）
            "type": "bar",  # 柱状图类型
            "data": brand_data  # 该品牌在各城市等级的点击率
        })

    # 最终返回给前端的格式
    response_data = {
        'xAxis': city_levels,  # X轴：城市等级
        'series': series       # 系列：各品牌的点击率数据
    }

    return jsonify({
        'code': 200,
        'data': response_data,
        'msg': '查询成功'
    })


if __name__ == '__main__':
    pidclkany()
    app.run(host='0.0.0.0', port=5000, debug=True)