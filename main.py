#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generator Manager - مدير المولدات
A professional offline-first Android App for tracking generator runtime,
electricity production, and diesel inventory.
"""

import flet as ft
import sqlite3
from datetime import datetime, date
from typing import Optional, List, Dict, Tuple
import os


# ============================================================================
# Database Manager
# ============================================================================
class DatabaseManager:
    """Handles all database operations for the Generator Manager app."""
    
    def __init__(self, db_path: str = "gen_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Create and return a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database schema."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Generators table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        # Meters table (Dynamic Sources)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generator_id INTEGER NOT NULL,
                type_name TEXT NOT NULL,
                last_reading REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (generator_id) REFERENCES generators(id)
            )
        """)
        
        # Diesel inventory table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS diesel_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                quantity_in REAL NOT NULL,
                station_name TEXT,
                receipt_no TEXT
            )
        """)
        
        # Daily logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                meter_id INTEGER NOT NULL,
                prev_reading REAL NOT NULL,
                curr_reading REAL NOT NULL,
                production REAL NOT NULL,
                diesel_consumed REAL NOT NULL,
                efficiency REAL NOT NULL,
                FOREIGN KEY (meter_id) REFERENCES meters(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    # Generator operations
    def add_generator(self, name: str) -> bool:
        """Add a new generator."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO generators (name) VALUES (?)", (name,))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_all_generators(self) -> List[Dict]:
        """Get all generators."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM generators ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    # Meter operations
    def add_meter(self, generator_id: int, type_name: str, initial_reading: float) -> bool:
        """Add a new meter to a generator."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO meters (generator_id, type_name, last_reading) VALUES (?, ?, ?)",
                (generator_id, type_name, initial_reading)
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
    
    def get_meters_by_generator(self, generator_id: int) -> List[Dict]:
        """Get all meters for a specific generator."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM meters WHERE generator_id = ? ORDER BY type_name",
            (generator_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_meter_last_reading(self, meter_id: int) -> Optional[float]:
        """Get the last reading for a specific meter."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT last_reading FROM meters WHERE id = ?", (meter_id,))
        row = cursor.fetchone()
        conn.close()
        return row['last_reading'] if row else None
    
    def update_meter_last_reading(self, meter_id: int, new_reading: float):
        """Update the last reading for a meter."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE meters SET last_reading = ? WHERE id = ?",
            (new_reading, meter_id)
        )
        conn.commit()
        conn.close()
    
    # Diesel inventory operations
    def add_diesel_supply(self, date_str: str, quantity: float, station_name: str, receipt_no: str) -> bool:
        """Add diesel supply record."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO diesel_inventory (date, quantity_in, station_name, receipt_no) VALUES (?, ?, ?, ?)",
                (date_str, quantity, station_name, receipt_no)
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
    
    def get_total_diesel_supply(self) -> float:
        """Get total diesel supplied."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(quantity_in) as total FROM diesel_inventory")
        row = cursor.fetchone()
        conn.close()
        return row['total'] if row['total'] else 0.0
    
    def get_total_diesel_consumed(self) -> float:
        """Get total diesel consumed."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(diesel_consumed) as total FROM daily_logs")
        row = cursor.fetchone()
        conn.close()
        return row['total'] if row['total'] else 0.0
    
    # Daily log operations
    def add_daily_log(self, date_str: str, meter_id: int, prev_reading: float,
                     curr_reading: float, diesel_consumed: float) -> bool:
        """Add a daily log entry."""
        try:
            production = curr_reading - prev_reading
            efficiency = production / diesel_consumed if diesel_consumed > 0 else 0
            
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO daily_logs 
                   (date, meter_id, prev_reading, curr_reading, production, diesel_consumed, efficiency)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (date_str, meter_id, prev_reading, curr_reading, production, diesel_consumed, efficiency)
            )
            conn.commit()
            conn.close()
            
            # Update meter's last reading
            self.update_meter_last_reading(meter_id, curr_reading)
            return True
        except Exception:
            return False
    
    def get_recent_logs(self, limit: int = 30) -> List[Dict]:
        """Get recent daily logs with generator and meter info."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT dl.*, m.type_name, g.name as generator_name
               FROM daily_logs dl
               JOIN meters m ON dl.meter_id = m.id
               JOIN generators g ON m.generator_id = g.id
               ORDER BY dl.date DESC, dl.id DESC
               LIMIT ?""",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_today_average_efficiency(self) -> float:
        """Get average efficiency for today."""
        today = date.today().isoformat()
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT AVG(efficiency) as avg_eff FROM daily_logs WHERE date = ?",
            (today,)
        )
        row = cursor.fetchone()
        conn.close()
        return row['avg_eff'] if row['avg_eff'] else 0.0
    
    def export_database(self, destination_path: str) -> bool:
        """Export database to a destination path."""
        try:
            import shutil
            shutil.copy2(self.db_path, destination_path)
            return True
        except Exception:
            return False


