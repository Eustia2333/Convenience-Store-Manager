import ttkbootstrap as ttk
import tkinter.ttk as tk_ttk
import tkinter as tk
import matplotlib.pyplot as plt
from ttkbootstrap.constants import *
from tkinter import simpledialog
from tkinter import messagebox, Toplevel
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from backend import AuthLogic, ProductLogic, SalesLogic, UserLogic, MemberLogic
from datetime import datetime, timedelta


class LoginFrame(ttk.Frame):
    """
    登录界面封装
    """

    def __init__(self, master, login_callback):
        super().__init__(master, padding=20)
        self.login_callback = login_callback
        self.pack(fill=BOTH, expand=True)

        # --- 界面布局 ---
        # 居中容器
        container = ttk.Frame(self)
        container.place(relx=0.5, rely=0.5, anchor=CENTER)

        # 标题
        lbl_title = ttk.Label(container, text="优选便利店", font=("微软雅黑", 24, "bold"), bootstyle="primary")
        lbl_title.pack(pady=(0, 10))

        lbl_subtitle = ttk.Label(container, text="智能库存管家系统", font=("微软雅黑", 12), bootstyle="secondary")
        lbl_subtitle.pack(pady=(0, 30))

        # 用户名输入
        input_frame = ttk.Frame(container)
        input_frame.pack(fill=X, pady=5)
        ttk.Label(input_frame, text="账号", width=6).pack(side=LEFT)
        self.entry_user = ttk.Entry(input_frame, width=25)
        self.entry_user.pack(side=LEFT, padx=5)
        # 默认聚焦在用户名框
        self.entry_user.focus()

        # 密码输入
        pass_frame = ttk.Frame(container)
        pass_frame.pack(fill=X, pady=5)
        ttk.Label(pass_frame, text="密码", width=6).pack(side=LEFT)
        self.entry_pass = ttk.Entry(pass_frame, width=25, show="*")
        self.entry_pass.pack(side=LEFT, padx=5)
        # 密码框回车也能登录
        self.entry_pass.bind("<Return>", lambda event: self.attempt_login())

        # 登录按钮
        btn_login = ttk.Button(container, text="立即登录", bootstyle="primary", command=self.attempt_login, width=20)
        btn_login.pack(pady=(20, 0))

        self.auth = AuthLogic()

    def attempt_login(self):
        """处理登录逻辑"""
        username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()

        if not username or not password:
            messagebox.showwarning("提示", "请输入账号和密码")
            return

        user = self.auth.login(username, password)

        if user:
            # 登录成功，调用主程序的回调函数，传入用户信息
            self.login_callback(user)
        else:
            messagebox.showerror("登录失败", "账号或密码错误")


