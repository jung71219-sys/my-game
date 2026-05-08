import sys
import os
import json
import csv
import time
import requests
import subprocess
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QDoubleSpinBox,
                             QMessageBox, QTabWidget, QComboBox, QSizePolicy, QFileDialog)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QColor



# --- 版本資訊 ---
CURRENT_VERSION = "1.0.0"
# GitHub Raw JSON 網址
UPDATE_URL = "https://raw.githubusercontent.com/jung71219-sys/my-game/main/game_data.json"


# --- 關鍵：處理打包後的檔案路徑 ---
def resource_path(relative_path):
    """ 取得資源絕對路徑，支援 PyInstaller 打包環境 """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)



class GameTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"遊戲練功效率紀錄工具 v{CURRENT_VERSION}")
        self.resize(1200, 900)
        
        # 資料檔案路徑
        self.data_file = "game_data.json"
        
        # 計時器變數
        self.start_time = None
        self.timer_display = QTimer()
        self.timer_display.timeout.connect(self.sync_realtime_updates)



        # 裝備資料存儲
        self.equip_data = {
            "武器": [], "項鍊": [], "卡片": [], 
            "坐騎": [], "鬥魂": [], "寵物": []
        }



        # 設定視窗圖示
        icon_file = resource_path("Exp.ico")
        if os.path.exists(icon_file):
            self.setWindowIcon(QIcon(icon_file))



        # 主分頁系統
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)



        self.record_tab = QWidget()
        self.analysis_tab = QWidget()
        self.config_tab = QWidget()



        self.tabs.addTab(self.record_tab, "練功紀錄")
        self.tabs.addTab(self.analysis_tab, "數據分析")
        self.tabs.addTab(self.config_tab, "裝備設定")



        self.setup_record_tab()
        self.setup_analysis_tab()
        self.setup_config_tab()
        
        # 載入存檔
        self.load_data()
        
        # 預設套用深色模式
        self.is_dark_mode = False
        self.toggle_dark_mode()
        
        # 啟動後檢查更新 (延遲 3 秒執行，避免卡到介面開啟)
        QTimer.singleShot(3000, self.auto_check_update)



    def setup_record_tab(self):
        layout = QVBoxLayout(self.record_tab)
        layout.setSpacing(10)



        plus_levels = [f"+{i}" for i in range(13)]



        def set_resizable(widget):
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)



        # --- 搜尋與工具排 ---
        tool_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜尋備註或裝備名稱...")
        self.search_input.textChanged.connect(self.filter_table)
        
        self.dark_mode_btn = QPushButton("切換深淺模式")
        self.dark_mode_btn.clicked.connect(self.toggle_dark_mode)
        
        self.import_csv_btn = QPushButton("匯入 CSV")
        self.import_csv_btn.clicked.connect(self.import_from_csv)
        
        self.export_csv_btn = QPushButton("匯出 CSV")
        self.export_csv_btn.clicked.connect(self.export_to_csv)
        
        tool_layout.addWidget(QLabel("搜尋:"))
        tool_layout.addWidget(self.search_input)
        tool_layout.addWidget(self.dark_mode_btn)
        tool_layout.addWidget(self.import_csv_btn)
        tool_layout.addWidget(self.export_csv_btn)



        # --- 第一排 ---
        input_layout1 = QHBoxLayout()
        input_layout1.setSpacing(15)
        
        self.weapon_plus = QComboBox(); self.weapon_plus.addItems(plus_levels); self.weapon_plus.setFixedWidth(55)
        self.weapon_input = QComboBox(); set_resizable(self.weapon_input)
        
        self.neck_plus = QComboBox(); self.neck_plus.addItems(plus_levels); self.neck_plus.setFixedWidth(55)
        self.neck_input = QComboBox(); set_resizable(self.neck_input)
        
        self.mount_plus = QComboBox(); self.mount_plus.addItems(plus_levels); self.mount_plus.setFixedWidth(55)
        self.mount_input = QComboBox(); set_resizable(self.mount_input)
        
        self.soul_plus = QComboBox(); self.soul_plus.addItems(plus_levels); self.soul_plus.setFixedWidth(55)
        self.soul_input = QComboBox(); set_resizable(self.soul_input)



        input_layout1.addWidget(QLabel("武器:"))
        input_layout1.addWidget(self.weapon_plus); input_layout1.addWidget(self.weapon_input)
        input_layout1.addWidget(QLabel("項鍊:"))
        input_layout1.addWidget(self.neck_plus); input_layout1.addWidget(self.neck_input)
        input_layout1.addWidget(QLabel("坐騎:"))
        input_layout1.addWidget(self.mount_plus); input_layout1.addWidget(self.mount_input)
        input_layout1.addWidget(QLabel("鬥魂:"))
        input_layout1.addWidget(self.soul_plus); input_layout1.addWidget(self.soul_input)



        # --- 第二排 (卡片/寵物) ---
        input_layout_cards = QHBoxLayout()
        self.card_plus1 = QComboBox(); self.card_plus1.addItems(plus_levels); self.card_plus1.setFixedWidth(55)
        self.card_input1 = QComboBox(); set_resizable(self.card_input1)
        self.card_plus2 = QComboBox(); self.card_plus2.addItems(plus_levels); self.card_plus2.setFixedWidth(55)
        self.card_input2 = QComboBox(); set_resizable(self.card_input2)
        self.card_plus3 = QComboBox(); self.card_plus3.addItems(plus_levels); self.card_plus3.setFixedWidth(55)
        self.card_input3 = QComboBox(); set_resizable(self.card_input3)
        self.card_plus4 = QComboBox(); self.card_plus4.addItems(plus_levels); self.card_plus4.setFixedWidth(55)
        self.card_input4 = QComboBox(); set_resizable(self.card_input4)
        self.pet_input = QComboBox(); set_resizable(self.pet_input)



        combos = [self.weapon_input, self.neck_input, self.card_input1, self.card_input2,
                  self.card_input3, self.card_input4, self.mount_input, self.soul_input, self.pet_input]
        for combo in combos:
            combo.setEditable(True)
            combo.setMinimumWidth(0)



        input_layout_cards.addWidget(QLabel("卡1:")); input_layout_cards.addWidget(self.card_plus1); input_layout_cards.addWidget(self.card_input1)
        input_layout_cards.addWidget(QLabel("卡2:")); input_layout_cards.addWidget(self.card_plus2); input_layout_cards.addWidget(self.card_input2)
        input_layout_cards.addWidget(QLabel("卡3:")); input_layout_cards.addWidget(self.card_plus3); input_layout_cards.addWidget(self.card_input3)
        input_layout_cards.addWidget(QLabel("卡4:")); input_layout_cards.addWidget(self.card_plus4); input_layout_cards.addWidget(self.card_input4)
        input_layout_cards.addWidget(QLabel("寵物:")); input_layout_cards.addWidget(self.pet_input)



        # --- 第三排 (數值/計時) ---
        input_layout2 = QHBoxLayout()
        self.crit_input = QLineEdit(); set_resizable(self.crit_input); self.crit_input.setPlaceholderText("爆傷 %")
        self.atk_boost_input = QLineEdit(); set_resizable(self.atk_boost_input); self.atk_boost_input.setPlaceholderText("攻擊力增幅")
        
        self.time_input = QDoubleSpinBox(); set_resizable(self.time_input)
        self.time_input.setRange(0.00, 999999); self.time_input.setSuffix(" 分鐘")



        self.exp_start_input = QDoubleSpinBox(); set_resizable(self.exp_start_input)
        self.exp_start_input.setRange(0, 100.00000); self.exp_start_input.setDecimals(5); self.exp_start_input.setSuffix(" % (起始)")



        self.exp_end_input = QDoubleSpinBox(); set_resizable(self.exp_end_input)
        self.exp_end_input.setRange(0, 100.00000); self.exp_end_input.setDecimals(5); self.exp_end_input.setSuffix(" % (結束)")
        
        self.note_input = QLineEdit(); set_resizable(self.note_input); self.note_input.setPlaceholderText("備註事項")



        input_layout2.addWidget(QLabel("爆傷:")); input_layout2.addWidget(self.crit_input)
        input_layout2.addWidget(QLabel("攻增:")); input_layout2.addWidget(self.atk_boost_input)
        input_layout2.addWidget(QLabel("時長:")); input_layout2.addWidget(self.time_input)
        input_layout2.addWidget(QLabel("起始:")); input_layout2.addWidget(self.exp_start_input)
        input_layout2.addWidget(QLabel("結束:")); input_layout2.addWidget(self.exp_end_input)
        input_layout2.addWidget(QLabel("備註:")); input_layout2.addWidget(self.note_input)



        # --- 第四排 (按鈕工具排) ---
        btn_layout = QHBoxLayout()
        self.timer_btn = QPushButton("開始計時")
        self.timer_btn.setStyleSheet("background-color: #673AB7; color: white; font-weight: bold; height: 35px;")
        self.timer_btn.clicked.connect(self.toggle_timer)



        self.copy_btn = QPushButton("複製前一筆")
        self.copy_btn.clicked.connect(self.copy_last_record)



        self.clear_btn = QPushButton("一鍵清空")
        self.clear_btn.clicked.connect(self.clear_inputs)



        add_btn = QPushButton("新增紀錄")
        add_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; height: 35px;")
        add_btn.clicked.connect(self.add_record)



        edit_btn = QPushButton("修改選中列")
        edit_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; height: 35px;")
        edit_btn.clicked.connect(self.edit_record)



        del_btn = QPushButton("刪除選中紀錄")
        del_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; height: 35px;")
        del_btn.clicked.connect(self.delete_record)



        btn_layout.addWidget(self.timer_btn)
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(del_btn)



        # --- 表格 ---
        self.table = QTableWidget()
        self.table.setColumnCount(17)
        self.table.setHorizontalHeaderLabels([
            "武器", "項鍊", "卡片1", "卡片2", "卡片3", "卡片4", "坐騎", "鬥魂", "寵物", 
            "爆傷", "攻增", "時間", "前經驗(%)", "後經驗(%)", "獲得(%)", "時薪(%/hr)", "備註"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemDoubleClicked.connect(self.load_to_inputs)



        layout.addLayout(tool_layout)
        layout.addLayout(input_layout1)
        layout.addLayout(input_layout_cards)
        layout.addLayout(input_layout2)
        layout.addLayout(btn_layout)
        layout.addWidget(self.table)



    def setup_analysis_tab(self):
        main_layout = QVBoxLayout(self.analysis_tab)
        
        # 上方：升級倒數區
        countdown_group = QHBoxLayout()
        self.next_lvl_exp = QDoubleSpinBox()
        self.next_lvl_exp.setRange(0, 100.00000)
        self.next_lvl_exp.setDecimals(5)
        self.next_lvl_exp.setPrefix("距離下級還差: ")
        self.next_lvl_exp.setSuffix(" %")
        self.next_lvl_exp.valueChanged.connect(self.calculate_countdown)
        
        self.countdown_label = QLabel("預計升級所需時間: --小時 --分")
        self.countdown_label.setStyleSheet("font-weight: bold; color: #FF9800; font-size: 14px;")
        
        countdown_group.addWidget(self.next_lvl_exp)
        countdown_group.addWidget(self.countdown_label)
        main_layout.addLayout(countdown_group)



        # 中間：排行榜
        info_label = QLabel("### 效率排行榜 (依據時薪 %/hr 排序)")
        info_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(info_label)



        self.rank_table = QTableWidget()
        self.rank_table.setColumnCount(5)
        self.rank_table.setHorizontalHeaderLabels(["排名", "關鍵裝備組合", "平均爆傷", "最高時薪(%)", "紀錄次數"])
        self.rank_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        main_layout.addWidget(self.rank_table)



        refresh_rank_btn = QPushButton("刷新分析數據")
        refresh_rank_btn.setFixedHeight(40)
        refresh_rank_btn.clicked.connect(self.update_analysis)
        main_layout.addWidget(refresh_rank_btn)



    def setup_config_tab(self):
        layout = QVBoxLayout(self.config_tab)
        layout.setSpacing(10)
        
        # --- 搜尋功能排 ---
        config_search_layout = QHBoxLayout()
        self.config_search_input = QLineEdit()
        self.config_search_input.setPlaceholderText("搜尋已存裝備名稱...")
        self.config_search_input.textChanged.connect(self.filter_config_table)
        config_search_layout.addWidget(QLabel("搜尋裝備:"))
        config_search_layout.addWidget(self.config_search_input)
        
        config_input_layout = QHBoxLayout()
        self.cate_combo = QComboBox()
        self.cate_combo.addItems(["武器", "項鍊", "卡片", "坐騎", "鬥魂", "寵物"])
        self.cate_combo.currentIndexChanged.connect(self.filter_config_table)
        self.item_name_input = QLineEdit()
        self.item_name_input.setPlaceholderText("輸入裝備名稱")
        self.item_name_input.returnPressed.connect(self.add_config_item)
        
        add_item_btn = QPushButton("新增至選單")
        add_item_btn.clicked.connect(self.add_config_item)
        
        config_input_layout.addWidget(QLabel("分類:"))
        config_input_layout.addWidget(self.cate_combo)
        config_input_layout.addWidget(self.item_name_input)
        config_input_layout.addWidget(add_item_btn)



        self.config_table = QTableWidget()
        self.config_table.setColumnCount(2)
        self.config_table.setHorizontalHeaderLabels(["類別", "名稱"])
        self.config_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.config_table.itemChanged.connect(self.on_config_item_changed)



        del_item_btn = QPushButton("刪除裝備項目")
        del_item_btn.clicked.connect(self.delete_config_item)



        layout.addLayout(config_search_layout)
        layout.addLayout(config_input_layout)
        layout.addWidget(self.config_table)
        layout.addWidget(del_item_btn)



    # --- 更新與資料同步邏輯 ---
    def auto_check_update(self):
        """ 檢查版本與同步遠端裝備資料 """
        try:
            response = requests.get(UPDATE_URL, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # --- 同步遠端裝備資料 (equip_data) ---
                if "equip_data" in data:
                    remote_equip = data["equip_data"]
                    for key in self.equip_data:
                        if key in remote_equip:
                            # 合併本地與遠端裝備，去除重複
                            combined = list(set(self.equip_data[key] + remote_equip[key]))
                            self.equip_data[key] = combined
                    
                    self.refresh_all_combos()
                    self.update_config_table_from_data()
                    self.save_data()



                # --- 檢查版本更新 ---
                remote_version = data.get("version", CURRENT_VERSION)
                remote_v_list = [int(x) for x in remote_version.split(".")]
                current_v_list = [int(x) for x in CURRENT_VERSION.split(".")]



                if remote_v_list > current_v_list:
                    reply = QMessageBox.information(
                        self, "發現新版本", 
                        f"目前版本: v{CURRENT_VERSION}\n最新版本: v{remote_version}\n\n"
                        f"更新內容：\n{data.get('changelog', '無')}\n\n是否立即自動更新並重啟？",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        self.execute_auto_update(data.get("url", ""))
        except Exception as e:
            print(f"檢查更新失敗: {e}")



    def execute_auto_update(self, download_url):
        """ 下載檔案並透過批次檔進行自我替換 """
        if not download_url:
            QMessageBox.warning(self, "錯誤", "找不到下載連結")
            return



        try:
            current_exe = os.path.abspath(sys.executable)
            new_exe = current_exe + ".new"



            response = requests.get(download_url, stream=True)
            if response.status_code == 200:
                with open(new_exe, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            else:
                raise Exception("下載失敗，伺服器回應錯誤")



            bat_path = os.path.join(os.path.dirname(current_exe), "update_helper.bat")
            exe_name = os.path.basename(current_exe)
            
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(f"""@echo off
chcp 65001 >nul
taskkill /f /im "{exe_name}" >nul 2>&1
timeout /t 1 /nobreak >nul
del /f /q "{current_exe}"
move /y "{new_exe}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
""")



            subprocess.Popen([bat_path], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            QApplication.quit()
            sys.exit()



        except Exception as e:
            QMessageBox.critical(self, "更新錯誤", f"更新過程中發生錯誤：\n{str(e)}")



    # --- 功能邏輯 ---
    def sync_realtime_updates(self):
        if self.start_time:
            elapsed_mins = (time.time() - self.start_time) / 60
            self.timer_btn.setText(f"結束計時 ({elapsed_mins:.2f}m)")
            self.calculate_countdown()



    def toggle_timer(self):
        if self.start_time is None:
            self.start_time = time.time()
            self.timer_btn.setText("結束計時 (0.00m)")
            self.timer_btn.setStyleSheet("background-color: #FF5722; color: white; font-weight: bold; height: 35px;")
            self.timer_display.start(1000) 
        else:
            elapsed = (time.time() - self.start_time) / 60
            self.time_input.setValue(elapsed)
            self.start_time = None
            self.timer_btn.setText("開始計時")
            self.timer_btn.setStyleSheet("background-color: #673AB7; color: white; font-weight: bold; height: 35px;")
            self.timer_display.stop()
            self.calculate_countdown()



    def calculate_countdown(self):
        diff_exp = self.next_lvl_exp.value()
        if diff_exp <= 0:
            self.countdown_label.setText("預計升級所需時間: --小時 --分")
            return



        exps = []
        for r in range(self.table.rowCount()):
            try:
                if not self.table.isRowHidden(r):
                    val = float(self.table.item(r, 15).text())
                    if val > 0: exps.append(val)
            except: pass
        
        avg_hr = sum(exps) / len(exps) if exps else 0
        if self.start_time:
            current_diff = self.exp_end_input.value() - self.exp_start_input.value()
            current_mins = (time.time() - self.start_time) / 60
            if current_mins > 0.1 and current_diff > 0:
                current_hr = (current_diff / current_mins) * 60
                avg_hr = (avg_hr + current_hr) / 2 if avg_hr > 0 else current_hr



        if avg_hr <= 0:
            self.countdown_label.setText("預計升級所需時間: 尚未有數據")
            return
            
        total_hours = diff_exp / avg_hr
        hrs = int(total_hours)
        mins = int((total_hours - hrs) * 60)
        
        if hrs > 9999:
            self.countdown_label.setText(f"預計升級所需時間: 超過 9999 小時")
        else:
            self.countdown_label.setText(f"預計升級所需時間: {hrs}小時 {mins}分")



    def clear_inputs(self):
        self.time_input.setValue(0)
        self.exp_start_input.setValue(0)
        self.exp_end_input.setValue(0)
        self.note_input.clear()



    def copy_last_record(self):
        if self.table.rowCount() > 0:
            last_row = self.table.rowCount() - 1
            self.load_to_inputs_by_row(last_row)
            try:
                prev_end = float(self.table.item(last_row, 13).text())
                self.exp_start_input.setValue(prev_end)
            except: pass



    def add_record(self):
        try:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.update_row_from_inputs(row)
            self.save_data()
            self.apply_conditional_formatting()
            self.update_analysis()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", str(e))



    def edit_record(self):
        row = self.table.currentRow()
        if row >= 0:
            self.update_row_from_inputs(row)
            self.save_data()
            self.apply_conditional_formatting()
            self.update_analysis()
        else:
            QMessageBox.warning(self, "提示", "請先點選要修改的資料列")



    def update_row_from_inputs(self, row):
        diff = self.exp_end_input.value() - self.exp_start_input.value()
        minutes = self.time_input.value()
        hourly_exp = (diff / minutes * 60) if minutes > 0 else 0
        
        data = [
            f"({self.weapon_plus.currentText()}){self.weapon_input.currentText()}",
            f"({self.neck_plus.currentText()}){self.neck_input.currentText()}",
            f"({self.card_plus1.currentText()}){self.card_input1.currentText()}",
            f"({self.card_plus2.currentText()}){self.card_input2.currentText()}",
            f"({self.card_plus3.currentText()}){self.card_input3.currentText()}",
            f"({self.card_plus4.currentText()}){self.card_input4.currentText()}",
            f"({self.mount_plus.currentText()}){self.mount_input.currentText()}",
            f"({self.soul_plus.currentText()}){self.soul_input.currentText()}",
            self.pet_input.currentText(),
            self.crit_input.text(), self.atk_boost_input.text(),
            f"{minutes:.2f}", f"{self.exp_start_input.value():.5f}", 
            f"{self.exp_end_input.value():.5f}", f"{diff:.5f}", f"{hourly_exp:.5f}",
            self.note_input.text()
        ]
        for col, val in enumerate(data):
            self.table.setItem(row, col, QTableWidgetItem(str(val)))



    def load_to_inputs(self, item):
        self.load_to_inputs_by_row(item.row())



    def load_to_inputs_by_row(self, row):
        def split_plus(text):
            if text.startswith("(+") and ")" in text:
                idx = text.find(")")
                return text[1:idx], text[idx+1:]
            return "+0", text



        w_p, w_v = split_plus(self.table.item(row, 0).text())
        self.weapon_plus.setCurrentText(w_p); self.weapon_input.setCurrentText(w_v)
        n_p, n_v = split_plus(self.table.item(row, 1).text())
        self.neck_plus.setCurrentText(n_p); self.neck_input.setCurrentText(n_v)
        cp1, cv1 = split_plus(self.table.item(row, 2).text())
        self.card_plus1.setCurrentText(cp1); self.card_input1.setCurrentText(cv1)
        cp2, cv2 = split_plus(self.table.item(row, 3).text())
        self.card_plus2.setCurrentText(cp2); self.card_input2.setCurrentText(cv2)
        cp3, cv3 = split_plus(self.table.item(row, 4).text())
        self.card_plus3.setCurrentText(cp3); self.card_input3.setCurrentText(cv3)
        cp4, cv4 = split_plus(self.table.item(row, 5).text())
        self.card_plus4.setCurrentText(cp4); self.card_input4.setCurrentText(cv4)
        m_p, m_v = split_plus(self.table.item(row, 6).text())
        self.mount_plus.setCurrentText(m_p); self.mount_input.setCurrentText(m_v)
        s_p, s_v = split_plus(self.table.item(row, 7).text())
        self.soul_plus.setCurrentText(s_p); self.soul_input.setCurrentText(s_v)



        self.pet_input.setCurrentText(self.table.item(row, 8).text())
        self.crit_input.setText(self.table.item(row, 9).text())
        self.atk_boost_input.setText(self.table.item(row, 10).text())
        self.time_input.setValue(float(self.table.item(row, 11).text()))
        self.exp_start_input.setValue(float(self.table.item(row, 12).text()))
        self.exp_end_input.setValue(float(self.table.item(row, 13).text()))
        self.note_input.setText(self.table.item(row, 16).text())



    def delete_record(self):
        row = self.table.currentRow()
        if row >= 0:
            if QMessageBox.question(self, "確認", "確定刪除？") == QMessageBox.Yes:
                self.table.removeRow(row)
                self.save_data()
                self.update_analysis()



    def add_config_item(self):
        cate = self.cate_combo.currentText()
        name = self.item_name_input.text().strip()
        if name:
            if name not in self.equip_data[cate]:
                self.equip_data[cate].append(name)
                self.update_config_table_from_data()
                self.refresh_all_combos()
                self.item_name_input.clear()
                self.save_data()



    def on_config_item_changed(self, item):
        if item.column() == 1:
            row = item.row()
            cate_item = self.config_table.item(row, 0)
            if cate_item:
                cate = cate_item.text()
                new_list = []
                for r in range(self.config_table.rowCount()):
                    if self.config_table.item(r, 0).text() == cate:
                        val = self.config_table.item(r, 1).text().strip()
                        if val: new_list.append(val)
                self.equip_data[cate] = list(dict.fromkeys(new_list))
                self.refresh_all_combos()
                self.save_data()



    def delete_config_item(self):
        row = self.config_table.currentRow()
        if row >= 0:
            if QMessageBox.question(self, "確認", "確定刪除此裝備項目？") == QMessageBox.Yes:
                cate = self.config_table.item(row, 0).text()
                name = self.config_table.item(row, 1).text()
                self.config_table.blockSignals(True)
                self.config_table.removeRow(row)
                self.config_table.blockSignals(False)
                if name in self.equip_data[cate]:
                    self.equip_data[cate].remove(name)
                self.refresh_all_combos()
                self.save_data()



    def update_config_table_from_data(self):
        self.config_table.blockSignals(True)
        self.config_table.setRowCount(0)
        for cate, items in self.equip_data.items():
            for name in items:
                row = self.config_table.rowCount()
                self.config_table.insertRow(row)
                item_cate = QTableWidgetItem(cate)
                item_cate.setFlags(item_cate.flags() & ~Qt.ItemIsEditable)
                self.config_table.setItem(row, 0, item_cate)
                self.config_table.setItem(row, 1, QTableWidgetItem(name))
        self.config_table.blockSignals(False)
        self.filter_config_table()



    def filter_config_table(self):
        selected_cate = self.cate_combo.currentText()
        search_text = self.config_search_input.text().lower().strip()
        for r in range(self.config_table.rowCount()):
            cate_item = self.config_table.item(r, 0)
            name_item = self.config_table.item(r, 1)
            if cate_item and name_item:
                match_cate = (cate_item.text() == selected_cate)
                match_search = (search_text in name_item.text().lower())
                self.config_table.setRowHidden(r, not (match_cate and match_search))



    def filter_table(self):
        search_text = self.search_input.text().lower()
        for r in range(self.table.rowCount()):
            match = False
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                if item and search_text in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(r, not match)



    def refresh_all_combos(self):
        self.update_combo_items(self.weapon_input, "武器")
        self.update_combo_items(self.neck_input, "項鍊")
        self.update_combo_items(self.mount_input, "坐騎")
        self.update_combo_items(self.soul_input, "鬥魂")
        self.update_combo_items(self.pet_input, "寵物")
        for cb in [self.card_input1, self.card_input2, self.card_input3, self.card_input4]:
            self.update_combo_items(cb, "卡片")



    def update_combo_items(self, combo, key):
        current = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(self.equip_data[key])
        combo.setCurrentText(current)
        combo.blockSignals(False)



    def apply_conditional_formatting(self):
        exps = []
        for r in range(self.table.rowCount()):
            try:
                exps.append(float(self.table.item(r, 15).text()))
            except: exps.append(0)
        
        if not exps: return
        max_exp = max(exps)
        min_exp = min(exps)
        
        for r in range(self.table.rowCount()):
            try:
                val = float(self.table.item(r, 15).text())
                item = self.table.item(r, 15)
                if val == max_exp and max_exp != min_exp:
                    item.setBackground(QColor("#C8E6C9"))
                    item.setForeground(QColor("#2E7D32"))
                elif val == min_exp and max_exp != min_exp:
                    item.setBackground(QColor("#FFCDD2"))
                    item.setForeground(QColor("#C62828"))
                else:
                    item.setBackground(Qt.transparent)
                    item.setForeground(QColor("#FFFFFF") if self.is_dark_mode else QColor("#000000"))
            except: pass



    def toggle_dark_mode(self):
        self.is_dark_mode = not self.is_dark_mode
        if self.is_dark_mode:
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #121212; color: #E0E0E0; }
                QTableWidget { background-color: #1E1E1E; gridline-color: #333333; color: #FFFFFF; }
                QHeaderView::section { background-color: #333333; color: #FFFFFF; }
                QLineEdit, QDoubleSpinBox, QComboBox { background-color: #2D2D2D; color: #FFFFFF; border: 1px solid #444; }
                QTabWidget::pane { border: 1px solid #444; }
                QTabBar::tab { background: #2D2D2D; color: #BBB; padding: 10px; }
                QTabBar::tab:selected { background: #3D3D3D; color: #FFF; }
                QPushButton { background-color: #333333; color: white; border: 1px solid #555; }
            """)
        else:
            self.setStyleSheet("")
        self.apply_conditional_formatting()



    def export_to_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "匯出 CSV", "", "CSV Files (*.csv)")
        if path:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
                writer.writerow(headers)
                for r in range(self.table.rowCount()):
                    row = [self.table.item(r, c).text() for c in range(self.table.columnCount())]
                    writer.writerow(row)
            QMessageBox.information(self, "成功", "資料已匯出")



    def import_from_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "匯入 CSV", "", "CSV Files (*.csv)")
        if path:
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    reader = csv.reader(f)
                    next(reader)
                    for row_data in reader:
                        row = self.table.rowCount()
                        self.table.insertRow(row)
                        for c, val in enumerate(row_data):
                            self.table.setItem(row, c, QTableWidgetItem(val))
                self.save_data()
                self.apply_conditional_formatting()
                QMessageBox.information(self, "成功", "資料已匯入")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"匯入失敗: {e}")



    def update_analysis(self):
        self.rank_table.setRowCount(0)
        combos = {}
        for r in range(self.table.rowCount()):
            try:
                if self.table.isRowHidden(r): continue
                # 組合鍵：武器+項鍊+卡片組合
                combo_key = f"{self.table.item(r, 0).text()} | {self.table.item(r, 1).text()}"
                hourly = float(self.table.item(r, 15).text())
                crit = float(self.table.item(r, 9).text().replace('%','')) if self.table.item(r, 9).text() else 0
                if combo_key not in combos:
                    combos[combo_key] = {"max_hr": 0, "crits": [], "count": 0}
                combos[combo_key]["max_hr"] = max(combos[combo_key]["max_hr"], hourly)
                combos[combo_key]["crits"].append(crit)
                combos[combo_key]["count"] += 1
            except: pass
        
        sorted_keys = sorted(combos.keys(), key=lambda k: combos[k]["max_hr"], reverse=True)
        for i, key in enumerate(sorted_keys):
            row = self.rank_table.rowCount()
            self.rank_table.insertRow(row)
            avg_crit = sum(combos[key]["crits"]) / len(combos[key]["crits"])
            self.rank_table.setItem(row, 0, QTableWidgetItem(str(i+1)))
            self.rank_table.setItem(row, 1, QTableWidgetItem(key))
            self.rank_table.setItem(row, 2, QTableWidgetItem(f"{avg_crit:.1f}%"))
            self.rank_table.setItem(row, 3, QTableWidgetItem(f"{combos[key]['max_hr']:.5f}"))
            self.rank_table.setItem(row, 4, QTableWidgetItem(str(combos[key]["count"])))
        self.calculate_countdown()



    def save_data(self):
        records = []
        for r in range(self.table.rowCount()):
            row_data = [self.table.item(r, c).text() for c in range(self.table.columnCount())]
            records.append(row_data)
        
        data = {
            "version": CURRENT_VERSION,
            "next_lvl_exp": self.next_lvl_exp.value(),
            "equip_data": self.equip_data,
            "records": records
        }
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)



    def load_data(self):
        if not os.path.exists(self.data_file): return
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.next_lvl_exp.setValue(data.get("next_lvl_exp", 0))
                self.equip_data.update(data.get("equip_data", {}))
                self.refresh_all_combos()
                self.update_config_table_from_data()
                
                records = data.get("records", [])
                self.table.setRowCount(0)
                for row_data in records:
                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    for c, val in enumerate(row_data):
                        self.table.setItem(row, c, QTableWidgetItem(str(val)))
            self.apply_conditional_formatting()
            self.update_analysis()
        except Exception as e:
            print(f"載入失敗: {e}")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameTracker()
    window.show()
    sys.exit(app.exec())