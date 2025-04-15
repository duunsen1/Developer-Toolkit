import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import os
import platform
import json
from datetime import datetime
import time
import queue
import uuid
import threading

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("开发者工具箱")
        self.geometry("525x500")
        
        # 添加窗口置顶状态变量
        self.topmost_state = tk.BooleanVar(value=False)
        self.attributes('-topmost', self.topmost_state.get())
        
        # 创建顶部状态栏
        self.status_bar = StatusBar(self, self.topmost_state)
        self.status_bar.pack(side="top", fill="x", pady=5)
        
        # 创建内容容器
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill="both", expand=True)
        
        # 初始化所有界面
        self.frames = {}
        for F in (MainMenu, ADBTools, FastbootTools, LogTools):
            frame = F(self.content_frame, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        
        self.show_frame("MainMenu")
    
    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()

    def run_scrcpy(self):
        """执行投屏程序"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        scrcpy_dir = os.path.join(script_dir, 'scrcpy')
        scrcpy_exe = os.path.join(scrcpy_dir, 'scrcpy.exe')
        
        # 检查scrcpy是否存在
        if not os.path.exists(scrcpy_exe):
            messagebox.showerror("程序缺失", f"未找到投屏程序：\n{scrcpy_exe}")
            return
        
        # 获取adb路径
        default_adb = os.path.join(scrcpy_dir, 'adb.exe')
        adb_path = default_adb if os.path.exists(default_adb) else 'adb'
        
        # 检测设备连接
        try:
            result = subprocess.run(
                [adb_path, 'devices'],
                capture_output=True,
                text=True,
                check=True
            )
            devices = [
                line.split('\t')[0]
                for line in result.stdout.splitlines()[1:]
                if '\tdevice' in line
            ]
            if not devices:
                messagebox.showerror("设备未连接", "未检测到安卓设备！")
                return
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            messagebox.showerror(
                "ADB错误",
                "ADB执行失败，请确保：\n1. 已安装ADB驱动\n2. 已开启USB调试\n3. 设备已授权"
            )
            return
        
        # 执行投屏程序
        try:
            subprocess.Popen(
                [scrcpy_exe],
                cwd=scrcpy_dir,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            messagebox.showinfo(
                "投屏启动",
                "投屏程序已启动，请查看设备授权提示！\n\n若窗口未出现，请检查杀毒软件拦截"
            )
        except Exception as e:
            messagebox.showerror("启动失败", f"投屏程序启动失败：\n{str(e)}")

class StatusBar(ttk.Frame):
    def __init__(self, parent, topmost_var):
        super().__init__(parent, style='Status.TFrame')
        self.topmost_var = topmost_var
        self.adb_status = tk.StringVar(value="N")
        self.fastboot_status = tk.StringVar(value="N")
        
        self.create_widgets()
        self.start_auto_check()
    
    def create_widgets(self):
        # 左侧状态显示部分
        status_frame = ttk.Frame(self)
        status_frame.pack(side="left", padx=10)
        
        ttk.Label(status_frame, text="ADB连接状态:").grid(row=0, column=0)
        self.lbl_adb = ttk.Label(status_frame, textvariable=self.adb_status,
                               font=('Arial', 12, 'bold'), foreground="gray")
        self.lbl_adb.grid(row=0, column=1, padx=5)
        
        ttk.Label(status_frame, text="Fastboot连接状态:").grid(row=0, column=2)
        self.lbl_fastboot = ttk.Label(status_frame, textvariable=self.fastboot_status,
                                    font=('Arial', 12, 'bold'), foreground="gray")
        self.lbl_fastboot.grid(row=0, column=3, padx=5)
        
        # 右侧功能按钮区（新增重启按钮）
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side="right", padx=10)
        
        # 新增重启按钮
        ttk.Button(btn_frame, text="重启设备", 
                 command=self.reboot_device).grid(row=0, column=1, padx=4)
        
        # 窗口置顶复选框
        topmost_btn = ttk.Checkbutton(
            btn_frame,
            text="置顶",
            variable=self.topmost_var,
            command=self.toggle_topmost
        ).grid(row=0, column=2, padx=4)
        
        # 设备管理器按钮
        ttk.Button(btn_frame, text="设备管理器", 
                 command=self.open_device_manager).grid(row=0, column=0, padx=4)

    def reboot_device(self):
        """执行adb reboot命令"""
        try:
            # 检查设备连接状态
            if self.adb_status.get() != "Y":
                messagebox.showwarning("警告", "当前没有已连接的ADB设备")
                return
            
            # 异步执行命令避免界面卡顿
            def run_reboot():
                try:
                    result = subprocess.run(
                        ["adb", "reboot"],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=10
                    )
                    self.master.after(0, lambda: messagebox.showinfo(
                        "成功", "重启命令已发送，设备即将重启"))
                except subprocess.CalledProcessError as e:
                    error_msg = f"重启失败：{e.stderr.strip()}"
                    self.master.after(0, lambda: messagebox.showerror("错误", error_msg))
                except Exception as e:
                    self.master.after(0, lambda: messagebox.showerror(
                        "异常", f"发生未知错误：{str(e)}"))

            threading.Thread(target=run_reboot, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("错误", f"执行异常：{str(e)}")
    
    def toggle_topmost(self):
        """切换窗口置顶状态"""
        new_state = self.topmost_var.get()
        self.master.attributes('-topmost', new_state)

    
    def start_auto_check(self):
        self.check_status()
        self.after(2000, self.start_auto_check)
    
    def check_status(self):
        self.check_adb()
        self.check_fastboot()
        self.update_colors()
    
    def check_adb(self):
        try:
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                timeout=2
            )
            connected = "Y" if self.has_connected_device(result.stdout, 'adb') else "N"
            self.adb_status.set(connected)
        except Exception as e:
            print(f"ADB检测异常: {str(e)}")
            self.adb_status.set("N")
    
    def check_fastboot(self):
        try:
            result = subprocess.run(
                ["fastboot", "devices"],
                capture_output=True,
                text=True,
                timeout=2
            )
            connected = "Y" if self.has_connected_device(result.stdout, 'fastboot') else "N"
            self.fastboot_status.set(connected)
        except Exception as e:
            print(f"Fastboot检测异常: {str(e)}")
            self.fastboot_status.set("N")
    
    def has_connected_device(self, output, mode):
        valid_lines = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            if mode == 'adb' and "List of devices" in line:
                continue
            if ("\t" in line) or (" " in line and "fastboot" in line):
                valid_lines.append(line)
        return len(valid_lines) > 0
    
    def update_colors(self):
        self.lbl_adb.config(foreground="green4" if self.adb_status.get() == "Y" else "red3")
        self.lbl_fastboot.config(foreground="green4" if self.fastboot_status.get() == "Y" else "red3")
    
    def open_device_manager(self):
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile("devmgmt.msc")
            elif system == "Darwin":
                subprocess.run(["open", "/System/Library/CoreServices/Applications/System Information.app"])
            elif system == "Linux":
                subprocess.run(["gnome-control-center", "devices"])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开设备管理器：{str(e)}")

class MainMenu(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.create_widgets(controller)
    
    def create_widgets(self, controller):
        ttk.Label(self, text="主菜单", font=("微软雅黑", 14)).pack(pady=20)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(expand=True)
        
        buttons = [
            ("Adb Flash", "ADBTools"),
            ("Fastboot flash", "FastbootTools"),
            ("日志过滤", "LogTools"),
            ("投屏", "run_scrcpy")
        ]
        
        for text, page in buttons:
            if page == "run_scrcpy":
                ttk.Button(btn_frame, text=text, width=20,
                          command=controller.run_scrcpy).pack(pady=5)
            else:
                ttk.Button(btn_frame, text=text, width=20,
                          command=lambda p=page: controller.show_frame(p)).pack(pady=5)

class ADBTools(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.history_file = "file_history.json"
        self.target_history_file = "target_history.json"
        self.file_history = []
        self.target_history = []
        self.current_file = ""
        self.current_target = ""

        self.create_header()
        self.setup_ui()
        self.load_histories()
        self.check_environment()

    def create_header(self):
        """创建标题和返回按钮"""
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky="ew", pady=5)
        
        ttk.Label(header_frame, text="ADB 单刷工具", font=("微软雅黑", 12)).pack(side="left", padx=10)
        ttk.Button(header_frame, text="返回主菜单",
                 command=lambda: self.controller.show_frame("MainMenu")).pack(side="right", padx=10)
        
        # 使header_frame的列自动扩展
        self.columnconfigure(0, weight=1)

    def setup_ui(self):
        # 环境检测区域
        self.env_frame = ttk.LabelFrame(self, text="环境检测")
        self.env_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        self.env_status = ttk.Label(self.env_frame, text="未检测")
        self.env_status.grid(row=0, column=0, padx=5, pady=2)
        
        ttk.Button(self.env_frame, text="检测环境", command=self.check_environment).grid(row=0, column=1, padx=5)
        ttk.Button(self.env_frame, text="配置指南", command=self.install_drivers).grid(row=0, column=2, padx=5)

        # 文件操作区域
        self.file_frame = ttk.LabelFrame(self, text="操作文件")
        self.file_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        
        self.file_info = ttk.Label(self.file_frame, text="未选择文件")
        self.file_info.grid(row=0, column=0, padx=5, pady=2, sticky="w")

        self.history_combo = ttk.Combobox(self.file_frame, values=self.file_history)
        self.history_combo.grid(row=1, column=0, padx=10, pady=2, sticky="ew")
        self.history_combo.bind("<<ComboboxSelected>>", self.on_file_history_select)
        ttk.Button(self.file_frame, text="选择文件", command=self.select_file).grid(row=1, column=1, padx=5)
        # 目标路径区域
        self.target_frame = ttk.LabelFrame(self, text="目标路径")
        self.target_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        
        self.target_combo = ttk.Combobox(self.target_frame, values=self.target_history)
        self.target_combo.grid(row=0, column=0, padx=5, pady=2, sticky="ew")
        self.target_combo.bind("<<ComboboxSelected>>", self.on_target_select)
        ttk.Button(self.target_frame, text="开始刷写", command=self.start_flash).grid(row=0, column=1, padx=5)
        
        self.target_frame.columnconfigure(0, weight=1)

        # 输出区域
        self.output_frame = ttk.LabelFrame(self, text="操作输出")
        self.output_frame.grid(row=4, column=0, padx=10, pady=5, sticky="nsew")
        
        self.output_text = tk.Text(self.output_frame, height=15, width=70, wrap=tk.WORD)
        vsb = ttk.Scrollbar(self.output_frame, orient="vertical", command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=vsb.set)
        
        self.output_text.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        
        # 布局配置
        self.rowconfigure(3, weight=1)
        self.columnconfigure(0, weight=1)
        self.output_frame.rowconfigure(0, weight=1)
        self.output_frame.columnconfigure(0, weight=1)

    def check_environment(self):
        """检测ADB环境"""
        self.insert_output("\n=== 开始环境检测 ===\n")
        try:
            subprocess.run(["adb", "version"],
                         check=True,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         creationflags=subprocess.CREATE_NO_WINDOW)
            
            self.env_status.config(text="环境正常", foreground="green")
            self.insert_output("检测结果：环境正常\n")
            return True
        except Exception as e:
            self.env_status.config(text="环境异常", foreground="red")
            self.insert_output("检测结果：环境异常\n")
            self.insert_output(f"错误信息：{str(e)}\n")
            return False

    def install_drivers(self):
        """显示驱动安装指南"""
        self.insert_output("\n=== ADB环境配置指南 ===\n")
        guide = """1. 下载Google USB驱动：
   官方地址：https://developer.android.com/studio/run/win-usb
    
2. 下载Platform Tools：
   下载页面：https://developer.android.com/studio/releases/platform-tools
   
3. 解压platform-tools到系统目录（例如：C:\\platform-tools）
   
4. 添加环境变量：
   • 右键点击"此电脑"选择"属性"
   • 进入"高级系统设置" -> "环境变量"
   • 在Path中添加platform-tools目录
   
5. 设备连接：
   • 启用USB调试模式（设置 -> 开发者选项）
   • 首次连接需要在设备上授权ADB调试"""
        self.insert_output(guide + "\n")

    def select_file(self):
        """选择文件"""
        file_path = filedialog.askopenfilename(filetypes=[("All Files", "*.*")])
        if file_path:
            self.current_file = file_path
            self.update_file_info()
            self.add_to_file_history(file_path)

    def select_target_dir(self):
        """选择目标目录"""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.current_target = dir_path
            self.target_combo.set(dir_path)
            self.add_to_target_history(dir_path)

    def on_target_select(self, event):
        """目标路径选择事件"""
        self.current_target = self.target_combo.get()

    def add_to_target_history(self, path):
        """维护目标路径历史记录"""
        if path in self.target_history:
            self.target_history.remove(path)
        self.target_history.insert(0, path)
        self.target_combo["values"] = self.target_history[:10]
        self.save_history(self.target_history_file, self.target_history)

    def update_file_info(self):
        """更新文件信息"""
        if self.current_file:
            filename = os.path.basename(self.current_file)
            mtime = os.path.getmtime(self.current_file)
            timestamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            self.file_info.config(text=f"{filename} - 修改时间: {timestamp}")

    def load_histories(self):
        """加载历史记录"""
        # 文件历史
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    self.file_history = json.load(f)
                    self.history_combo["values"] = self.file_history
            except Exception as e:
                self.insert_output(f"\n加载文件历史失败：{str(e)}\n")
        
        # 目标路径历史
        if os.path.exists(self.target_history_file):
            try:
                with open(self.target_history_file, "r") as f:
                    self.target_history = json.load(f)
                    self.target_combo["values"] = self.target_history
            except Exception as e:
                self.insert_output(f"\n加载路径历史失败：{str(e)}\n")

    def add_to_file_history(self, path):
        """维护文件历史记录"""
        if path in self.file_history:
            self.file_history.remove(path)
        self.file_history.insert(0, path)
        self.history_combo["values"] = self.file_history[:10]
        self.save_history(self.history_file, self.file_history)

    def save_history(self, filename, history):
        """保存历史记录"""
        try:
            with open(filename, "w") as f:
                json.dump(history[:10], f)
        except Exception as e:
            self.insert_output(f"\n保存历史记录失败：{str(e)}\n")

    def on_file_history_select(self, event):
        """文件历史选择事件"""
        self.current_file = self.history_combo.get()
        self.update_file_info()

    def on_target_history_select(self, event):
        """目标路径历史选择事件"""
        self.current_target = self.target_history_combo.get()
        self.target_entry.delete(0, tk.END)
        self.target_entry.insert(0, self.current_target)

    def start_flash(self):
        """启动刷写流程"""
        self.current_target = self.target_combo.get()

        if not self.current_file:
            messagebox.showwarning("警告", "请先选择要刷写的文件！")
            return
        if not self.current_target.strip():
            messagebox.showwarning("警告", "请输入目标路径！")
            return
        
        self.output_text.delete(1.0, tk.END)
        self.insert_output("=== 开始ADB刷写流程 ===\n")
        
        try:
            # 等待设备连接
            if self.run_command("adb wait-for-device") != 0:
                raise Exception("设备未连接")
            
            # 获取root权限
            if self.run_command("adb root") != 0:
                raise Exception("获取Root权限失败")
            
            # 尝试禁用验证
            if self.run_command("adb disable-verity") != 0:
                self.insert_output("验证禁用失败，尝试重启设备...\n")
                self.run_command("adb reboot")
                time.sleep(20)
                
                if self.run_command("adb wait-for-device") != 0:
                    raise Exception("设备重启后未连接")
                
                if self.run_command("adb root") != 0:
                    raise Exception("重启后获取Root失败")
                
            # 重新挂载分区
            if self.run_command("adb remount") != 0:
                raise Exception("分区挂载失败")
            
            # 推送文件
            push_cmd = f'adb push "{self.current_file}" "{self.current_target}"'
            if self.run_command(push_cmd) == 0:
                self.insert_output("\n✅ 文件推送成功！\n")
            else:
                raise Exception("文件推送失败")
            
        except Exception as e:
            self.insert_output(f"\n❌ 操作失败: {str(e)}\n")
            messagebox.showerror("错误", f"操作失败: {str(e)}")

    def run_command(self, command):
        """执行命令并返回状态码"""
        self.insert_output(f"\n>>> 执行命令: {command}\n")
        try:
            process = subprocess.Popen(command,
                                     shell=True,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     text=True,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.insert_output(output)
            
            returncode = process.poll()
            self.insert_output(f"\n返回代码: {returncode}\n")
            return returncode
        except Exception as e:
            self.insert_output(f"命令执行失败: {str(e)}\n")
            return -1

    def insert_output(self, text):
        """插入输出文本"""
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.update_idletasks()


class FastbootTools(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.history_file = "file_history.json"
        self.file_history = []
        self.current_file = ""
        
        # 分区映射配置
        self.partition_map = {
            "boot.img": "boot_a",
            "system.img": "system_a",
            "vendor.img": "vendor_a",
            "vbmeta.img": "vbmeta_a",
            "dtbo.img": "dtbo_a",
            "recovery.img": "recovery"
        }

        self.pad_config = {
            "frame_padx": 8,    # 框架水平外间距
            "frame_pady": 3,    # 框架垂直外间距
            "widget_padx": 3,   # 控件水平内间距
            "widget_pady": 2    # 控件垂直内间距
        }

        self.create_header()
        self.setup_ui()
        self.load_history()
        self.check_environment()

    def create_header(self):
        """创建标题和返回按钮"""
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, 
                            column=0, 
                            sticky="ew", 
                            pady=self.pad_config["frame_pady"])
        
        ttk.Label(header_frame, text="Fastboot 单刷工具", font=("微软雅黑", 12)).pack(
            side="left", 
            padx=self.pad_config["widget_padx"]
        )
        ttk.Button(header_frame, text="返回主菜单",
                 command=lambda: self.controller.show_frame("MainMenu")).pack(
                     side="right", 
                     padx=self.pad_config["widget_padx"]
                 )
        
        self.columnconfigure(0, weight=1)

    def setup_ui(self):
        # 环境检测区域
        self.env_frame = ttk.LabelFrame(self, text="环境检测")
        self.env_frame.grid(
            row=1, 
            column=0, 
            padx=self.pad_config["frame_padx"],
            pady=self.pad_config["frame_pady"],
            sticky="ew"
        )
        
        self.env_status = ttk.Label(self.env_frame, text="未检测")
        self.env_status.grid(
            row=0, 
            column=0, 
            padx=self.pad_config["widget_padx"],
            pady=self.pad_config["widget_pady"]
        )
        
        ttk.Button(self.env_frame, text="检测环境", command=self.check_environment).grid(
            row=0, 
            column=1, 
            padx=self.pad_config["widget_padx"]
        )
        ttk.Button(self.env_frame, text="配置指南", command=self.install_drivers).grid(
            row=0, 
            column=2, 
            padx=self.pad_config["widget_padx"]
        )

        # 文件操作区域
        self.file_frame = ttk.LabelFrame(self, text="文件操作")
        self.file_frame.grid(
            row=2, 
            column=0, 
            padx=self.pad_config["frame_padx"],
            pady=self.pad_config["frame_pady"],
            sticky="ew"
        )
        
        # 第一行：文件信息+操作按钮
        self.file_info = ttk.Label(self.file_frame, text="未选择文件")
        self.file_info.grid(
            row=0, 
            column=0, 
            padx=self.pad_config["widget_padx"],
            pady=self.pad_config["widget_pady"],
            sticky="w"
        )
        
        btn_frame = ttk.Frame(self.file_frame)
        btn_frame.grid(row=0, column=1, sticky="e")
        ttk.Button(btn_frame, text="选择文件", command=self.select_file).pack(
            side="left", 
            padx=self.pad_config["widget_padx"]
        )
        ttk.Button(btn_frame, text="刷入分区", command=self.start_flash).pack(
            side="left", 
            padx=self.pad_config["widget_padx"]
        )

        # 第二行：历史记录下拉框
        self.history_combo = ttk.Combobox(self.file_frame, values=self.file_history)
        self.history_combo.grid(
            row=1, 
            column=0, 
            columnspan=2,
            padx=self.pad_config["widget_padx"],
            pady=self.pad_config["widget_pady"],
            sticky="ew"
        )
        self.history_combo.bind("<<ComboboxSelected>>", self.on_history_select)

        # 输出区域
        self.output_frame = ttk.LabelFrame(self, text="操作输出")
        self.output_frame.grid(
            row=3, 
            column=0, 
            padx=self.pad_config["frame_padx"],
            pady=self.pad_config["frame_pady"],
            sticky="nsew"
        )
        
        self.output_text = tk.Text(
            self.output_frame, 
            height=15, 
            width=70, 
            wrap=tk.WORD,
            padx=3,  # 文本区内边距
            pady=3
        )
        vsb = ttk.Scrollbar(self.output_frame, orient="vertical", command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=vsb.set)
        
        self.output_text.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        
        # 布局配置
        self.rowconfigure(3, weight=1)
        self.columnconfigure(0, weight=1)
        self.output_frame.columnconfigure(0, weight=1)
        self.output_frame.rowconfigure(0, weight=1)

        # 配置所有LabelFrame的统一样式
        for frame in [self.env_frame, self.file_frame, self.output_frame]:
            frame.grid_configure(padx=self.pad_config["frame_padx"], pady=self.pad_config["frame_pady"])

    def check_environment(self):
        """检测ADB和Fastboot环境"""
        self.insert_output("\n=== 开始环境检测 ===\n")
        try:
            # 检测ADB
            subprocess.run(["adb", "version"],
                         check=True,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         creationflags=subprocess.CREATE_NO_WINDOW)
            
            # 检测Fastboot
            subprocess.run(["fastboot", "--version"],
                         check=True,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         creationflags=subprocess.CREATE_NO_WINDOW)
            
            self.env_status.config(text="环境正常", foreground="green")
            self.insert_output("检测结果：环境正常\n")
            return True
        except Exception as e:
            self.env_status.config(text="环境异常", foreground="red")
            self.insert_output("检测结果：环境异常\n")
            self.insert_output(f"错误信息：{str(e)}\n")
            return False

    def install_drivers(self):
        """显示驱动安装指南到输出窗口"""
        self.insert_output("\n=== Fastboot环境配置指南 ===\n")
        guide = """1. 下载Google USB驱动：
   官方地址：https://developer.android.com/studio/run/win-usb
    
2. 下载Platform Tools：
   下载页面：https://developer.android.com/studio/releases/platform-tools
   
3. 解压platform-tools到系统目录（例如：C:\\platform-tools）
   
4. 添加环境变量：
   - 右键点击"此电脑"选择"属性"
   - 进入"高级系统设置" -> "环境变量"
   - 在Path中添加platform-tools目录
   
5. 设备连接：
   - 启用USB调试模式（设置 -> 开发者选项）
   - 首次连接需要在设备上授权ADB调试"""
        self.insert_output(guide + "\n")

    def select_file(self):
        """选择镜像文件"""
        file_path = filedialog.askopenfilename(filetypes=[("镜像文件", "*.img")])
        if file_path:
            self.current_file = file_path
            self.update_file_info()
            self.add_to_history(file_path)

    def update_file_info(self):
        """更新文件信息显示"""
        if self.current_file:
            filename = os.path.basename(self.current_file)
            mtime = os.path.getmtime(self.current_file)
            timestamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            self.file_info.config(text=f"{filename} - 最后修改: {timestamp}")

    def add_to_history(self, path):
        """维护历史记录"""
        if path in self.file_history:
            self.file_history.remove(path)
        self.file_history.insert(0, path)
        self.history_combo["values"] = self.file_history[:10]
        self.save_history()

    def save_history(self):
        """保存历史记录到文件"""
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.file_history[:10], f)
        except Exception as e:
            self.insert_output(f"\n保存历史记录失败：{str(e)}\n")

    def load_history(self):
        """加载历史记录"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    self.file_history = json.load(f)
                    self.history_combo["values"] = self.file_history
            except Exception as e:
                self.insert_output(f"\n加载历史记录失败：{str(e)}\n")

    def on_history_select(self, event):
        """历史记录选择事件"""
        self.current_file = self.history_combo.get()
        self.update_file_info()

    def start_flash(self):
        """启动自动刷写流程"""
        if not self.current_file:
            messagebox.showwarning("警告", "请先选择要刷写的镜像文件！")
            return
        
        if not self.check_environment():
            return
        
        filename = os.path.basename(self.current_file)
        partition = self.partition_map.get(filename.lower())
        
        if not partition:
            messagebox.showerror("错误", f"无法自动识别 {filename} 对应的分区！")
            return
        
        self.output_text.delete(1.0, tk.END)
        self.insert_output("=== 开始自动刷写流程 ===\n")
        
        try:
            # 步骤1：等待设备并重启到fastboot模式
            self.run_command("adb wait-for-device")
            self.run_command("adb reboot bootloader")
            
            # 步骤2：等待进入fastboot模式
            if not self.wait_for_fastboot():
                messagebox.showerror("错误", "设备未进入Fastboot模式！")
                return
            
            # 步骤3：执行刷写命令
            cmd = f"fastboot flash {partition} {self.current_file}"
            self.run_command(cmd)
            
            # 步骤4：重启设备
            self.run_command("fastboot reboot")
            self.insert_output("\n✅ 刷写完成，设备已重启！\n")
            
        except Exception as e:
            self.insert_output(f"\n❌ 刷写失败: {str(e)}\n")
            messagebox.showerror("错误", f"刷写失败: {str(e)}")

    def wait_for_fastboot(self, timeout=30):
        """等待设备进入fastboot模式"""
        start_time = time.time()
        self.insert_output("\n等待设备进入Fastboot模式...")
        
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(["fastboot", "devices"],
                                      capture_output=True,
                                      text=True,
                                      creationflags=subprocess.CREATE_NO_WINDOW)
                if "fastboot" in result.stdout:
                    self.insert_output("检测到Fastboot设备！\n")
                    return True
                time.sleep(1)
            except:
                pass
        
        return False

    def run_command(self, command):
        """执行命令并显示输出"""
        self.insert_output(f"\n>>> 执行命令: {command}\n")
        try:
            process = subprocess.Popen(command.split(),
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     text=True,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.insert_output(output)
            
            returncode = process.poll()
            self.insert_output(f"\n返回代码: {returncode}\n")
            return returncode == 0
            
        except Exception as e:
            self.insert_output(f"命令执行失败: {str(e)}\n")
            raise

    def insert_output(self, text):
        """插入文本并自动滚动"""
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.update_idletasks()

class LogTools(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.history_file = 'keyword_history.txt'
        self.keyword_history = self.load_history()
        
        # 新增：创建默认目录
        self.default_dir = "D:/Joyboy"
        os.makedirs(self.default_dir, exist_ok=True)
        self.create_header()
        self.create_widgets()
        self.queues = {}
        self.log_windows = {}
        self.processes = {}
        self.running_flags = {}  # 新增运行状态标志

    def create_header(self):
        """创建标题和返回按钮"""
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky="ew", pady=5)
        
        ttk.Label(header_frame, text="日志过滤", font=("微软雅黑", 12)).pack(side="left", padx=10)
        ttk.Button(header_frame, text="返回主菜单",
                 command=lambda: self.controller.show_frame("MainMenu")).pack(side="right", padx=10)
        
        # 使header_frame的列自动扩展
        self.columnconfigure(0, weight=1)

    def load_history(self):
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f.readlines()]
        return []

    def save_history(self):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            for item in self.keyword_history:
                f.write(f"{item}\n")

    def create_widgets(self):
        # Logcat配置
        self.logcat_frame = ttk.LabelFrame(self, text="Logcat配置")
        self.logcat_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.logcat_enabled = tk.BooleanVar()
        ttk.Checkbutton(self.logcat_frame, text="启用", variable=self.logcat_enabled).grid(row=0, column=0, padx=5, sticky="w")

        ttk.Label(self.logcat_frame, text="关键词（逗号分隔）:").grid(row=1, column=0, padx=5, sticky="w")
        self.logcat_keyword = ttk.Entry(self.logcat_frame, width=30)
        self.logcat_keyword.grid(row=1, column=1, padx=5, sticky="ew")

        self.logcat_case = tk.BooleanVar()
        ttk.Checkbutton(self.logcat_frame, text="区分大小写", variable=self.logcat_case).grid(row=1, column=2, padx=5, sticky="w")

        self.logcat_history_var = tk.BooleanVar()
        ttk.Checkbutton(self.logcat_frame, text="历史记录", variable=self.logcat_history_var, 
                       command=lambda: self.toggle_history('logcat')).grid(row=2, column=0, padx=5, sticky="w")
        self.logcat_history = ttk.Combobox(self.logcat_frame, values=self.keyword_history, width=28)
        self.logcat_history.grid(row=2, column=1, padx=5, sticky="ew")
        self.logcat_history.grid_remove()

        ttk.Label(self.logcat_frame, text="保存路径:").grid(row=3, column=0, padx=5, sticky="w")
        self.logcat_path = ttk.Entry(self.logcat_frame, width=30)
        # 新增：设置默认logcat路径
        self.logcat_path.insert(0, f"{self.default_dir}/logcat.txt")  # 关键修改点1
        self.logcat_path.grid(row=3, column=1, padx=5, sticky="ew")
        ttk.Button(self.logcat_frame, text="浏览", command=lambda: self.browse('logcat')).grid(row=3, column=2, padx=5)

        # Kmsg配置
        self.kmsg_frame = ttk.LabelFrame(self, text="Kmsg配置")
        self.kmsg_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        self.kmsg_enabled = tk.BooleanVar()
        ttk.Checkbutton(self.kmsg_frame, text="启用", variable=self.kmsg_enabled).grid(row=0, column=0, padx=5, sticky="w")

        ttk.Label(self.kmsg_frame, text="关键词（逗号分隔）:").grid(row=1, column=0, padx=5, sticky="w")
        self.kmsg_keyword = ttk.Entry(self.kmsg_frame, width=30)
        self.kmsg_keyword.grid(row=1, column=1, padx=5, sticky="ew")

        self.kmsg_case = tk.BooleanVar()
        ttk.Checkbutton(self.kmsg_frame, text="区分大小写", variable=self.kmsg_case).grid(row=1, column=2, padx=5, sticky="w")

        self.kmsg_history_var = tk.BooleanVar()
        ttk.Checkbutton(self.kmsg_frame, text="历史记录", variable=self.kmsg_history_var,
                       command=lambda: self.toggle_history('kmsg')).grid(row=2, column=0, padx=5, sticky="w")
        self.kmsg_history = ttk.Combobox(self.kmsg_frame, values=self.keyword_history, width=28)
        self.kmsg_history.grid(row=2, column=1, padx=5, sticky="ew")
        self.kmsg_history.grid_remove()

        ttk.Label(self.kmsg_frame, text="保存路径:").grid(row=3, column=0, padx=5, sticky="w")
        self.kmsg_path = ttk.Entry(self.kmsg_frame, width=30)
        # 新增：设置默认kmsg路径
        self.kmsg_path.insert(0, f"{self.default_dir}/kmsg.txt")  # 关键修改点2
        self.kmsg_path.grid(row=3, column=1, padx=5, sticky="ew")
        ttk.Button(self.kmsg_frame, text="浏览", command=lambda: self.browse('kmsg')).grid(row=3, column=2, padx=5)

        # qsee_log配置
        self.qsee_log_frame = ttk.LabelFrame(self, text="qsee_log配置")
        self.qsee_log_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        self.qsee_log_enabled = tk.BooleanVar()
        ttk.Checkbutton(self.qsee_log_frame, text="启用", variable=self.qsee_log_enabled).grid(row=0, column=0, padx=5, sticky="w")

        ttk.Label(self.qsee_log_frame, text="关键词（逗号分隔）:").grid(row=1, column=0, padx=5, sticky="w")
        self.qsee_log_keyword = ttk.Entry(self.qsee_log_frame, width=30)
        self.qsee_log_keyword.grid(row=1, column=1, padx=5, sticky="ew")

        self.qsee_log_case = tk.BooleanVar()
        ttk.Checkbutton(self.qsee_log_frame, text="区分大小写", variable=self.qsee_log_case).grid(row=1, column=2, padx=5, sticky="w")

        self.qsee_log_history_var = tk.BooleanVar()
        ttk.Checkbutton(self.qsee_log_frame, text="历史记录", variable=self.qsee_log_history_var, 
                       command=lambda: self.toggle_history('qsee_log')).grid(row=2, column=0, padx=5, sticky="w")
        self.qsee_log_history = ttk.Combobox(self.qsee_log_frame, values=self.keyword_history, width=28)
        self.qsee_log_history.grid(row=2, column=1, padx=5, sticky="ew")
        self.qsee_log_history.grid_remove()

        ttk.Label(self.qsee_log_frame, text="保存路径:").grid(row=3, column=0, padx=5, sticky="w")
        self.qsee_log_path = ttk.Entry(self.qsee_log_frame, width=30)
        # 新增：设置默认qsee_log路径
        self.qsee_log_path.insert(0, f"{self.default_dir}/qsee_log.txt")  # 关键修改点1
        self.qsee_log_path.grid(row=3, column=1, padx=5, sticky="ew")
        ttk.Button(self.qsee_log_frame, text="浏览", command=lambda: self.browse('qsee_log')).grid(row=3, column=2, padx=5)


        # 控制按钮
        ttk.Button(self, text="开始抓取", command=self.start).grid(row=4, column=0, pady=10, sticky="ew")

    def create_window(self, window_id, log_type, path):
        window = tk.Toplevel(self)
        window.title(f"{log_type}日志 - {os.path.basename(path)}")
        window.geometry("800x400")
        
        text_area = scrolledtext.ScrolledText(window, wrap=tk.WORD)
        text_area.pack(expand=True, fill='both')
        
        ttk.Button(window, text="打开文件", command=lambda: os.startfile(path)).pack(pady=5)
        
        # 修正1：确保使用UTF-8编码打开文件
        self.log_windows[window_id] = {
            'window': window,
            'text_area': text_area,
            'file': open(path, 'a', encoding='utf-8', errors='replace')
        }

    def toggle_history(self, log_type):
        if log_type == 'logcat':
            if self.logcat_history_var.get():
                self.logcat_history.grid()
                self.logcat_history.bind('<<ComboboxSelected>>', lambda e: self.select_history('logcat'))
            else:
                self.logcat_history.grid_remove()
        elif log_type == 'kmsg':
            if self.kmsg_history_var.get():
                self.kmsg_history.grid()
                self.kmsg_history.bind('<<ComboboxSelected>>', lambda e: self.select_history('kmsg'))
            else:
                self.kmsg_history.grid_remove()
        else:
            if self.qsee_log_history_var.get():
                self.qsee_log_history.grid()
                self.qsee_log_history.bind('<<ComboboxSelected>>', lambda e: self.select_history('qsee_log'))
            else:
                self.qsee_log_history.grid_remove()

    def select_history(self, log_type):
        if log_type == 'logcat':
            self.logcat_keyword.delete(0, tk.END)
            self.logcat_keyword.insert(0, self.logcat_history.get())
        elif log_type == 'kmsg':
            self.kmsg_keyword.delete(0, tk.END)
            self.kmsg_keyword.insert(0, self.kmsg_history.get())
        else:
            self.qsee_log_keyword.delete(0, tk.END)
            self.qsee_log_keyword.insert(0, self.kmsg_history.get())

    def browse(self, log_type):
        path = filedialog.asksaveasfilename(defaultextension=".log")
        if path:
            if log_type == 'logcat':
                self.logcat_path.delete(0, tk.END)
                self.logcat_path.insert(0, path)
            elif log_type == 'kmsg':
                self.kmsg_path.delete(0, tk.END)
                self.kmsg_path.insert(0, path)
            else:
                self.qsee_log_path.delete(0, tk.END)
                self.qsee_log_path.insert(0, path)

    def start(self):
        tasks = []
        if self.logcat_enabled.get():
            logcat_keyword = self.logcat_keyword.get().strip()
            tasks.append(('logcat', logcat_keyword, self.logcat_path.get(), self.logcat_case.get()))
        
        if self.kmsg_enabled.get():
            kmsg_keyword = self.kmsg_keyword.get().strip()
            tasks.append(('kmsg', kmsg_keyword, self.kmsg_path.get(), self.kmsg_case.get()))

        if self.qsee_log_enabled.get():
            qsee_log_keyword = self.qsee_log_keyword.get().strip()
            tasks.append(('qsee_log', qsee_log_keyword, self.qsee_log_path.get(), self.qsee_log_case.get()))

        if not tasks:
            messagebox.showerror("错误", "请至少选择一个日志类型")
            return
    
        for task in tasks:
            log_type, keywords, path, case = task
            # 修改验证逻辑（仅检查路径）
            if not path:  # 移除了对keywords的检查
                messagebox.showerror("错误", "请填写保存路径")
                return
            
            # 历史记录处理（空关键词不保存）
            if keywords and keywords not in self.keyword_history:
                self.keyword_history.insert(0, keywords)
                # 保持历史记录不超过20条
                if len(self.keyword_history) > 20:
                    self.keyword_history.pop()
                self.save_history()
                self.logcat_history['values'] = self.keyword_history
                self.kmsg_history['values'] = self.keyword_history
                self.qsee_log_history['values'] = self.keyword_history

            q = queue.Queue()
            window_id = str(uuid.uuid4())
            self.queues[window_id] = q
            self.create_window(window_id, log_type, path)
            self.running_flags[window_id] = True  # 新增运行标志
            threading.Thread(target=self.capture, args=(log_type, keywords, path, case, q, window_id), daemon=True).start()
            self.after(100, self.update_display, window_id)

    def create_window(self, window_id, log_type, path):
        window = tk.Toplevel(self)
        window.title(f"{log_type}日志 - {os.path.basename(path)}")
        window.geometry("800x400")
        
        text_area = scrolledtext.ScrolledText(window, wrap=tk.WORD)
        text_area.pack(expand=True, fill='both')
        
        ttk.Button(window, text="打开文件", command=lambda: os.startfile(path)).pack(pady=5)
        
        self.log_windows[window_id] = {
            'window': window,
            'text_area': text_area,
            'file': open(path, 'a', encoding='utf-8')
        }
        window.protocol("WM_DELETE_WINDOW", lambda: self.close_window(window_id))

    def close_window(self, window_id):
        """安全关闭窗口的流程"""
        if window_id in self.running_flags:
            self.running_flags[window_id] = False  # 停止捕获线程
            
        if window_id in self.processes:
            self.processes[window_id].terminate()  # 终止ADB进程
            del self.processes[window_id]
            
        if window_id in self.log_windows:
            self.log_windows[window_id]['file'].close()  # 关闭文件
            self.log_windows[window_id]['window'].destroy()
            del self.log_windows[window_id]

    def capture(self, log_type, keywords, path, case_sensitive, q, window_id):
        keywords = [k.strip() for k in keywords.split(',')]
        cmd = ['adb', 'shell', 'logcat'] if log_type == 'logcat' else (
    ['adb', 'shell', 'cat', '/proc/kmsg'] if log_type == 'kmsg' 
    else ['adb', 'shell', 'cat', '/proc/tzdbg/qsee_log']
)
        
        try:
            proc = subprocess.Popen(cmd, 
                                   stdout=subprocess.PIPE,
                                   text=True,
                                   encoding='utf-8',
                                   errors='replace')
            self.processes[window_id] = proc
            
            # 新增批量处理机制
            buffer = []
            last_flush = time.time()
            
            while self.running_flags.get(window_id, False):
                line = proc.stdout.readline()
                if not line:
                    time.sleep(0.1)  # 防止CPU空转
                    continue
                
                if self.check_filter(line, keywords, case_sensitive):
                    buffer.append(line)
                    q.put(line)  # 先存入队列
                    
                    # 批量写入文件（每100条或0.5秒刷新一次）
                    if len(buffer) >= 100 or (time.time() - last_flush) > 0.5:
                        self.log_windows[window_id]['file'].writelines(buffer)
                        buffer.clear()
                        last_flush = time.time()
                        
                # 检查进程状态
                if proc.poll() is not None:
                    break
                
            # 写入剩余缓存
            if buffer:
                self.log_windows[window_id]['file'].writelines(buffer)
                
        except Exception as e:
            q.put(f"Error: {str(e)}")
        finally:
            self.close_window(window_id)

    def check_filter(self, line, keywords, case_sensitive):
        if not keywords:
            return True
        line_check = line if case_sensitive else line.lower()
        return any(
            (kw if case_sensitive else kw.lower()) in line_check 
            for kw in keywords
        )

    def update_display(self, window_id):
        if window_id not in self.running_flags or not self.running_flags[window_id]:
            return
        
        try:
            # 批量更新界面（每次最多处理50行）
            max_lines = 50
            processed = 0
            
            while not self.queues[window_id].empty() and processed < max_lines:
                line = self.queues[window_id].get_nowait()
                self.log_windows[window_id]['text_area'].insert(tk.END, line)
                processed += 1
                
            self.log_windows[window_id]['text_area'].see(tk.END)
            
        except queue.Empty:
            pass
        finally:
            self.after(50, self.update_display, window_id)



if __name__ == "__main__":
    app = MainApplication()
    # 配置样式
    style = ttk.Style()
    style.configure('Status.TFrame', background='#f0f0f0', borderwidth=2, relief="groove")
    app.mainloop()