class ManagerDashboard(ttk.Frame):
    """
    店长后台：包含商品管理、销售报表、订单审计、人员管理
    """

    def __init__(self, master, user_info, logout_callback):
        super().__init__(master, padding=10)
        self.pack(fill=BOTH, expand=True)
        self.user_info = user_info

        self.prod_logic = ProductLogic()
        self.sales_logic = SalesLogic()
        self.user_logic = UserLogic()
        self.member_logic = MemberLogic()

        # 标志位：防止重复初始化
        self.is_chart_initialized = False

        self._init_header(logout_callback)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=BOTH, expand=True, pady=10)

        # Tab 1: 商品
        self.tab_product = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_product, text="商品库存管理")
        self._init_product_tab()

        # Tab 2: 报表
        self.tab_report = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_report, text="经营数据报表")
        self._init_report_tab()

        # Tab 3: 订单
        self.tab_orders = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_orders, text="订单与审计")
        self._init_orders_tab()

        # Tab 4: 员工
        self.tab_staff = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_staff, text="员工账号管理")
        self._init_staff_tab()

        # 绑定切换事件
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

    def _init_header(self, logout_callback):
        header = ttk.Frame(self)
        header.pack(fill=X)
        ttk.Label(header, text=f"店长 | 管理员: {self.user_info['username']}",
                  font=("微软雅黑", 14, "bold"), bootstyle="primary").pack(side=LEFT)
        ttk.Button(header, text="注销退出", bootstyle="danger-outline",
                   command=logout_callback).pack(side=RIGHT)

    def on_tab_change(self, event):
        """切换到报表页时才刷新数据"""
        if self.notebook.index(self.notebook.select()) == 1:
            # 延时一点点，确保布局计算完成
            self.after(50, self.refresh_report_data)

    # ================= Tab 1: 商品管理 =================
    def _init_product_tab(self):
        # --- 1. 顶部搜索栏 ---
        search_frame = ttk.Frame(self.tab_product, padding=5)
        search_frame.pack(fill=X)

        self.search_var = tk.StringVar()
        entry_search = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        entry_search.pack(side=LEFT, padx=(0, 5))
        entry_search.bind("<Return>", lambda e: self.search_mgr_products())

        ttk.Button(search_frame, text="搜索", command=self.search_mgr_products, bootstyle="info").pack(side=LEFT)
        ttk.Button(search_frame, text="重置", command=self.refresh_product_list, bootstyle="secondary-outline").pack(
            side=LEFT, padx=5)

        # --- 2. 工具栏 ---
        toolbar = ttk.Frame(self.tab_product, padding=5)
        toolbar.pack(fill=X, pady=(0, 5))

        ttk.Button(toolbar, text="新增商品", bootstyle="success", command=self.popup_add_product).pack(side=LEFT)
        ttk.Button(toolbar, text="刷新列表", bootstyle="info-outline", command=self.refresh_product_list).pack(
            side=LEFT, padx=10)

        # --- 修改点：将按钮赋值给 self.btn_expire，以便后续修改它的文字 ---
        self.btn_expire = ttk.Button(toolbar, text="临期商品查询", bootstyle="warning",
                                     command=self.show_expiring_goods)
        self.btn_expire.pack(side=LEFT, padx=10)

        ttk.Label(toolbar, text="* 红色高亮代表库存不足", bootstyle="danger", font=("微软雅黑", 9)).pack(side=RIGHT)

        # --- 3. 表格区域 ---
        cols = ("id", "name", "category", "in_price", "out_price", "stock", "alert", "expire")
        self.tree_prod = ttk.Treeview(self.tab_product, columns=cols, show="headings", selectmode="browse")

        headers = ["ID", "商品名称", "分类", "进价", "售价", "库存", "预警线", "临期时间"]

        for col, name in zip(cols, headers):
            self.tree_prod.heading(col, text=name)
            width = 80
            if col == "name": width = 150
            if col == "expire": width = 100
            self.tree_prod.column(col, width=width, anchor=CENTER)

            # 1. 库存不足 (原有)
            self.tree_prod.tag_configure("low_stock", foreground="red")
            # 2. 已过期 (严重警告，深灰色背景白字)
            self.tree_prod.tag_configure("expired", background="#555", foreground="white")
            # 3. 临期 (黄色背景)
            self.tree_prod.tag_configure("expiring", background="#FFF8DC", foreground="#FF8C00")

        scroll = ttk.Scrollbar(self.tab_product, orient=VERTICAL, command=self.tree_prod.yview)
        self.tree_prod.configure(yscrollcommand=scroll.set)

        self.tree_prod.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=RIGHT, fill=Y)

        # 右键菜单
        self.menu_prod = tk.Menu(self, tearoff=0)
        self.menu_prod.add_command(label="修改商品", command=self.popup_edit_product)
        self.menu_prod.add_command(label="删除商品", command=self.delete_product)
        self.tree_prod.bind("<Button-3>", self.show_prod_menu)

        # 初始加载
        self.refresh_product_list()

    def show_prod_menu(self, event):
        item = self.tree_prod.identify_row(event.y)
        if item:
            self.tree_prod.selection_set(item)
            self.menu_prod.post(event.x_root, event.y_root)

    def show_expiring_goods(self):
        """显示临期/过期商品"""
        # 1. 查数据
        products = self.prod_logic.get_expiring_products(7)

        if not products:
            messagebox.showinfo("结果", "没有过期或临期的商品。")
            return

            # 2. 清空列表
        for item in self.tree_prod.get_children():
            self.tree_prod.delete(item)

        today = datetime.now().date()  # 获取今天日期用于比对

        for p in products:
            # 逻辑判断：给不同的 tag
            tags = ()
            p_date = p['expire_date']

            if p_date < today:
                tags = ("expired",)  # 已过期
            else:
                tags = ("expiring",)  # 还没过期，但快了

            self.tree_prod.insert("", END, values=(
                p['id'], p['name'], p['category'], p['buy_price'], p['sell_price'],
                p['stock'], p['min_stock_alert'], p['expire_date']
            ), tags=tags)

        # 3. 按钮变身
        self.btn_expire.configure(
            text="返回全部商品",
            bootstyle="secondary",
            command=self.refresh_product_list
        )

        messagebox.showwarning("预警", f"注意：发现 {len(products)} 个风险商品（含过期）！")

    def refresh_product_list(self):
        """刷新列表"""
        for item in self.tree_prod.get_children():
            self.tree_prod.delete(item)

        products = self.prod_logic.get_all_products()
        today = datetime.now().date()  # 获取今天

        for p in products:
            tags = []  # 使用列表以便叠加多个标签

            # 1. 库存预警逻辑
            if p['stock'] < p['min_stock_alert']:
                tags.append("low_stock")

            # 2. 保质期逻辑
            if p['expire_date']:  # 如果有保质期
                if p['expire_date'] < today:
                    tags.append("expired")  # 优先显示过期色
                elif p['expire_date'] <= today + timedelta(days=7):
                    tags.append("expiring")

            self.tree_prod.insert("", END, values=(
                p['id'],
                p['name'],
                p['category'],
                p['buy_price'],
                p['sell_price'],
                p['stock'],
                p['min_stock_alert'],
                p['expire_date']
            ), tags=tuple(tags))  # 转回 tuple

        # 重置按钮
        if hasattr(self, 'btn_expire'):
            self.btn_expire.configure(
                text="临期商品查询",
                bootstyle="warning",
                command=self.show_expiring_goods
            )

    def search_mgr_products(self):
        """店长端的搜索逻辑"""
        keyword = self.search_var.get().strip()
        if not keyword:
            self.refresh_product_list()
            return

        # 1. 清空表格
        for item in self.tree_prod.get_children():
            self.tree_prod.delete(item)

        # 2. 调用后端的搜索
        products = self.prod_logic.search_products(keyword)

        # 3. 填充数据
        for p in products:
            tags = ("low_stock",) if p['stock'] < p['min_stock_alert'] else ()
            self.tree_prod.insert("", END, values=(
                p['id'], p['name'], p['category'],
                p['buy_price'], p['sell_price'],
                p['stock'], p['min_stock_alert']
            ), tags=tags)

    def delete_product(self):
        selection = self.tree_prod.selection()
        if selection:
            p_id = self.tree_prod.item(selection[0], "values")[0]
            if messagebox.askyesno("警告", "确定要永久删除该商品吗？"):
                self.prod_logic.delete_product(p_id)
                self.refresh_product_list()

    def popup_add_product(self):
        self._show_product_dialog("新增商品")

    def popup_edit_product(self):
        selection = self.tree_prod.selection()
        if not selection: return
        vals = self.tree_prod.item(selection[0], "values")
        data = {'id': vals[0], 'name': vals[1], 'category': vals[2], 'buy': vals[3], 'sell': vals[4], 'stock': vals[5],
                'alert': vals[6]}
        self._show_product_dialog("修改商品", data)

    def _show_product_dialog(self, title, data=None):
        dlg = Toplevel(self)
        dlg.title(title)
        dlg.geometry("400x700")
        x = self.winfo_rootx() + 100
        y = self.winfo_rooty() + 100
        dlg.geometry(f"+{x}+{y}")
        dlg.grab_set()

        fields = [
            ("商品名称", "name"),
            ("分类", "category"),
            ("进货价", "buy"),
            ("销售价", "sell"),
            ("当前库存", "stock"),
            ("预警阈值", "alert"),
            ("临期时间(YYYY-MM-DD)", "expire")
        ]

        entries = {}
        for i, (label, key) in enumerate(fields):
            ttk.Label(dlg, text=label).pack(anchor=W, padx=20, pady=(10, 0))
            entry = ttk.Entry(dlg)
            entry.pack(fill=X, padx=20, pady=5)
            entries[key] = entry

            # 如果是修改模式，回填数据
            if data:

                val = data.get(key, "")
                if val is None: val = ""
                entry.insert(0, str(val))

        def save():
            try:
                name = entries['name'].get()
                cat = entries['category'].get()
                buy = float(entries['buy'].get())
                sell = float(entries['sell'].get())
                stock = int(entries['stock'].get())
                alert = int(entries['alert'].get())

                # --- 获取保质期输入 ---
                expire = entries['expire'].get().strip()
                if not expire:
                    expire = None  # 如果没填，就是 None

                if data:
                    # 调用更新方法
                    self.prod_logic.update_product(data['id'], name, cat, buy, sell, stock, alert, expire)
                else:
                    # 调用新增方法
                    self.prod_logic.add_product(name, cat, buy, sell, stock, alert, expire)

                messagebox.showinfo("成功", "保存成功！")
                dlg.destroy()
                self.refresh_product_list()
            except ValueError:
                messagebox.showerror("错误", "价格必须是数字，库存必须是整数")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {str(e)}")

        ttk.Button(dlg, text="保存提交", bootstyle="primary", command=save).pack(pady=20, fill=X, padx=20)

    # ================= Tab 2: 销售报表=================
    def _init_report_tab(self):
        """初始化报表页签"""
        # 1. 顶部数据
        card_frame = ttk.Frame(self.tab_report, padding=10)
        card_frame.pack(fill=X)
        self.lbl_revenue = ttk.Label(card_frame, text="总销售额: --", font=("微软雅黑", 12), bootstyle="success")
        self.lbl_revenue.pack(side=LEFT, padx=20)
        self.lbl_profit = ttk.Label(card_frame, text="净利润: --", font=("微软雅黑", 12), bootstyle="warning")
        self.lbl_profit.pack(side=LEFT, padx=20)
        ttk.Button(card_frame, text="刷新数据", command=self.refresh_report_data).pack(side=RIGHT)

        # 2. 上下分栏
        main_pane = tk_ttk.PanedWindow(self.tab_report, orient=VERTICAL)
        main_pane.pack(fill=BOTH, expand=True, pady=10)

        # 图表容器
        self.chart_frame = ttk.Frame(main_pane)
        main_pane.add(self.chart_frame, weight=3)

        # 排行容器
        rank_frame = ttk.Frame(main_pane, padding=10)
        main_pane.add(rank_frame, weight=1)

        # 排行榜
        ttk.Label(rank_frame, text="热销商品排行榜", font=("微软雅黑", 11, "bold")).pack(anchor=W)
        self.tree_rank = ttk.Treeview(rank_frame, columns=("name", "qty"), show="headings", height=5)
        self.tree_rank.heading("name", text="商品名称")
        self.tree_rank.heading("qty", text="销量")
        self.tree_rank.column("name", width=200, anchor=CENTER)
        self.tree_rank.column("qty", width=100, anchor=CENTER)
        self.tree_rank.pack(fill=BOTH, expand=True)

        # 3. 创建图表
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False

        self.fig = plt.Figure(figsize=(5, 4), dpi=100)
        self.ax1 = self.fig.add_subplot(121)
        self.ax2 = self.fig.add_subplot(122)
        self.fig.subplots_adjust(wspace=0.3, bottom=0.15, left=0.1, right=0.95)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        tk_widget = self.canvas.get_tk_widget()

        tk_widget.place(relx=0, rely=0, relwidth=1, relheight=1)

    def refresh_report_data(self):
        """刷新数据"""
        # 1. 刷新文字
        stats = self.sales_logic.get_profit_stats()
        self.lbl_revenue.config(text=f"总销售额: ¥{stats['total_revenue']:.2f}")
        self.lbl_profit.config(text=f"净利润: ¥{stats['total_profit']:.2f}")

        # 2. 刷新排行
        for i in self.tree_rank.get_children(): self.tree_rank.delete(i)
        top5 = self.sales_logic.get_top_selling_products()
        for p in top5:
            self.tree_rank.insert("", END, values=(p['name'], p['total_qty']))

        # 3. 刷新图表
        try:
            self.ax1.clear()
            self.ax2.clear()

            pie_data = self.sales_logic.get_category_pie_data()
            times_str, totals = self.sales_logic.get_minute_sales_stats()

            # 左图
            if pie_data:
                labels = [d['category'] for d in pie_data]
                sizes = [float(d['value']) for d in pie_data]
                self.ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, wedgeprops={'width': 0.4})
                self.ax1.set_title("分类占比")
            else:
                self.ax1.text(0.5, 0.5, "暂无数据", ha='center')
                self.ax1.axis('off')

            # 右图
            x_minutes = []
            for t in times_str:
                h, m = map(int, t.split(':'))
                x_minutes.append(h * 60 + m)

            if x_minutes:
                self.ax2.plot(x_minutes, totals, marker='.', markersize=8, linestyle='-', color='#e74c3c',
                              linewidth=1.5)
                self.ax2.fill_between(x_minutes, totals, color='#e74c3c', alpha=0.1)
            else:
                self.ax2.text(720, 0, "暂无销售", ha='center')

            self.ax2.set_xlim(0, 1440)
            self.ax2.set_ylim(bottom=0)
            ticks = [0, 240, 480, 720, 960, 1200, 1440]
            labels = ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "24:00"]
            self.ax2.set_xticks(ticks)
            self.ax2.set_xticklabels(labels)
            self.ax2.set_title("今日销售走势")
            self.ax2.grid(True, linestyle='--', alpha=0.5)

            # 只重绘，不调整布局
            self.canvas.draw()

        except Exception as e:
            print(f"图表刷新报错: {e}")

    # ================= Tab 3: 订单与审计 =================
    def _init_orders_tab(self):
        ttk.Label(self.tab_orders, text="历史订单流水", font=("微软雅黑", 10, "bold")).pack(anchor=W, pady=5)
        cols = ("oid", "time", "clerk", "prod", "qty", "total")
        self.tree_orders = ttk.Treeview(self.tab_orders, columns=cols, show="headings", height=8)
        self.tree_orders.heading("oid", text="订单号");
        self.tree_orders.heading("time", text="时间")
        self.tree_orders.heading("clerk", text="操作员");
        self.tree_orders.heading("prod", text="商品")
        self.tree_orders.heading("qty", text="数量");
        self.tree_orders.heading("total", text="金额")
        self.tree_orders.column("oid", width=120);
        self.tree_orders.column("prod", width=100)
        self.tree_orders.pack(fill=X, pady=(0, 10))

        ttk.Label(self.tab_orders, text="订单修改记录", font=("微软雅黑", 10, "bold"),
                  bootstyle="danger").pack(anchor=W, pady=5)
        log_cols = ("time", "op", "prod", "detail", "oid")
        self.tree_logs = ttk.Treeview(self.tab_orders, columns=log_cols, show="headings", height=6)
        self.tree_logs.heading("time", text="修改时间");
        self.tree_logs.heading("op", text="修改人")
        self.tree_logs.heading("prod", text="涉及商品");
        self.tree_logs.heading("detail", text="修改内容")
        self.tree_logs.heading("oid", text="关联订单")
        self.tree_logs.pack(fill=BOTH, expand=True)
        ttk.Button(self.tab_orders, text="刷新列表", command=self.refresh_orders_logs).pack(pady=5)
        self.refresh_orders_logs()

    def refresh_orders_logs(self):
        for i in self.tree_orders.get_children(): self.tree_orders.delete(i)
        orders = self.sales_logic.get_all_orders()
        for o in orders: self.tree_orders.insert("", END, values=(
        o['order_id'], o['sale_time'], o['clerk_name'], o['product_name'], o['quantity'], f"{o['total_price']}"))
        for i in self.tree_logs.get_children(): self.tree_logs.delete(i)
        logs = self.sales_logic.get_modification_logs()
        for l in logs: self.tree_logs.insert("", END, values=(
        l['log_time'], l['operator'], l['product'], l['details'], l['order_id']))

    # ================= Tab 4: 人员管理 =================
    def _init_staff_tab(self):
        top_frame = ttk.Frame(self.tab_staff)
        top_frame.pack(fill=X, pady=10)
        ttk.Label(top_frame, text="新员工账号:").pack(side=LEFT)
        self.entry_staff_name = ttk.Entry(top_frame, width=15);
        self.entry_staff_name.pack(side=LEFT, padx=5)
        ttk.Label(top_frame, text="初始密码:").pack(side=LEFT)
        self.entry_staff_pass = ttk.Entry(top_frame, width=15);
        self.entry_staff_pass.pack(side=LEFT, padx=5)
        ttk.Button(top_frame, text="添加售货员", command=self.add_staff).pack(side=LEFT, padx=10)
        ttk.Button(top_frame, text="删除选中", bootstyle="danger", command=self.del_staff).pack(side=RIGHT)
        cols = ("id", "username", "role", "created")
        self.tree_staff = ttk.Treeview(self.tab_staff, columns=cols, show="headings")
        self.tree_staff.heading("id", text="ID");
        self.tree_staff.heading("username", text="用户名")
        self.tree_staff.heading("role", text="权限");
        self.tree_staff.heading("created", text="创建时间")
        self.tree_staff.pack(fill=BOTH, expand=True, pady=10)
        self.refresh_staff_list()

    def refresh_staff_list(self):
        for item in self.tree_staff.get_children(): self.tree_staff.delete(item)
        users = self.user_logic.get_all_clerks()
        for u in users: self.tree_staff.insert("", END, values=(u['id'], u['username'], u['role'], u['created_at']))

    def add_staff(self):
        name = self.entry_staff_name.get().strip();
        pwd = self.entry_staff_pass.get().strip()
        if name and pwd:
            if self.user_logic.add_clerk(name, pwd):
                messagebox.showinfo("成功", f"员工 {name} 添加成功")
                self.refresh_staff_list()
                self.entry_staff_name.delete(0, END);
                self.entry_staff_pass.delete(0, END)
            else:
                messagebox.showerror("失败", "添加失败，可能是用户名重复")
        else:
            messagebox.showwarning("提示", "请填写用户名和密码")

    def del_staff(self):
        selection = self.tree_staff.selection()
        if selection:
            uid = self.tree_staff.item(selection[0], "values")[0]
            name = self.tree_staff.item(selection[0], "values")[1]
            if messagebox.askyesno("删除确认", f"确定删除员工 {name} 吗？"):
                success, msg = self.user_logic.delete_user(uid)
                if success:
                    messagebox.showinfo("成功", msg)
                    self.refresh_staff_list()
                else:
                    messagebox.showerror("删除失败", msg)