# ============================================================================
# Main Application
# ============================================================================
class GeneratorManagerApp:
    """Main application class for Generator Manager."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.db = DatabaseManager()
        self.setup_page()
        self.build_ui()
    
    def setup_page(self):
        """Configure page settings."""
        self.page.title = "مدير المولدات - Generator Manager"
        self.page.rtl = True  # Right-to-Left layout
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(color_scheme_seed=ft.colors.BLUE)
        self.page.padding = 0
        self.page.scroll = ft.ScrollMode.AUTO
    
    def build_ui(self):
        """Build the main UI."""
        # Navigation rail
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.icons.DASHBOARD_OUTLINED,
                    selected_icon=ft.icons.DASHBOARD,
                    label="الرئيسية"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.EDIT_NOTE_OUTLINED,
                    selected_icon=ft.icons.EDIT_NOTE,
                    label="التسجيل اليومي"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.SETTINGS_OUTLINED,
                    selected_icon=ft.icons.SETTINGS,
                    label="التوريد والإعدادات"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.ASSESSMENT_OUTLINED,
                    selected_icon=ft.icons.ASSESSMENT,
                    label="التقارير"
                ),
            ],
            on_change=self.nav_changed,
        )
        
        # Content area
        self.content_area = ft.Container(
            content=self.build_dashboard_view(),
            expand=True,
            padding=20,
        )
        
        # Main layout
        self.page.add(
            ft.Row(
                [
                    self.nav_rail,
                    ft.VerticalDivider(width=1),
                    self.content_area,
                ],
                expand=True,
            )
        )
    
    def nav_changed(self, e):
        """Handle navigation changes."""
        index = e.control.selected_index
        
        if index == 0:
            self.content_area.content = self.build_dashboard_view()
        elif index == 1:
            self.content_area.content = self.build_daily_operations_view()
        elif index == 2:
            self.content_area.content = self.build_supply_setup_view()
        elif index == 3:
            self.content_area.content = self.build_reports_view()
        
        self.page.update()
    
    # ========================================================================
    # View A: Dashboard
    # ========================================================================
    def build_dashboard_view(self) -> ft.Column:
        """Build the dashboard view."""
        total_supply = self.db.get_total_diesel_supply()
        total_consumed = self.db.get_total_diesel_consumed()
        estimated_diesel = total_supply - total_consumed
        avg_efficiency = self.db.get_today_average_efficiency()
        
        return ft.Column(
            [
                ft.Text("لوحة التحكم", size=32, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                
                # Inventory Card
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.ListTile(
                                leading=ft.Icon(ft.icons.LOCAL_GAS_STATION, size=40),
                                title=ft.Text("الديزل المقدر في الخزان", size=20, weight=ft.FontWeight.BOLD),
                                subtitle=ft.Text(f"{estimated_diesel:.2f} لتر", size=24, color=ft.colors.BLUE),
                            ),
                            ft.Divider(),
                            ft.Row([
                                ft.Text(f"إجمالي التوريد: {total_supply:.2f} لتر", size=14),
                                ft.Text(f"إجمالي الاستهلاك: {total_consumed:.2f} لتر", size=14),
                            ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
                        ]),
                        padding=10,
                    ),
                    elevation=4,
                ),
                
                ft.SizedBox(height=20),
                
                # Status Card
                ft.Card(
                    content=ft.Container(
                        content=ft.ListTile(
                            leading=ft.Icon(ft.icons.SPEED, size=40),
                            title=ft.Text("متوسط الكفاءة اليوم", size=20, weight=ft.FontWeight.BOLD),
                            subtitle=ft.Text(
                                f"{avg_efficiency:.2f} كيلووات/لتر",
                                size=24,
                                color=ft.colors.GREEN if avg_efficiency > 3.2 else ft.colors.RED if avg_efficiency < 3.0 else ft.colors.ORANGE
                            ),
                        ),
                        padding=10,
                    ),
                    elevation=4,
                ),
                
                ft.SizedBox(height=20),
                
                # Quick Action Button
                ft.ElevatedButton(
                    "إضافة سجل يومي سريع",
                    icon=ft.icons.ADD_CIRCLE,
                    on_click=lambda _: self.quick_add_log(),
                    style=ft.ButtonStyle(
                        padding=20,
                        text_style=ft.TextStyle(size=18),
                    ),
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
    
    def quick_add_log(self):
        """Quick navigation to daily operations view."""
        self.nav_rail.selected_index = 1
        self.content_area.content = self.build_daily_operations_view()
        self.page.update()
    
    # ========================================================================
    # View B: Daily Operations
    # ========================================================================
    def build_daily_operations_view(self) -> ft.Column:
        """Build the daily operations view."""
        # Form fields
        self.generator_dropdown = ft.Dropdown(
            label="اختر المولد",
            hint_text="اختر المولد",
            on_change=self.on_generator_selected,
            width=300,
        )
        
        self.meter_dropdown = ft.Dropdown(
            label="اختر العداد/الشاشة",
            hint_text="اختر العداد",
            on_change=self.on_meter_selected,
            width=300,
            disabled=True,
        )
        
        self.prev_reading_field = ft.TextField(
            label="القراءة السابقة",
            read_only=True,
            width=300,
            value="0.0",
        )
        
        self.curr_reading_field = ft.TextField(
            label="القراءة الحالية",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=300,
        )
        
        self.diesel_consumed_field = ft.TextField(
            label="الديزل المستهلك (لتر)",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=300,
        )
        
        self.status_text = ft.Text("", color=ft.colors.RED)
        
        # Load generators
        self.load_generators()
        
        return ft.Column(
            [
                ft.Text("التسجيل اليومي", size=32, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                
                ft.Container(
                    content=ft.Column([
                        self.generator_dropdown,
                        self.meter_dropdown,
                        self.prev_reading_field,
                        self.curr_reading_field,
                        self.diesel_consumed_field,
                        
                        ft.SizedBox(height=20),
                        
                        ft.ElevatedButton(
                            "حفظ السجل",
                            icon=ft.icons.SAVE,
                            on_click=self.save_daily_log,
                            style=ft.ButtonStyle(
                                padding=20,
                                text_style=ft.TextStyle(size=18),
                            ),
                        ),
                        
                        self.status_text,
                    ]),
                    padding=20,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
    
    def load_generators(self):
        """Load generators into dropdown."""
        generators = self.db.get_all_generators()
        self.generator_dropdown.options = [
            ft.dropdown.Option(key=str(g['id']), text=g['name'])
            for g in generators
        ]
        self.page.update()
    
    def on_generator_selected(self, e):
        """Handle generator selection."""
        if not self.generator_dropdown.value:
            return
        
        generator_id = int(self.generator_dropdown.value)
        meters = self.db.get_meters_by_generator(generator_id)
        
        self.meter_dropdown.options = [
            ft.dropdown.Option(key=str(m['id']), text=m['type_name'])
            for m in meters
        ]
        self.meter_dropdown.disabled = False
        self.meter_dropdown.value = None
        self.prev_reading_field.value = "0.0"
        self.page.update()
    
    def on_meter_selected(self, e):
        """Handle meter selection - Smart Logic."""
        if not self.meter_dropdown.value:
            return
        
        meter_id = int(self.meter_dropdown.value)
        last_reading = self.db.get_meter_last_reading(meter_id)
        
        if last_reading is not None:
            self.prev_reading_field.value = f"{last_reading:.2f}"
        else:
            self.prev_reading_field.value = "0.0"
        
        self.page.update()
    
    def save_daily_log(self, e):
        """Save daily log with validation."""
        # Validation
        if not self.generator_dropdown.value or not self.meter_dropdown.value:
            self.status_text.value = "❌ يرجى اختيار المولد والعداد"
            self.status_text.color = ft.colors.RED
            self.page.update()
            return
        
        try:
            prev_reading = float(self.prev_reading_field.value)
            curr_reading = float(self.curr_reading_field.value)
            diesel_consumed = float(self.diesel_consumed_field.value)
        except ValueError:
            self.status_text.value = "❌ يرجى إدخال أرقام صحيحة"
            self.status_text.color = ft.colors.RED
            self.page.update()
            return
        
        # Validation: Current must be >= Previous
        if curr_reading < prev_reading:
            self.status_text.value = "❌ القراءة الحالية يجب أن تكون أكبر من أو تساوي القراءة السابقة"
            self.status_text.color = ft.colors.RED
            self.page.update()
            return
        
        # Save to database
        today = date.today().isoformat()
        meter_id = int(self.meter_dropdown.value)
        
        success = self.db.add_daily_log(
            today, meter_id, prev_reading, curr_reading, diesel_consumed
        )
        
        if success:
            self.status_text.value = "✅ تم حفظ السجل بنجاح"
            self.status_text.color = ft.colors.GREEN
            
            # Clear form
            self.curr_reading_field.value = ""
            self.diesel_consumed_field.value = ""
            
            # Reload meter to update last reading
            self.on_meter_selected(None)
        else:
            self.status_text.value = "❌ حدث خطأ أثناء الحفظ"
            self.status_text.color = ft.colors.RED
        
        self.page.update()
    
    # ========================================================================
    # View C: Supply & Setup
    # ========================================================================
    def build_supply_setup_view(self) -> ft.Column:
        """Build the supply and setup view."""
        # Tabs
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="توريد الديزل",
                    icon=ft.icons.LOCAL_SHIPPING,
                    content=self.build_diesel_supply_tab(),
                ),
                ft.Tab(
                    text="الإعدادات",
                    icon=ft.icons.SETTINGS,
                    content=self.build_setup_tab(),
                ),
            ],
            expand=True,
        )
        
        return ft.Column(
            [
                ft.Text("التوريد والإعدادات", size=32, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                tabs,
            ],
            expand=True,
        )
    
    def build_diesel_supply_tab(self) -> ft.Container:
        """Build diesel supply tab."""
        self.supply_date_field = ft.TextField(
            label="التاريخ",
            value=date.today().isoformat(),
            width=300,
        )
        
        self.supply_quantity_field = ft.TextField(
            label="الكمية (لتر)",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=300,
        )
        
        self.supply_station_field = ft.TextField(
            label="اسم المحطة",
            width=300,
        )
        
        self.supply_receipt_field = ft.TextField(
            label="رقم الإيصال",
            width=300,
        )
        
        self.supply_status_text = ft.Text("", color=ft.colors.RED)
        
        return ft.Container(
            content=ft.Column([
                ft.Text("إضافة توريد ديزل جديد", size=20, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                
                self.supply_date_field,
                self.supply_quantity_field,
                self.supply_station_field,
                self.supply_receipt_field,
                
                ft.SizedBox(height=20),
                
                ft.ElevatedButton(
                    "حفظ التوريد",
                    icon=ft.icons.SAVE,
                    on_click=self.save_diesel_supply,
                    style=ft.ButtonStyle(
                        padding=20,
                        text_style=ft.TextStyle(size=18),
                    ),
                ),
                
                self.supply_status_text,
            ]),
            padding=20,
        )
    
    def save_diesel_supply(self, e):
        """Save diesel supply record."""
        try:
            date_str = self.supply_date_field.value
            quantity = float(self.supply_quantity_field.value)
            station = self.supply_station_field.value
            receipt = self.supply_receipt_field.value
        except ValueError:
            self.supply_status_text.value = "❌ يرجى إدخال بيانات صحيحة"
            self.supply_status_text.color = ft.colors.RED
            self.page.update()
            return
        
        success = self.db.add_diesel_supply(date_str, quantity, station, receipt)
        
        if success:
            self.supply_status_text.value = "✅ تم حفظ التوريد بنجاح"
            self.supply_status_text.color = ft.colors.GREEN
            
            # Clear form
            self.supply_quantity_field.value = ""
            self.supply_station_field.value = ""
            self.supply_receipt_field.value = ""
        else:
            self.supply_status_text.value = "❌ حدث خطأ أثناء الحفظ"
            self.supply_status_text.color = ft.colors.RED
        
        self.page.update()
    
    def build_setup_tab(self) -> ft.Container:
        """Build setup tab."""
        # Generator setup
        self.new_generator_field = ft.TextField(
            label="اسم المولد الجديد",
            width=300,
        )
        
        self.generator_status_text = ft.Text("", color=ft.colors.RED)
        
        # Meter setup
        self.meter_generator_dropdown = ft.Dropdown(
            label="اختر المولد",
            hint_text="اختر المولد",
            width=300,
        )
        
        self.new_meter_type_field = ft.TextField(
            label="نوع العداد (مثل: شاشة دمج، محول تيار)",
            width=300,
        )
        
        self.new_meter_initial_reading_field = ft.TextField(
            label="القراءة الأولية",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=300,
        )
        
        self.meter_status_text = ft.Text("", color=ft.colors.RED)
        
        # Backup
        self.backup_status_text = ft.Text("", color=ft.colors.RED)
        
        # Load generators for meter dropdown
        self.load_meter_generators()
        
        return ft.Container(
            content=ft.Column([
                # Add Generator Section
                ft.Text("إضافة مولد جديد", size=20, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                
                self.new_generator_field,
                ft.ElevatedButton(
                    "إضافة مولد",
                    icon=ft.icons.ADD,
                    on_click=self.add_generator,
                ),
                self.generator_status_text,
                
                ft.SizedBox(height=30),
                
                # Add Meter Section
                ft.Text("إضافة عداد/شاشة جديدة", size=20, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                
                self.meter_generator_dropdown,
                self.new_meter_type_field,
                self.new_meter_initial_reading_field,
                ft.ElevatedButton(
                    "إضافة عداد",
                    icon=ft.icons.ADD,
                    on_click=self.add_meter,
                ),
                self.meter_status_text,
                
                ft.SizedBox(height=30),
                
                # Backup Section
                ft.Text("النسخ الاحتياطي", size=20, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                
                ft.ElevatedButton(
                    "تصدير قاعدة البيانات",
                    icon=ft.icons.BACKUP,
                    on_click=self.export_database,
                ),
                self.backup_status_text,
            ]),
            padding=20,
            scroll=ft.ScrollMode.AUTO,
        )
    
    def load_meter_generators(self):
        """Load generators for meter dropdown."""
        generators = self.db.get_all_generators()
        self.meter_generator_dropdown.options = [
            ft.dropdown.Option(key=str(g['id']), text=g['name'])
            for g in generators
        ]
        self.page.update()
    
    def add_generator(self, e):
        """Add a new generator."""
        name = self.new_generator_field.value.strip()
        
        if not name:
            self.generator_status_text.value = "❌ يرجى إدخال اسم المولد"
            self.generator_status_text.color = ft.colors.RED
            self.page.update()
            return
        
        success = self.db.add_generator(name)
        
        if success:
            self.generator_status_text.value = "✅ تم إضافة المولد بنجاح"
            self.generator_status_text.color = ft.colors.GREEN
            self.new_generator_field.value = ""
            
            # Reload dropdowns
            self.load_generators()
            self.load_meter_generators()
        else:
            self.generator_status_text.value = "❌ المولد موجود بالفعل أو حدث خطأ"
            self.generator_status_text.color = ft.colors.RED
        
        self.page.update()
    
    def add_meter(self, e):
        """Add a new meter."""
        if not self.meter_generator_dropdown.value:
            self.meter_status_text.value = "❌ يرجى اختيار المولد"
            self.meter_status_text.color = ft.colors.RED
            self.page.update()
            return
        
        type_name = self.new_meter_type_field.value.strip()
        
        if not type_name:
            self.meter_status_text.value = "❌ يرجى إدخال نوع العداد"
            self.meter_status_text.color = ft.colors.RED
            self.page.update()
            return
        
        try:
            initial_reading = float(self.new_meter_initial_reading_field.value)
        except ValueError:
            self.meter_status_text.value = "❌ يرجى إدخال قراءة أولية صحيحة"
            self.meter_status_text.color = ft.colors.RED
            self.page.update()
            return
        
        generator_id = int(self.meter_generator_dropdown.value)
        success = self.db.add_meter(generator_id, type_name, initial_reading)
        
        if success:
            self.meter_status_text.value = "✅ تم إضافة العداد بنجاح"
            self.meter_status_text.color = ft.colors.GREEN
            
            # Clear form
            self.new_meter_type_field.value = ""
            self.new_meter_initial_reading_field.value = ""
        else:
            self.meter_status_text.value = "❌ حدث خطأ أثناء الإضافة"
            self.meter_status_text.color = ft.colors.RED
        
        self.page.update()
    
    def export_database(self, e):
        """Export database to Downloads folder."""
        downloads_path = os.path.expanduser("~/Downloads")
        if not os.path.exists(downloads_path):
            downloads_path = os.path.expanduser("~")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = os.path.join(downloads_path, f"gen_data_backup_{timestamp}.db")
        
        success = self.db.export_database(destination)
        
        if success:
            self.backup_status_text.value = f"✅ تم تصدير قاعدة البيانات إلى:\n{destination}"
            self.backup_status_text.color = ft.colors.GREEN
        else:
            self.backup_status_text.value = "❌ حدث خطأ أثناء التصدير"
            self.backup_status_text.color = ft.colors.RED
        
        self.page.update()
    
    # ========================================================================
    # View D: Reports
    # ========================================================================
    def build_reports_view(self) -> ft.Column:
        """Build the reports view."""
        logs = self.db.get_recent_logs(30)
        
        # Build data table
        rows = []
        for log in logs:
            efficiency = log['efficiency']
            
            # Color coding based on efficiency
            if efficiency < 3.0:
                text_color = ft.colors.RED
            elif efficiency > 3.2:
                text_color = ft.colors.GREEN
            else:
                text_color = ft.colors.BLACK
            
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(log['date'], color=text_color)),
                        ft.DataCell(ft.Text(log['generator_name'], color=text_color)),
                        ft.DataCell(ft.Text(log['type_name'], color=text_color)),
                        ft.DataCell(ft.Text(f"{log['production']:.2f}", color=text_color)),
                        ft.DataCell(ft.Text(f"{log['diesel_consumed']:.2f}", color=text_color)),
                        ft.DataCell(ft.Text(f"{efficiency:.2f}", color=text_color)),
                    ]
                )
            )
        
        data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("التاريخ", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("المولد", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("العداد", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("الإنتاج (كيلووات)", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("الديزل (لتر)", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("الكفاءة", weight=ft.FontWeight.BOLD)),
            ],
            rows=rows,
        )
        
        return ft.Column(
            [
                ft.Text("التقارير", size=32, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                
                ft.Container(
                    content=ft.Column([
                        ft.Text("آخر 30 سجل", size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "الكفاءة: أخضر (> 3.2) | أحمر (< 3.0)",
                            size=14,
                            color=ft.colors.GREY_700,
                        ),
                        ft.Divider(),
                        
                        ft.Container(
                            content=data_table,
                            border=ft.border.all(1, ft.colors.GREY_400),
                            border_radius=5,
                            padding=10,
                        ),
                    ]),
                    padding=10,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )


# ============================================================================
# Application Entry Point
# ============================================================================
def main(page: ft.Page):
    """Application entry point."""
    GeneratorManagerApp(page)


if __name__ == "__main__":
    ft.app(target=main)
