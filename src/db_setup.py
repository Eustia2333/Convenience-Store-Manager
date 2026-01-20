import pymysql
from pymysql.cursors import DictCursor

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '141596',
    'charset': 'utf8mb4',
    'autocommit': True
}

DB_NAME = 'convenience_store_db'

class DatabaseManager:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def connect(self, use_db=True):
        """建立数据库连接，开发环境下直接抛出异常以便调试"""
        if self.conn and self.conn.open:
            self.conn.ping(reconnect=True)
            self.cursor = self.conn.cursor(DictCursor)
            return

        current_config = DB_CONFIG.copy()
        if use_db and self.db_name:
            current_config['database'] = self.db_name

        self.conn = pymysql.connect(**current_config)
        self.cursor = self.conn.cursor(DictCursor)

    def close(self):
        """清理资源"""
        if self.cursor:
            self.cursor.close()
        if self.conn and self.conn.open:
            self.conn.close()

    def execute_query(self, query, params=None):
        self.connect()
        self.cursor.execute(query, params)
        return True

    def init_database(self, hard_reset=False):
        """初始化数据库结构和种子数据"""
        self.connect(use_db=False)

        if hard_reset:
            self.cursor.execute(f"DROP DATABASE IF EXISTS {self.db_name}")

        self.cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.db_name} DEFAULT CHARACTER SET utf8mb4")

        self.close()
        self.connect(use_db=True)

        self._create_tables()

        self._seed_data()

        self.close()

    def _create_tables(self):

        tables = [
            """CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(100) NOT NULL,
                role VARCHAR(20) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS members (
                id INT AUTO_INCREMENT PRIMARY KEY,
                phone VARCHAR(20) NOT NULL UNIQUE,
                name VARCHAR(50),
                points INT DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",

            """CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                category VARCHAR(50) NOT NULL,
                buy_price DECIMAL(10, 2) NOT NULL,
                sell_price DECIMAL(10, 2) NOT NULL,
                stock INT NOT NULL DEFAULT 0,
                min_stock_alert INT NOT NULL DEFAULT 10,
                expire_date DATE DEFAULT NULL 
            )""",
            """CREATE TABLE IF NOT EXISTS sales (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id VARCHAR(50) NOT NULL, 
                product_id INT NOT NULL,
                user_id INT NOT NULL,
                quantity INT NOT NULL,
                buy_price_snapshot DECIMAL(10, 2) NOT NULL,
                sell_price_snapshot DECIMAL(10, 2) NOT NULL,
                total_price DECIMAL(10, 2) NOT NULL,
                sale_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                member_id INT DEFAULT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )""",
            """CREATE TABLE IF NOT EXISTS modification_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sale_id INT NOT NULL,
                operator_id INT NOT NULL,
                action_type VARCHAR(50) NOT NULL,
                details TEXT,
                log_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        ]
        for sql in tables:
            self.execute_query(sql)

    def _seed_data(self):
        """重置并填充测试数据"""
        self.execute_query("SET FOREIGN_KEY_CHECKS = 0")
        self.execute_query("TRUNCATE TABLE sales")
        self.execute_query("TRUNCATE TABLE modification_logs")
        self.execute_query("TRUNCATE TABLE products")
        self.execute_query("TRUNCATE TABLE users")
        self.execute_query("TRUNCATE TABLE members")
        self.execute_query("SET FOREIGN_KEY_CHECKS = 1")


        self.execute_query(
            "INSERT INTO users (id, username, password, role) VALUES (1, '1', '1', 'Manager'), (2, '2', '2', 'Clerk')")


        self.execute_query(
            "INSERT INTO members (id, phone, name, points) VALUES (1, '13800138000', '李雷', 100), (2, '13900139000', '韩梅梅', 250)")



        products_sql = """
        INSERT INTO products (id, name, category, buy_price, sell_price, stock, min_stock_alert, expire_date) VALUES
        (1, '可口可乐', '饮料', 2.00, 3.50, 100, 20, '2026-12-31'),
        (2, '康师傅红烧牛肉面', '食品', 3.50, 5.00, 50, 10, '2026-06-30'),
        (3, '晨光笔记本', '文具', 5.00, 8.00, 5, 10, NULL),
        (4, '乐事薯片(原味)', '零食', 4.00, 7.00, 80, 15, '2026-03-15'),
        (5, '农夫山泉', '饮料', 1.00, 2.00, 120, 20, '2027-01-01'),
        (6, '德芙巧克力', '零食', 8.00, 12.00, 40, 10, '2026-10-01'),
        (7, '中华铅笔(HB)', '文具', 0.50, 1.00, 200, 50, NULL)
        """
        self.execute_query(products_sql)


        sales_sql = """
        INSERT INTO sales (order_id, product_id, user_id, quantity, buy_price_snapshot, sell_price_snapshot, total_price, sale_time, member_id) VALUES
        ('20251001083001', 5, 2, 2, 1.00, 2.00, 4.00, CONCAT(CURDATE(), ' 08:30:00'), 1),
        ('20251001083002', 2, 2, 1, 3.50, 5.00, 5.00, CONCAT(CURDATE(), ' 08:30:00'), 1),
        ('20251001121501', 3, 2, 5, 5.00, 8.00, 40.00, CONCAT(CURDATE(), ' 12:15:00'), NULL),
        ('20251001154501', 1, 2, 10, 2.00, 3.50, 35.00, CONCAT(CURDATE(), ' 15:45:00'), 2),
        ('20251001154501', 4, 2, 5, 4.00, 7.00, 35.00, CONCAT(CURDATE(), ' 15:45:00'), 2),
        ('20251001200001', 6, 2, 3, 8.00, 12.00, 36.00, CONCAT(CURDATE(), ' 20:00:00'), NULL),
        ('20251001223001', 1, 2, 1, 2.00, 3.50, 3.50, CONCAT(CURDATE(), ' 22:30:00'), NULL)
        """
        self.execute_query(sales_sql)


        self.execute_query(
            "INSERT INTO modification_logs (sale_id, operator_id, action_type, details, log_time) VALUES (1, 2, 'MODIFY', '将数量从1修改为2', NOW())")


if __name__ == '__main__':
    manager = DatabaseManager(DB_NAME)
    manager.init_database(hard_reset=True)