class ClerkStation(ttk.Frame):
    """
    售货员收银台：包含前台收银、个人历史订单查询
    """

    def __init__(self, master, user_info, logout_callback):
        super().__init__(master, padding=10)
        self.pack(fill=BOTH, expand=True)
        self.user_info = user_info

        self.product_logic = ProductLogic()
        self.sales_logic = SalesLogic()
        self.user_logic = UserLogic()

        self.cart_data = []

        # 顶部栏
        self._init_header(logout_callback)

        # 选项卡控件
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=BOTH, expand=True, pady=10)

        # --- Tab 1: 前台收银 ---
        self.tab_cashier = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_cashier, text="前台收银")
        self._init_cashier_ui()

        # --- Tab 2: 历史订单 (只看自己的) ---
        self.tab_history = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_history, text="历史订单")
        self._init_history_ui()

        # 绑定事件：切换标签时自动刷新数据
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.member_logic = MemberLogic()  # 初始化
        self.current_member = None  # 存储当前交易的会员

    def on_tab_change(self, event):
        """切换标签页时的刷新逻辑"""
        # 获取当前选中的 Tab 索引
        selected_tab_index = self.notebook.index(self.notebook.select())

        # 索引 0 是收银台，索引 1 是历史订单
        if selected_tab_index == 1:
            self.refresh_my_orders()
        elif selected_tab_index == 0:
            self.refresh_product_list()

    def _init_header(self, logout_callback):
        header = ttk.Frame(self)
        header.pack(fill=X)
        ttk.Label(header, text=f"收银台 | 操作员: {self.user_info['username']}",
                  font=("微软雅黑", 12, "bold"), bootstyle="primary").pack(side=LEFT)
        ttk.Button(header, text="交班退出", bootstyle="danger-outline-small",
                   command=logout_callback).pack(side=RIGHT)

    # ================= Tab 1: 收银台逻辑 =================
    def _init_cashier_ui(self):
        main_pane = tk_ttk.PanedWindow(self.tab_cashier, orient=HORIZONTAL)
        main_pane.pack(fill=BOTH, expand=True, pady=10)

        # 左侧框架 (商品选择)
        self.left_frame = ttk.Frame(main_pane, padding=(0, 0, 10, 0))
        main_pane.add(self.left_frame, weight=3)

        # 右侧框架 (购物车)
        self.right_frame = ttk.Frame(main_pane, padding=(10, 0, 0, 0))
        main_pane.add(self.right_frame, weight=2)

        self._init_product_area()
        self._init_cart_area()
        self.refresh_product_list()

    def _init_product_area(self):
        """左侧：商品列表与搜索"""
        search_frame = ttk.Frame(self.left_frame)
        search_frame.pack(fill=X, pady=(0, 10))

        self.search_var = tk.StringVar()
        entry_search = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        entry_search.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        # 绑定回车搜索
        entry_search.bind("<Return>", lambda e: self.search_products())

        ttk.Button(search_frame, text="搜索", command=self.search_products, bootstyle="info").pack(side=LEFT)
        ttk.Button(search_frame, text="重置", command=self.refresh_product_list, bootstyle="secondary-outline").pack(side=LEFT, padx=5)

        # 商品表格
        columns = ("id", "name", "category", "price", "stock")
        self.tree_products = ttk.Treeview(self.left_frame, columns=columns, show="headings", selectmode="browse")

        self.tree_products.heading("id", text="ID")
        self.tree_products.heading("name", text="商品名称")
        self.tree_products.heading("category", text="分类")
        self.tree_products.heading("price", text="单价")
        self.tree_products.heading("stock", text="库存")

        self.tree_products.column("id", width=40, anchor=CENTER)
        self.tree_products.column("name", width=150)
        self.tree_products.column("category", width=80, anchor=CENTER)
        self.tree_products.column("price", width=60, anchor=E)
        self.tree_products.column("stock", width=60, anchor=CENTER)

        scrollbar = ttk.Scrollbar(self.left_frame, orient=VERTICAL, command=self.tree_products.yview)
        self.tree_products.configure(yscrollcommand=scrollbar.set)

        self.tree_products.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # 双击添加商品
        self.tree_products.bind("<Double-1>", self.on_add_to_cart)

    def _init_cart_area(self):
        mem_frame = ttk.Labelframe(self.right_frame, text="会员服务", padding=10, bootstyle="info")
        mem_frame.pack(fill=X, pady=(0, 10))

        self.mem_var = tk.StringVar()
        entry_mem = ttk.Entry(mem_frame, textvariable=self.mem_var, width=15)
        entry_mem.pack(side=LEFT, padx=5)
        entry_mem.bind("<Return>", lambda e: self.check_member())

        ttk.Button(mem_frame, text="识别", command=self.check_member, bootstyle="info-outline").pack(side=LEFT)

        self.lbl_member_info = ttk.Label(mem_frame, text="未登录", font=("微软雅黑", 9))
        self.lbl_member_info.pack(side=LEFT, padx=10)

        ttk.Button(mem_frame, text="注册", command=self.popup_register, bootstyle="link").pack(side=RIGHT)
        """右侧：购物车与结账"""
        ttk.Label(self.right_frame, text="当前购物车", font=("微软雅黑", 11, "bold")).pack(anchor=W, pady=(0, 10))

        columns = ("name", "qty", "total")
        self.tree_cart = ttk.Treeview(self.right_frame, columns=columns, show="headings", height=15)

        self.tree_cart.heading("name", text="商品")
        self.tree_cart.heading("qty", text="数量")
        self.tree_cart.heading("total", text="小计")

        self.tree_cart.column("name", width=120)
        self.tree_cart.column("qty", width=50, anchor=CENTER)
        self.tree_cart.column("total", width=70, anchor=E)

        self.tree_cart.pack(fill=BOTH, expand=True)

        btn_frame = ttk.Frame(self.right_frame)
        btn_frame.pack(fill=X, pady=5)
        ttk.Button(btn_frame, text="移出商品", bootstyle="warning-link", command=self.remove_from_cart).pack(side=RIGHT)

        footer_frame = ttk.Frame(self.right_frame, padding=10, bootstyle="light")
        footer_frame.pack(fill=X, pady=10)

        self.lbl_total_price = ttk.Label(footer_frame, text="总计: ¥0.00", font=("微软雅黑", 16, "bold"), bootstyle="danger")
        self.lbl_total_price.pack(side=LEFT)

        ttk.Button(footer_frame, text="立即结账", bootstyle="success", width=15, command=self.checkout).pack(side=RIGHT)

    # ================= Tab 2: 历史订单逻辑 =================
    def _init_history_ui(self):
        """Feature 5: 查询并修改订单"""
        toolbar = ttk.Frame(self.tab_history)
        toolbar.pack(fill=X, pady=5)
        ttk.Button(toolbar, text="修改选中订单数量", bootstyle="warning", command=self.modify_selected_order).pack(side=LEFT)
        ttk.Button(toolbar, text="刷新列表", command=self.refresh_my_orders).pack(side=RIGHT)

        cols = ("id", "oid", "time", "prod", "qty", "total")
        self.tree_history = ttk.Treeview(self.tab_history, columns=cols, show="headings")
        self.tree_history.heading("id", text="流水号")
        self.tree_history.heading("oid", text="订单号")
        self.tree_history.heading("time", text="时间")
        self.tree_history.heading("prod", text="商品")
        self.tree_history.heading("qty", text="数量")
        self.tree_history.heading("total", text="金额")

        self.tree_history.column("id", width=50)
        self.tree_history.column("qty", width=50)
        self.tree_history.pack(fill=BOTH, expand=True)

    def refresh_my_orders(self):
        # 清空列表
        for i in self.tree_history.get_children():
            self.tree_history.delete(i)

        # 传入 current_user_id 只查自己的订单
        orders = self.sales_logic.get_all_orders(clerk_id=self.user_info['id'])
        for o in orders:
            self.tree_history.insert("", END, values=(
                o['id'], o['order_id'], o['sale_time'],
                o['product_name'], o['quantity'], o['total_price']
            ))

    def modify_selected_order(self):
        selection = self.tree_history.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选择一条记录")
            return

        vals = self.tree_history.item(selection[0], "values")
        sale_id = vals[0]
        prod_name = vals[3]
        old_qty = int(vals[4])

        new_qty = simpledialog.askinteger("修改订单",
                                          f"正在修改商品: {prod_name}\n原数量: {old_qty}\n\n请输入新数量 (0=退货):",
                                          parent=self, minvalue=0)

        if new_qty is not None:
            # 调用 backend 中的修改逻辑
            success, msg = self.sales_logic.modify_order_qty(sale_id, new_qty, self.user_info['id'])
            if success:
                messagebox.showinfo("成功", "订单修改成功！")
                self.refresh_my_orders()
            else:
                messagebox.showerror("失败", msg)

    # ================= 辅助逻辑 (收银相关) =================
    def refresh_product_list(self):

        for item in self.tree_products.get_children():
            self.tree_products.delete(item)

        products = self.product_logic.get_all_products()

        for p in products:
            # 收银端只需要显示基础信息，通常不需要显示进价和保质期
            self.tree_products.insert("", END, values=(
                p['id'],
                p['name'],
                p['category'],
                f"{p['sell_price']}",
                p['stock']
            ))

    def show_expiring_goods(self):
        """显示临期商品"""
        for item in self.tree_prod.get_children():
            self.tree_prod.delete(item)

        products = self.prod_logic.get_expiring_products(7)

        for p in products:

            self.tree_prod.insert("", END, values=(
                p['id'], p['name'], p['category'], p['buy_price'], p['sell_price'],
                p['stock'], p['min_stock_alert'], p['expire_date']
            ), tags=("low_stock",))

        if not products:
            messagebox.showinfo("结果", "未来7天没有即将过期的商品。")
        else:
            messagebox.showwarning("预警", f"发现 {len(products)} 个即将过期的商品！")

    def search_products(self):
        keyword = self.search_var.get().strip()
        if not keyword:
            self.refresh_product_list()
            return

        # 注意：使用 tree_products
        for item in self.tree_products.get_children():
            self.tree_products.delete(item)

        # 注意：使用 product_logic
        products = self.product_logic.search_products(keyword)

        for p in products:
            self.tree_products.insert("", END, values=(
                p['id'],
                p['name'],
                p['category'],
                f"{p['sell_price']}",
                p['stock']
            ))

    def on_add_to_cart(self, event):
        selection = self.tree_products.selection()
        if not selection: return

        item_values = self.tree_products.item(selection[0], "values")
        p_id, p_name, _, p_price, p_stock = item_values
        p_price = float(p_price)
        p_stock = int(p_stock)

        if p_stock <= 0:
            messagebox.showwarning("库存不足", f"{p_name} 暂时缺货！")
            return

        qty = simpledialog.askinteger("添加商品", f"请输入购买 '{p_name}' 的数量:",
                                      parent=self, minvalue=1, maxvalue=p_stock)

        if qty:
            self.add_item_to_cart_data(p_id, p_name, p_price, qty, p_stock)

    def add_item_to_cart_data(self, p_id, name, price, qty, max_stock):
        found = False
        for item in self.cart_data:
            if str(item['id']) == str(p_id):
                new_qty = item['buy_qty'] + qty
                if new_qty > max_stock:
                    messagebox.showwarning("提示", f"库存不足！最多只能购买 {max_stock} 件")
                    return
                item['buy_qty'] = new_qty
                item['total'] = item['buy_qty'] * item['sell_price']
                found = True
                break

        if not found:
            self.cart_data.append({
                'id': p_id, 'name': name, 'sell_price': price,
                'buy_qty': qty, 'total': price * qty, 'max_stock': max_stock
            })

        self.refresh_cart_view()

    def remove_from_cart(self):
        selection = self.tree_cart.selection()
        if not selection: return
        idx = self.tree_cart.index(selection[0])
        del self.cart_data[idx]
        self.refresh_cart_view()

    def refresh_cart_view(self):
        for item in self.tree_cart.get_children():
            self.tree_cart.delete(item)
        total_amount = 0.0
        for item in self.cart_data:
            self.tree_cart.insert("", END, values=(item['name'], item['buy_qty'], f"¥{item['total']:.2f}"))
            total_amount += item['total']
        self.lbl_total_price.config(text=f"总计: ¥{total_amount:.2f}")

    def checkout(self):
        if not self.cart_data:
            messagebox.showwarning("提示", "购物车是空的")
            return

        # 获取会员ID
        member_id = self.current_member['id'] if self.current_member else None

        if not messagebox.askyesno("确认",
                                   f"总计: {self.lbl_total_price.cget('text')}\n会员: {'是' if member_id else '否'}"):
            return

        clerk_id = self.user_info['id']
        # 调用修改后的 backend checkout，接收3个返回值
        success, msg, receipt_data = self.sales_logic.checkout(clerk_id, self.cart_data, member_id)

        if success:
            messagebox.showinfo("成功", msg)
            self.show_receipt(receipt_data)  # 打印小票
            self.cart_data = []
            self.refresh_cart_view()
            self.refresh_product_list()
            # 重置会员状态
            self.current_member = None
            self.lbl_member_info.config(text="未登录", bootstyle="secondary")
            self.mem_var.set("")
        else:
            messagebox.showerror("失败", msg)

    def show_receipt(self, data):
        """弹出虚拟小票窗口"""
        win = Toplevel(self)
        win.title("电子小票")
        win.geometry("300x500")

        txt = tk.Text(win, font=("Courier New", 10), width=35, height=30)
        txt.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # 构造小票内容
        content = f"""
        ******************************
               优选便利店 电子凭证
        ******************************
        单号: {data['order_id']}
        时间: {data['time']}
        收银: {self.user_info['username']}
        ------------------------------
        商品             数量    金额
        """
        for item in data['items']:
            name = item['name'][:10]  # 截断长名
            content += f"{name:<12} x{item['buy_qty']:<3} {item['total']:>6.2f}\n"

        content += f"""
        ------------------------------
        总计金额:         ¥{data['total']:.2f}
        """

        if self.current_member:
            content += f"""
        ------------------------------
        会员: {self.current_member['name']}
        本次积分: {data['member_points']}
        """

        content += "\n    *** 谢谢惠顾 欢迎下次光临 ***"

        txt.insert(END, content)
        txt.config(state=DISABLED)  # 只读

    def check_member(self):
        phone = self.mem_var.get().strip()
        if not phone: return
        member = self.member_logic.get_member_by_phone(phone)
        if member:
            self.current_member = member
            self.lbl_member_info.config(text=f"VIP: {member['name']} | 积分: {member['points']}", bootstyle="success")
            messagebox.showinfo("成功", f"欢迎会员：{member['name']}")
        else:
            self.current_member = None
            self.lbl_member_info.config(text="会员不存在", bootstyle="danger")
            if messagebox.askyesno("提示", "会员不存在，是否立即注册？"):
                self.popup_register()

    def popup_register(self):
        phone = simpledialog.askstring("注册", "请输入手机号:")
        if not phone: return
        name = simpledialog.askstring("注册", "请输入会员昵称:")
        if not name: return

        if self.member_logic.register_member(phone, name):
            messagebox.showinfo("成功", "注册成功，请重新识别")
            self.mem_var.set(phone)
            self.check_member()
        else:
            messagebox.showerror("失败", "注册失败，手机号可能已存在")

