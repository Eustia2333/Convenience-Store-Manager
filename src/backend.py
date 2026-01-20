import pymysql
from db_setup import DatabaseManager, DB_NAME
from datetime import datetime
import time

class AuthLogic:
    """
    负责用户认证与权限管理
    """

    def __init__(self):
        self.db = DatabaseManager(DB_NAME)

    def login(self, username, password):
        """
        验证登录
        """
        self.db.connect()
        sql = "SELECT id, username, role FROM users WHERE username=%s AND password=%s"
        try:
            self.db.cursor.execute(sql, (username, password))
            user = self.db.cursor.fetchone()
            return user  # 成功返回用户信息字典，失败返回 None
        except Exception as e:
            print(f"[Login Error] {e}")
            return None
        finally:
            self.db.close()


class ProductLogic:
    """
    负责商品增删查改
    """

    def __init__(self):
        self.db = DatabaseManager(DB_NAME)

    def add_product(self, name, category, buy_price, sell_price, stock, min_stock_alert, expire_date):

        self.db.connect()
        sql = """
        INSERT INTO products (name, category, buy_price, sell_price, stock, min_stock_alert, expire_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        try:
            success = self.db.execute_query(sql, (name, category, buy_price, sell_price, stock, min_stock_alert, expire_date))
            return success
        finally:
            self.db.close()

    def delete_product(self, product_id):
        """删除商品"""
        self.db.connect()
        sql = "DELETE FROM products WHERE id=%s"
        try:
            return self.db.execute_query(sql, (product_id,))
        finally:
            self.db.close()

    def update_product(self, product_id, name, category, buy_price, sell_price, stock, min_stock_alert, expire_date):
        self.db.connect()
        sql = """
        UPDATE products 
        SET name=%s, category=%s, buy_price=%s, sell_price=%s, stock=%s, min_stock_alert=%s, expire_date=%s
        WHERE id=%s
        """
        try:
            return self.db.execute_query(sql, (name, category, buy_price, sell_price, stock, min_stock_alert, expire_date, product_id))
        finally:
            self.db.close()

    def get_all_products(self):
        """获取所有商品"""
        self.db.connect()
        try:
            self.db.cursor.execute("SELECT * FROM products ORDER BY id DESC")
            return self.db.cursor.fetchall()
        finally:
            self.db.close()

    def get_expiring_products(self, days=7):
        """查询即将过期（包含已经过期）的商品"""
        self.db.connect()
        sql = """
        SELECT * FROM products 
        WHERE expire_date IS NOT NULL 
        AND expire_date <= DATE_ADD(CURDATE(), INTERVAL %s DAY)
        ORDER BY expire_date ASC
        """
        try:
            self.db.cursor.execute(sql, (days,))
            return self.db.cursor.fetchall()
        finally:
            self.db.close()

    def search_products(self, keyword):
        """
        搜索功能
        """
        self.db.connect()

        sql = """
        SELECT * FROM products 
        WHERE 
            name LIKE %s 
            OR category LIKE %s 
        """

        pattern = f"%{keyword}%"

        try:
            self.db.cursor.execute(sql, (pattern, pattern))
            return self.db.cursor.fetchall()
        finally:
            self.db.close()

    def get_low_stock_products(self):
        """获取低库存预警列表"""
        self.db.connect()
        sql = "SELECT * FROM products WHERE stock < min_stock_alert"
        try:
            self.db.cursor.execute(sql)
            return self.db.cursor.fetchall()
        finally:
            self.db.close()

class UserLogic:
    """负责用户/员工管理"""

    def __init__(self):
        self.db = DatabaseManager(DB_NAME)

    def get_all_clerks(self):
        """获取所有售货员"""
        self.db.connect()
        try:
            # 只获取售货员，不显示管理员
            self.db.cursor.execute("SELECT id, username, role, created_at FROM users WHERE role='Clerk'")
            return self.db.cursor.fetchall()
        finally:
            self.db.close()

    def add_clerk(self, username, password):
        """添加新售货员"""
        self.db.connect()
        try:
            sql = "INSERT INTO users (username, password, role) VALUES (%s, %s, 'Clerk')"
            return self.db.execute_query(sql, (username, password))
        finally:
            self.db.close()

    def delete_user(self, user_id):
        """删除用户"""
        self.db.connect()
        try:
            self.db.cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
            return True, "删除成功"
        except pymysql.Error as e:

            if e.args[0] == 1451:
                return False, "删除失败：该员工已处理过订单，\n数据库存在关联记录，无法物理删除！"
            return False, f"数据库错误: {e}"
        finally:
            self.db.close()

class SalesLogic:
    def __init__(self):
        self.db = DatabaseManager(DB_NAME)

    def checkout(self, clerk_id, cart_items, member_id=None):
        """
        处理结账事务
        :param clerk_id: 收银员ID
        :param cart_items: 购物车列表
        :param member_id: 会员ID (新增参数，默认为None)
        """
        if not cart_items:
            #如果失败也需要返回3个值 (False, 消息, None)
            return False, "购物车为空", None

        # 生成唯一订单号 (时间戳)
        order_id = time.strftime('%Y%m%d%H%M%S')

        self.db.connect()
        conn = self.db.conn
        cursor = self.db.cursor
        try:
            conn.begin()
            total_amount = 0

            for item in cart_items:
                p_id = item['id']
                buy_qty = int(item['buy_qty'])

                # 获取当前库存和进价 (悲观锁)
                cursor.execute("SELECT name, stock, buy_price, sell_price FROM products WHERE id=%s FOR UPDATE",
                               (p_id,))
                product = cursor.fetchone()

                if not product or product['stock'] < buy_qty:
                    raise Exception(f"商品 {product['name']} 库存不足")

                # 扣库存
                cursor.execute("UPDATE products SET stock = stock - %s WHERE id=%s", (buy_qty, p_id))

                # 插入销售记录
                item_total = float(product['sell_price']) * buy_qty


                sql = """
                INSERT INTO sales (order_id, product_id, user_id, quantity, buy_price_snapshot, sell_price_snapshot, total_price, sale_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """
                cursor.execute(sql, (
                order_id, p_id, clerk_id, buy_qty, product['buy_price'], product['sell_price'], item_total))

                total_amount += item_total

            # --- 积分逻辑 ---
            points_added = 0
            if member_id:
                # 1元 = 1分
                points_added = int(total_amount)
                cursor.execute("UPDATE members SET points = points + %s WHERE id=%s", (points_added, member_id))

            conn.commit()

            # 构建成功消息
            msg = f"结账成功! 订单号:{order_id} 总额:¥{total_amount:.2f}"
            if member_id:
                msg += f"\n会员积分 +{points_added}"

            # 构建小票数据字典
            receipt_data = {
                "order_id": order_id,
                "items": cart_items,
                "total": total_amount,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "member_points": points_added
            }

            return True, msg, receipt_data

        except Exception as e:
            conn.rollback()
            return False, str(e), None
        finally:
            self.db.close()

    def get_sales_report(self):
        """
        获取销售报表 (按商品分组统计)
        """
        self.db.connect()
        sql = """
        SELECT p.name, SUM(s.quantity) as total_qty, SUM(s.total_price) as total_revenue 
        FROM sales s
        JOIN products p ON s.product_id = p.id
        GROUP BY p.id, p.name
        ORDER BY total_revenue DESC
        """
        try:
            self.db.cursor.execute(sql)
            return self.db.cursor.fetchall()
        finally:
            self.db.close()

    # --- 查询订单 ---
    def get_all_orders(self, clerk_id=None):
        """店长看所有，店员看自己"""
        self.db.connect()
        sql = """
        SELECT s.id, s.order_id, p.name as product_name, u.username as clerk_name, 
               s.quantity, s.total_price, s.sale_time, s.buy_price_snapshot
        FROM sales s
        JOIN products p ON s.product_id = p.id
        JOIN users u ON s.user_id = u.id
        """
        params = []
        if clerk_id:
            sql += " WHERE s.user_id = %s"
            params.append(clerk_id)

        sql += " ORDER BY s.sale_time DESC"
        try:
            self.db.cursor.execute(sql, params)
            return self.db.cursor.fetchall()
        finally:
            self.db.close()

    # --- 修改订单 (店员权限) ---
    def modify_order_qty(self, sale_id, new_qty, operator_id):
        """修改单个销售记录的数量"""
        self.db.connect()
        conn = self.db.conn
        cursor = self.db.cursor
        try:
            conn.begin()

            # 1. 获取原订单信息
            cursor.execute("SELECT * FROM sales WHERE id=%s FOR UPDATE", (sale_id,))
            sale_rec = cursor.fetchone()
            if not sale_rec: raise Exception("订单不存在")

            old_qty = sale_rec['quantity']
            p_id = sale_rec['product_id']
            diff = new_qty - old_qty  # 正数代表多买，负数代表退货

            if diff == 0: return True, "数量未变更"

            # 2. 检查并更新库存
            # 如果是增加购买量，要检查库存；如果是减少，直接加回库存
            cursor.execute("SELECT stock FROM products WHERE id=%s FOR UPDATE", (p_id,))
            current_stock = cursor.fetchone()['stock']

            if diff > 0 and current_stock < diff:
                raise Exception("修改失败：库存不足")

            cursor.execute("UPDATE products SET stock = stock - %s WHERE id=%s", (diff, p_id))

            # 3. 更新销售记录
            new_total = float(sale_rec['sell_price_snapshot']) * new_qty
            cursor.execute("UPDATE sales SET quantity=%s, total_price=%s WHERE id=%s", (new_qty, new_total, sale_id))

            # 4. 记录操作日志
            log_msg = f"将数量从 {old_qty} 修改为 {new_qty}"
            cursor.execute(
                "INSERT INTO modification_logs (sale_id, operator_id, action_type, details) VALUES (%s, %s, 'MODIFY', %s)",
                (sale_id, operator_id, log_msg))

            conn.commit()
            return True, "修改成功"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            self.db.close()

    # --- 数据统计 (店长权限) ---
    def get_profit_stats(self):
        """计算总销售额、总净利润"""
        self.db.connect()
        # 利润 = (售价快照 - 进价快照) * 数量
        sql = """
        SELECT 
            SUM(total_price) as total_revenue,
            SUM((sell_price_snapshot - buy_price_snapshot) * quantity) as total_profit
        FROM sales
        """
        try:
            self.db.cursor.execute(sql)
            res = self.db.cursor.fetchone()
            return res if res['total_revenue'] else {'total_revenue': 0, 'total_profit': 0}
        finally:
            self.db.close()

    def get_category_pie_data(self):
        """获取分类销售占比"""
        self.db.connect()
        sql = """
        SELECT p.category, SUM(s.total_price) as value
        FROM sales s
        JOIN products p ON s.product_id = p.id
        GROUP BY p.category
        """
        try:
            self.db.cursor.execute(sql)
            return self.db.cursor.fetchall()
        finally:
            self.db.close()

    def get_top_selling_products(self, limit=5):
        """热销排行榜"""
        self.db.connect()
        sql = """
        SELECT p.name, SUM(s.quantity) as total_qty
        FROM sales s
        JOIN products p ON s.product_id = p.id
        GROUP BY p.id, p.name
        ORDER BY total_qty DESC
        LIMIT %s
        """
        try:
            self.db.cursor.execute(sql, (limit,))
            return self.db.cursor.fetchall()
        finally:
            self.db.close()

    def get_modification_logs(self):
        """获取修改记录"""
        self.db.connect()
        sql = """
        SELECT l.log_time, u.username as operator, p.name as product, l.details, s.order_id
        FROM modification_logs l
        JOIN users u ON l.operator_id = u.id
        JOIN sales s ON l.sale_id = s.id
        JOIN products p ON s.product_id = p.id
        ORDER BY l.log_time DESC
        """
        try:
            self.db.cursor.execute(sql)
            return self.db.cursor.fetchall()
        finally:
            self.db.close()

    def get_hourly_sales_stats(self):
        """获取24小时销售趋势数据 (0-23点)"""
        self.db.connect()
        # 提取 sale_time 的小时部分 (HOUR函数) 进行分组求和
        sql = """
        SELECT HOUR(sale_time) as h, SUM(total_price) as total
        FROM sales
        GROUP BY h
        ORDER BY h ASC
        """
        try:
            self.db.cursor.execute(sql)
            data = self.db.cursor.fetchall()

            # 数据清洗：确保 0-23 小时都有数据，没有的补 0
            # 转成字典方便查询 {8: 100.0, 9: 200.0 ...}
            data_dict = {item['h']: float(item['total']) for item in data}

            hours = list(range(24))  # 0到23
            totals = [data_dict.get(h, 0.0) for h in hours]  # 如果该小时没数据，填0

            return hours, totals
        finally:
            self.db.close()

    def get_minute_sales_stats(self):
        """获取今日分钟级销售趋势"""
        self.db.connect()

        sql = """
        SELECT HOUR(sale_time) as h, MINUTE(sale_time) as m, SUM(total_price) as total
        FROM sales
        WHERE DATE(sale_time) = CURDATE()
        GROUP BY h, m
        ORDER BY h ASC, m ASC
        """
        try:
            self.db.cursor.execute(sql)
            data = self.db.cursor.fetchall()

            if not data:
                return [], []

            times = []
            totals = []

            for item in data:
                # :02d 表示不足两位补0
                time_str = f"{item['h']:02d}:{item['m']:02d}"
                times.append(time_str)
                totals.append(float(item['total']))

            return times, totals
        finally:
            self.db.close()

class MemberLogic:
    """
    负责会员管理与积分变动
    """
    def __init__(self):
        self.db = DatabaseManager(DB_NAME)

    def get_member_by_phone(self, phone):
        """根据手机号查找会员"""
        self.db.connect()
        try:
            self.db.cursor.execute("SELECT * FROM members WHERE phone=%s", (phone,))
            return self.db.cursor.fetchone()
        finally:
            self.db.close()

    def register_member(self, phone, name):
        """注册新会员"""
        self.db.connect()
        try:
            sql = "INSERT INTO members (phone, name, points) VALUES (%s, %s, 0)"
            return self.db.execute_query(sql, (phone, name))
        except Exception as e:
            return False
        finally:
            self.db.close()

    def update_points(self, member_id, points_delta):
        """更新积分（正数增加，负数扣除）"""
        self.db.connect()
        try:
            sql = "UPDATE members SET points = points + %s WHERE id=%s"
            return self.db.execute_query(sql, (points_delta, member_id))
        finally:
            self.db.close()