class MainApp(ttk.Window):
    """
    主应用程序控制器
    """

    def __init__(self):
        # 初始化窗口，设置主题
        super().__init__(themename="cosmo")
        self.title("优选便利店智能库存管家系统")
        self.geometry("1000x700")
        self.center_window()

        # 当前登录用户数据
        self.current_user = None

        # 初始显示登录页
        self.show_login()

    def center_window(self):
        """窗口居中辅助函数"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def clear_frame(self):
        """清空当前窗口中的所有组件"""
        for widget in self.winfo_children():
            widget.destroy()

    def show_login(self):
        """显示登录页面"""
        self.clear_frame()
        self.current_user = None
        LoginFrame(self, self.on_login_success)

    def on_login_success(self, user):
        """登录成功后的路由逻辑"""
        self.current_user = user
        role = user['role']

        if role == 'Manager':
            self.show_manager_dashboard()
        elif role == 'Clerk':
            self.show_clerk_station()
        else:
            messagebox.showerror("系统错误", f"未知的用户角色: {role}")

    def show_manager_dashboard(self):
        """显示店长界面"""
        self.clear_frame()
        ManagerDashboard(self, self.current_user, self.logout)

    def show_clerk_station(self):
        """显示收银界面"""
        self.clear_frame()
        ClerkStation(self, self.current_user, self.logout)

    def logout(self):
        """注销"""
        if messagebox.askyesno("确认", "确定要退出登录吗？"):
            self.show_login()


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()