import os
import sys
import json
import threading
import math
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import psutil
from PIL import Image, ImageDraw

import optimizer
import autostart

# Инициализируем настройки CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Путь для сохранения настроек и шрифтов
APPDATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'CanSpeed')
os.makedirs(APPDATA_DIR, exist_ok=True)
SETTINGS_FILE = os.path.join(APPDATA_DIR, 'settings.json')

FONT_URL = "https://unpkg.com/boxicons@2.1.4/fonts/boxicons.ttf"
FONT_PATH = os.path.join(APPDATA_DIR, "boxicons.ttf")

def download_font_if_needed():
    """
    Скачивает шрифт Boxicons с CDN в папку AppData, если он отсутствует.
    """
    if not os.path.exists(FONT_PATH):
        try:
            import urllib.request
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            req = urllib.request.Request(FONT_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                with open(FONT_PATH, 'wb') as out_file:
                    out_file.write(response.read())
        except Exception:
            pass

DEFAULT_SETTINGS = {
    'auto_clean_enabled': True,
    'ram_threshold': 80,
    'check_interval': 15,
    'minimize_to_tray': True,
    'notifications_enabled': True,
    'disabled_startup': {},  # Содержит данные отключенных элементов
    'game_boost_enabled': False,
    'clean_browser_cache_enabled': True,
    'clean_standby_enabled': True,
    'clean_recycle_clipboard_enabled': False
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Объединяем с дефолтными на случай отсутствия ключей
                return {**DEFAULT_SETTINGS, **data}
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def get_icon(name, color="#8b5cf6", size=(20, 20)):
    """
    Генерирует сглаженную векторную иконку.
    Если шрифт Boxicons доступен, рендерит профессиональную иконку.
    В противном случае рисует резервную фигуру (fallback).
    """
    scale = 4
    w_scale = size[0] * scale
    h_scale = size[1] * scale
    
    # Карта символов Boxicons
    char_map = {
        "dashboard": 0xeea3, # bx-tachometer
        "services": 0xea7b,  # bx-cog
        "startup": 0xeeca,   # bx-rocket
        "settings": 0xeed2,  # bx-sliders
        "game": 0xeab4,      # bxs-game
        "ram": 0xea8f,       # bx-chip
        "disk": 0xeab8,      # bx-hdd
        "brush": 0xea3d,     # bx-brush
        "bolt": 0xea5b,      # bx-bolt
        "trash": 0xeb15,     # bx-trash
        "copy": 0xea83,      # bx-copy
        "world": 0xec2c,     # bx-world
        "shield": 0xeec1,    # bx-shield
        "pulse": 0xee92      # bx-pulse
    }
    
    img = Image.new("RGBA", (w_scale, h_scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    rendered = False
    
    if os.path.exists(FONT_PATH) and name in char_map:
        try:
            from PIL import ImageFont
            font = ImageFont.truetype(FONT_PATH, int(w_scale * 0.95))
            char_str = chr(char_map[name])
            
            bbox = font.getbbox(char_str)
            char_w = bbox[2] - bbox[0]
            char_h = bbox[3] - bbox[1]
            
            x = (w_scale - char_w) / 2 - bbox[0]
            y = (h_scale - char_h) / 2 - bbox[1]
            
            draw.text((x, y), char_str, fill=color, font=font)
            rendered = True
        except Exception:
            pass
            
    if not rendered:
        # Резервное рисование
        if name == "dashboard":
            draw.arc([w_scale*0.1, h_scale*0.1, w_scale*0.9, h_scale*0.9], start=135, end=45, fill=color, width=int(2.2*scale))
            draw.ellipse([w_scale*0.43, h_scale*0.43, w_scale*0.57, h_scale*0.57], fill=color)
            draw.line([w_scale*0.5, h_scale*0.5, w_scale*0.75, h_scale*0.25], fill=color, width=int(2.5*scale))
        elif name == "services":
            draw.ellipse([w_scale*0.3, h_scale*0.3, w_scale*0.7, h_scale*0.7], outline=color, width=int(2.5*scale))
            for i in range(8):
                angle = i * (2 * math.pi / 8)
                cx = w_scale * 0.5 + w_scale * 0.3 * math.cos(angle)
                cy = h_scale * 0.5 + h_scale * 0.3 * math.sin(angle)
                draw.ellipse([cx - w_scale*0.08, cy - h_scale*0.08, cx + w_scale*0.08, cy + h_scale*0.08], fill=color)
            draw.ellipse([w_scale*0.44, h_scale*0.44, w_scale*0.56, h_scale*0.56], fill=(0, 0, 0, 0))
        elif name == "startup":
            draw.ellipse([w_scale*0.36, h_scale*0.15, w_scale*0.64, h_scale*0.75], fill=color)
            draw.polygon([(w_scale*0.36, h_scale*0.4), (w_scale*0.5, h_scale*0.05), (w_scale*0.64, h_scale*0.4)], fill=color)
            draw.polygon([(w_scale*0.36, h_scale*0.6), (w_scale*0.2, h_scale*0.8), (w_scale*0.36, h_scale*0.8)], fill=color)
            draw.polygon([(w_scale*0.64, h_scale*0.6), (w_scale*0.8, h_scale*0.8), (w_scale*0.64, h_scale*0.8)], fill=color)
            draw.polygon([(w_scale*0.44, h_scale*0.75), (w_scale*0.5, h_scale*0.95), (w_scale*0.56, h_scale*0.75)], fill="#ef4444")
        elif name == "settings":
            draw.line([w_scale*0.15, h_scale*0.3, w_scale*0.85, h_scale*0.3], fill=color, width=int(1.8*scale))
            draw.ellipse([w_scale*0.3, h_scale*0.18, w_scale*0.46, h_scale*0.42], fill=color)
            draw.line([w_scale*0.15, h_scale*0.7, w_scale*0.85, h_scale*0.7], fill=color, width=int(1.8*scale))
            draw.ellipse([w_scale*0.54, h_scale*0.58, w_scale*0.7, h_scale*0.82], fill=color)
        elif name == "game":
            draw.rounded_rectangle([w_scale*0.15, h_scale*0.25, w_scale*0.85, h_scale*0.75], radius=int(6*scale), fill=color)
            draw.ellipse([w_scale*0.15, h_scale*0.45, w_scale*0.35, h_scale*0.85], fill=color)
            draw.ellipse([w_scale*0.65, h_scale*0.45, w_scale*0.85, h_scale*0.85], fill=color)
            # Кнопки действия (4 точки)
            draw.ellipse([w_scale*0.68, h_scale*0.42, w_scale*0.74, h_scale*0.48], fill="#13131b")
            draw.ellipse([w_scale*0.76, h_scale*0.42, w_scale*0.82, h_scale*0.48], fill="#13131b")
            draw.ellipse([w_scale*0.72, h_scale*0.34, w_scale*0.78, h_scale*0.40], fill="#13131b")
            draw.ellipse([w_scale*0.72, h_scale*0.50, w_scale*0.78, h_scale*0.56], fill="#13131b")
            # D-pad (крестовина)
            draw.rectangle([w_scale*0.26, h_scale*0.42, w_scale*0.38, h_scale*0.48], fill="#13131b")
            draw.rectangle([w_scale*0.30, h_scale*0.38, w_scale*0.34, h_scale*0.52], fill="#13131b")
        else:
            draw.ellipse([w_scale*0.1, h_scale*0.1, w_scale*0.9, h_scale*0.9], fill=color)
            
    img = img.resize(size, Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=size)


class CircularProgress(tk.Canvas):
    """
    Красивый круговой индикатор использования ОЗУ с плавной анимацией.
    """
    def __init__(self, parent, size=220, thickness=16, bg_color="#1e1e24", circle_color="#2d2d3d", **kwargs):
        # Находим цвет фона родительского виджета для слияния
        bg_rgb = parent.cget("fg_color")
        if isinstance(bg_rgb, list) or isinstance(bg_rgb, tuple):
            bg_hex = bg_rgb[1] if len(bg_rgb) > 1 else bg_rgb[0]
        else:
            bg_hex = bg_rgb if bg_rgb else bg_color
            
        super().__init__(parent, width=size, height=size, bg=bg_hex, highlightthickness=0, **kwargs)
        self.size = size
        self.thickness = thickness
        self.circle_color = circle_color
        self.value = 0
        self.target_value = 0
        self.is_animating = False
        self.draw_widget()
        
    def draw_widget(self):
        self.delete("all")
        padding = self.thickness / 2 + 5
        coord = (padding, padding, self.size - padding, self.size - padding)
        
        # Фоновый круг
        self.create_oval(coord, outline=self.circle_color, width=self.thickness)
        
        # Выбор цвета на основе процента загрузки
        if self.value < 65:
            color = "#10b981"  # Зеленый (Нормально)
        elif self.value < 85:
            color = "#f59e0b"  # Оранжевый (Внимание)
        else:
            color = "#ef4444"  # Красный (Перегрузка)
            
        # Дуга прогресса
        extent = -(self.value / 100.0) * 360
        self.create_arc(coord, start=90, extent=extent, outline=color, width=self.thickness, style="arc", tags="arc")
        
        # Текст внутри круга
        self.create_text(self.size/2, self.size/2 - 12, text=f"{self.value}%", fill="#ffffff", font=("Segoe UI", 36, "bold"))
        self.create_text(self.size/2, self.size/2 + 25, text="Занято ОЗУ", fill="#9ca3af", font=("Segoe UI", 10))
        
    def set_value(self, value):
        self.target_value = max(0, min(100, int(value)))
        if not self.is_animating:
            self.animate_progress()
            
    def animate_progress(self):
        diff = self.target_value - self.value
        if diff == 0:
            self.is_animating = False
            return
            
        self.is_animating = True
        step = 1 if diff > 0 else -1
        
        # Ускоряем шаг при больших изменениях
        if abs(diff) > 10:
            step = int(diff / 5)
            if step == 0:
                step = 1 if diff > 0 else -1
                
        self.value += step
        if (step > 0 and self.value > self.target_value) or (step < 0 and self.value < self.target_value):
            self.value = self.target_value
            
        self.draw_widget()
        
        if self.value != self.target_value:
            self.after(15, self.animate_progress)
        else:
            self.is_animating = False


class DashboardFrame(ctk.CTkFrame):
    """
    Панель состояния (Дашборд).
    """
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        # Заголовок
        self.title_label = ctk.CTkLabel(self, text="Панель состояния системы", font=("Segoe UI", 24, "bold"), text_color="#f3f4f6")
        self.title_label.pack(anchor="w", padx=25, pady=(20, 10))
        
        # --- Панель дополнительных функций сверху ---
        self.addons_frame = ctk.CTkFrame(self, fg_color="#13131b", corner_radius=12, border_width=1, border_color="#2b2b3a")
        self.addons_frame.pack(fill="x", padx=25, pady=(0, 10))
        
        self.addons_title = ctk.CTkLabel(self.addons_frame, text="Доп. функции:", font=("Segoe UI", 12, "bold"), text_color="#8b5cf6")
        self.addons_title.pack(side="left", padx=15, pady=8)
        
        self.settings = load_settings()
        
        # 1. Игровой режим
        self.var_game = ctk.BooleanVar(value=self.settings.get('game_boost_enabled', False))
        self.switch_game = ctk.CTkSwitch(
            self.addons_frame, 
            text="Игровой режим", 
            variable=self.var_game, 
            command=self.save_addons_settings,
            font=("Segoe UI", 11, "bold"),
            progress_color="#8b5cf6"
        )
        self.switch_game.pack(side="left", padx=12, pady=8)
        
        # 2. Очистка Standby List
        self.var_standby = ctk.BooleanVar(value=self.settings.get('clean_standby_enabled', True))
        self.switch_standby = ctk.CTkSwitch(
            self.addons_frame, 
            text="Standby ОЗУ", 
            variable=self.var_standby, 
            command=self.save_addons_settings,
            font=("Segoe UI", 11),
            progress_color="#8b5cf6"
        )
        self.switch_standby.pack(side="left", padx=12, pady=8)
        
        # 3. Очистка кэша браузеров
        self.var_browser = ctk.BooleanVar(value=self.settings.get('clean_browser_cache_enabled', True))
        self.switch_browser = ctk.CTkSwitch(
            self.addons_frame, 
            text="Кэш браузеров", 
            variable=self.var_browser, 
            command=self.save_addons_settings,
            font=("Segoe UI", 11),
            progress_color="#8b5cf6"
        )
        self.switch_browser.pack(side="left", padx=12, pady=8)
        
        # 4. Очистка корзины и буфера
        self.var_recycle = ctk.BooleanVar(value=self.settings.get('clean_recycle_clipboard_enabled', False))
        self.switch_recycle = ctk.CTkSwitch(
            self.addons_frame, 
            text="Корзина и буфер", 
            variable=self.var_recycle, 
            command=self.save_addons_settings,
            font=("Segoe UI", 11),
            progress_color="#8b5cf6"
        )
        self.switch_recycle.pack(side="left", padx=12, pady=8)
        
        # --- Основной контейнер с сеткой ---
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True, padx=25, pady=5)
        
        # Левая карточка (Индикатор RAM)
        self.left_card = ctk.CTkFrame(self.content_container, fg_color="#181822", corner_radius=16, border_width=1, border_color="#2b2b3a")
        self.left_card.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)
        
        self.circular_progress = CircularProgress(self.left_card, size=220, thickness=16)
        self.circular_progress.pack(pady=(20, 10))
        
        # Статистика памяти под индикатором
        self.stats_frame = ctk.CTkFrame(self.left_card, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=20, pady=5)
        
        self.label_used = ctk.CTkLabel(self.stats_frame, text="Использовано: -- ГБ", font=("Segoe UI", 13), text_color="#f3f4f6")
        self.label_used.pack(pady=2)
        
        self.label_free = ctk.CTkLabel(self.stats_frame, text="Свободно: -- ГБ", font=("Segoe UI", 13), text_color="#9ca3af")
        self.label_free.pack(pady=2)
        
        self.label_total = ctk.CTkLabel(self.stats_frame, text="Всего ОЗУ: -- ГБ", font=("Segoe UI", 12), text_color="#6b7280")
        self.label_total.pack(pady=2)
        
        # Правая карточка (Действия по очистке)
        self.right_card = ctk.CTkFrame(self.content_container, fg_color="#181822", corner_radius=16, border_width=1, border_color="#2b2b3a")
        self.right_card.pack(side="right", fill="both", expand=True, padx=(10, 0), pady=10)
        
        # Секция ОЗУ
        self.ram_sec_title = ctk.CTkLabel(self.right_card, text="Оптимизация памяти", font=("Segoe UI", 16, "bold"), text_color="#8b5cf6")
        self.ram_sec_title.pack(anchor="w", padx=20, pady=(20, 5))
        
        self.ram_desc = ctk.CTkLabel(self.right_card, text="Освобождает ОЗУ путем очистки неиспользуемых рабочих областей всех запущенных программ.", justify="left", wraplength=280, font=("Segoe UI", 12), text_color="#9ca3af")
        self.ram_desc.pack(anchor="w", padx=20, pady=5)
        
        self.btn_optimize_ram = ctk.CTkButton(
            self.right_card, 
            text="Оптимизировать ОЗУ", 
            fg_color="#8b5cf6", 
            hover_color="#7c3aed",
            font=("Segoe UI", 13, "bold"),
            height=40,
            command=self.run_ram_optimization
        )
        self.btn_optimize_ram.pack(fill="x", padx=20, pady=10)
        
        # Разделитель
        self.separator = ctk.CTkFrame(self.right_card, height=1, fg_color="#2b2b3a")
        self.separator.pack(fill="x", padx=20, pady=15)
        
        # Секция Очистки Диска
        self.disk_sec_title = ctk.CTkLabel(self.right_card, text="Очистка временных файлов", font=("Segoe UI", 16, "bold"), text_color="#06b6d4")
        self.disk_sec_title.pack(anchor="w", padx=20, pady=5)
        
        self.disk_desc = ctk.CTkLabel(self.right_card, text="Удаляет системный кэш, файлы обновлений и временные файлы из Temp/Prefetch.", justify="left", wraplength=280, font=("Segoe UI", 12), text_color="#9ca3af")
        self.disk_desc.pack(anchor="w", padx=20, pady=5)
        
        self.label_junk_size = ctk.CTkLabel(self.right_card, text="Временных файлов обнаружено: расчет...", font=("Segoe UI", 13, "bold"), text_color="#f3f4f6")
        self.label_junk_size.pack(anchor="w", padx=20, pady=5)
        
        self.btn_clean_disk = ctk.CTkButton(
            self.right_card, 
            text="Очистить диск", 
            fg_color="#06b6d4", 
            hover_color="#0891b2",
            font=("Segoe UI", 13, "bold"),
            height=40,
            command=self.run_disk_cleaning
        )
        self.btn_clean_disk.pack(fill="x", padx=20, pady=10)
        
        # Запуск обновления статистики
        self.update_stats()
        self.calculate_junk_size()
        
    def save_addons_settings(self):
        settings = load_settings()
        settings['game_boost_enabled'] = self.var_game.get()
        settings['clean_standby_enabled'] = self.var_standby.get()
        settings['clean_browser_cache_enabled'] = self.var_browser.get()
        settings['clean_recycle_clipboard_enabled'] = self.var_recycle.get()
        save_settings(settings)
        # Оповещаем контроллер о смене настроек
        self.controller.on_settings_updated()
        # Принудительно пересчитываем размер мусора, если сменилась опция кэша браузеров
        self.calculate_junk_size()
        
    def update_stats(self):
        try:
            mem = psutil.virtual_memory()
            self.circular_progress.set_value(mem.percent)
            
            total_gb = mem.total / (1024**3)
            used_gb = mem.used / (1024**3)
            free_gb = mem.available / (1024**3)
            
            self.label_used.configure(text=f"Использовано: {used_gb:.2f} ГБ")
            self.label_free.configure(text=f"Свободно: {free_gb:.2f} ГБ")
            self.label_total.configure(text=f"Всего ОЗУ: {total_gb:.2f} ГБ")
        except Exception:
            pass
        self.after(2000, self.update_stats)
        
    def calculate_junk_size(self):
        def task():
            settings = load_settings()
            total_mb = 0
            for name, path in optimizer.get_junk_paths():
                total_mb += optimizer.get_folder_size(path)
            
            if settings.get('clean_browser_cache_enabled', True):
                for name, path in optimizer.get_browser_cache_paths():
                    total_mb += optimizer.get_folder_size(path)
                    
            # Возвращаем в главный поток
            self.after(0, lambda: self.label_junk_size.configure(text=f"Временных файлов обнаружено: {total_mb:.1f} МБ"))
        
        threading.Thread(target=task, daemon=True).start()
        
    def run_ram_optimization(self):
        self.btn_optimize_ram.configure(state="disabled", text="Оптимизация...")
        
        def task():
            settings = load_settings()
            # 1. Очистка рабочих областей процессов
            cleaned_count, before_mb, after_mb, freed_mb = optimizer.optimize_ram()
            
            # 2. Очистка системного Standby List, если включена
            standby_freed = False
            if settings.get('clean_standby_enabled', True):
                standby_freed = optimizer.clean_system_cache_standby()
                
            def done():
                self.btn_optimize_ram.configure(state="normal", text="Оптимизировать ОЗУ")
                msg = f"Успешно оптимизировано процессов: {cleaned_count}\nОсвобождено памяти: {freed_mb:.1f} МБ"
                if settings.get('clean_standby_enabled', True):
                    if standby_freed:
                        msg += "\nСистемный Standby кэш успешно очищен!"
                    else:
                        msg += "\nНе удалось очистить Standby кэш (требуется запуск от имени Администратора)."
                messagebox.showinfo("Оптимизация ОЗУ", msg)
                self.update_stats()
                
            self.after(0, done)
            
        threading.Thread(target=task, daemon=True).start()
        
    def run_disk_cleaning(self):
        self.btn_clean_disk.configure(state="disabled", text="Очистка...")
        
        def task():
            settings = load_settings()
            # 1. Очистка Temp/Prefetch
            freed_mb = optimizer.clean_junk()
            
            # 2. Очистка кэша браузеров
            browser_freed_mb = 0
            if settings.get('clean_browser_cache_enabled', True):
                browser_freed_mb = optimizer.clean_browser_cache()
                
            # 3. Очистка корзины и буфера
            if settings.get('clean_recycle_clipboard_enabled', False):
                optimizer.clean_recycle_bin()
                optimizer.clean_clipboard()
                
            total_freed = freed_mb + browser_freed_mb
            
            def done():
                self.btn_clean_disk.configure(state="normal", text="Очистить диск")
                msg = f"Очистка завершена!\nУдалено неиспользуемых файлов: {freed_mb:.1f} МБ"
                if settings.get('clean_browser_cache_enabled', True):
                    msg += f"\nОчищено кэша браузеров: {browser_freed_mb:.1f} МБ"
                if settings.get('clean_recycle_clipboard_enabled', False):
                    msg += "\nКорзина и буфер обмена успешно очищены!"
                messagebox.showinfo("Очистка временных файлов", msg)
                self.calculate_junk_size()
                
            self.after(0, done)
            
        threading.Thread(target=task, daemon=True).start()


class ServicesFrame(ctk.CTkFrame):
    """
    Панель оптимизации служб Windows.
    """
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        # Заголовок
        self.title_label = ctk.CTkLabel(self, text="Оптимизация служб Windows", font=("Segoe UI", 24, "bold"), text_color="#f3f4f6")
        self.title_label.pack(anchor="w", padx=25, pady=(20, 10))
        
        self.desc_label = ctk.CTkLabel(
            self, 
            text="Отключение ненужных фоновых служб позволяет освободить до 500 МБ оперативной памяти и снизить нагрузку на процессор.", 
            justify="left", 
            font=("Segoe UI", 12), 
            text_color="#9ca3af"
        )
        self.desc_label.pack(anchor="w", padx=25, pady=(0, 15))
        
        # Скроллируемая область для списка служб
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#181822", corner_radius=16, border_width=1, border_color="#2b2b3a")
        self.scroll_frame.pack(fill="both", expand=True, padx=25, pady=(0, 20))
        
        self.service_widgets = []
        self.load_services()
        
    def load_services(self):
        # Очистим старые виджеты, если есть
        for w in self.service_widgets:
            w.destroy()
        self.service_widgets.clear()
        
        # Загружаем данные служб в фоновом потоке, чтобы GUI не зависал
        def task():
            services_data = []
            for s_name, desc in optimizer.OPTIMIZABLE_SERVICES.items():
                is_running, startup_type = optimizer.get_service_status(s_name)
                services_data.append((s_name, desc, is_running, startup_type))
            
            # Обновляем GUI в главном потоке
            self.after(0, lambda: self.render_services(services_data))
            
        threading.Thread(target=task, daemon=True).start()
        
    def render_services(self, services_data):
        for index, (s_name, desc, is_running, startup_type) in enumerate(services_data):
            # Контейнер для службы
            service_row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            service_row.pack(fill="x", padx=10, pady=8)
            self.service_widgets.append(service_row)
            
            # Текстовый блок (Имя службы и Описание)
            info_frame = ctk.CTkFrame(service_row, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True)
            
            name_lbl = ctk.CTkLabel(info_frame, text=s_name, font=("Segoe UI", 14, "bold"), text_color="#f3f4f6")
            name_lbl.pack(anchor="w")
            
            desc_lbl = ctk.CTkLabel(info_frame, text=desc, font=("Segoe UI", 11), text_color="#9ca3af", justify="left", wraplength=450)
            desc_lbl.pack(anchor="w")
            
            # Блок управления
            control_frame = ctk.CTkFrame(service_row, fg_color="transparent")
            control_frame.pack(side="right", padx=10)
            
            # Индикатор состояния
            status_text = "Работает" if is_running else "Остановлена"
            status_color = "#10b981" if is_running else "#6b7280"
            status_lbl = ctk.CTkLabel(control_frame, text=status_text, text_color=status_color, font=("Segoe UI", 12, "bold"))
            status_lbl.pack(side="left", padx=15)
            
            # Выпадающий список состояний автозапуска
            current_var = ctk.StringVar(value=self.translate_startup_type(startup_type))
            combobox = ctk.CTkComboBox(
                control_frame, 
                values=["Автозапуск", "Вручную", "Отключена"],
                variable=current_var,
                width=120,
                command=lambda val, name=s_name, var=current_var, lbl=status_lbl: self.change_service_state(name, val, var, lbl)
            )
            combobox.pack(side="left")
            
            # Разделительная линия
            if index < len(services_data) - 1:
                sep = ctk.CTkFrame(self.scroll_frame, height=1, fg_color="#2d2d3d")
                sep.pack(fill="x", padx=10, pady=2)
                self.service_widgets.append(sep)
                
    def translate_startup_type(self, startup_type):
        if startup_type == 'Automatic':
            return "Автозапуск"
        elif startup_type == 'Manual':
            return "Вручную"
        elif startup_type == 'Disabled':
            return "Отключена"
        return "Вручную"
        
    def change_service_state(self, service_name, chosen_value, var_obj, status_lbl):
        state_map = {
            "Автозапуск": "enable_auto",
            "Вручную": "enable_manual",
            "Отключена": "disable"
        }
        
        target_state = state_map[chosen_value]
        
        def task():
            success = optimizer.set_service_state(service_name, target_state)
            
            def done():
                if success:
                    # Обновляем статус
                    is_running, startup_type = optimizer.get_service_status(service_name)
                    status_text = "Работает" if is_running else "Остановлена"
                    status_color = "#10b981" if is_running else "#6b7280"
                    status_lbl.configure(text=status_text, text_color=status_color)
                    var_obj.set(self.translate_startup_type(startup_type))
                    messagebox.showinfo("Службы Windows", f"Настройки службы {service_name} успешно применены!")
                else:
                    messagebox.showerror("Ошибка", f"Не удалось изменить состояние службы {service_name}.\nТребуются права Администратора.")
                    # Сбрасываем значение к исходному
                    _, startup_type = optimizer.get_service_status(service_name)
                    var_obj.set(self.translate_startup_type(startup_type))
                    
            self.after(0, done)
            
        threading.Thread(target=task, daemon=True).start()


class StartupFrame(ctk.CTkFrame):
    """
    Панель управления автозагрузкой приложений.
    """
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        # Заголовок
        self.title_label = ctk.CTkLabel(self, text="Менеджер автозагрузки", font=("Segoe UI", 24, "bold"), text_color="#f3f4f6")
        self.title_label.pack(anchor="w", padx=25, pady=(20, 10))
        
        self.desc_label = ctk.CTkLabel(
            self, 
            text="Отключите тяжелые сторонние программы в автозапуске, чтобы ускорить время загрузки ноутбука и освободить ОЗУ.", 
            justify="left", 
            font=("Segoe UI", 12), 
            text_color="#9ca3af"
        )
        self.desc_label.pack(anchor="w", padx=25, pady=(0, 15))
        
        # Скролл
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#181822", corner_radius=16, border_width=1, border_color="#2b2b3a")
        self.scroll_frame.pack(fill="both", expand=True, padx=25, pady=(0, 20))
        
        self.item_widgets = []
        self.load_startup_items()
        
    def load_startup_items(self):
        for w in self.item_widgets:
            w.destroy()
        self.item_widgets.clear()
        
        def task():
            import winreg
            items = []
            
            # Чтение реестра текущего пользователя
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
                info = winreg.QueryInfoKey(key)
                for i in range(info[0]):
                    name, val, val_type = winreg.EnumValue(key, i)
                    items.append({
                        'name': name,
                        'path': val,
                        'source': 'Реестр (Пользователь)',
                        'hive': 'HKCU',
                        'key_path': r"Software\Microsoft\Windows\CurrentVersion\Run",
                        'status': True
                    })
                winreg.CloseKey(key)
            except Exception:
                pass
                
            # Чтение реестра системы
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
                info = winreg.QueryInfoKey(key)
                for i in range(info[0]):
                    name, val, val_type = winreg.EnumValue(key, i)
                    items.append({
                        'name': name,
                        'path': val,
                        'source': 'Реестр (Система)',
                        'hive': 'HKLM',
                        'key_path': r"Software\Microsoft\Windows\CurrentVersion\Run",
                        'status': True
                    })
                winreg.CloseKey(key)
            except Exception:
                pass
                
            # Чтение отключенных элементов из настроек CanSpeed
            settings = load_settings()
            disabled_items = settings.get('disabled_startup', {})
            for name, data in disabled_items.items():
                items.append({
                    'name': name,
                    'path': data.get('path', ''),
                    'source': data.get('source', 'Отключено CanSpeed'),
                    'hive': data.get('hive', ''),
                    'key_path': data.get('key_path', ''),
                    'status': False
                })
                
            # Сортируем
            items.sort(key=lambda x: x['name'].lower())
            
            self.after(0, lambda: self.render_startup_items(items))
            
        threading.Thread(target=task, daemon=True).start()
        
    def render_startup_items(self, items):
        if not items:
            empty_lbl = ctk.CTkLabel(self.scroll_frame, text="Элементы автозагрузки не найдены", font=("Segoe UI", 14), text_color="#6b7280")
            empty_lbl.pack(pady=40)
            self.item_widgets.append(empty_lbl)
            return
            
        for index, item in enumerate(items):
            item_row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            item_row.pack(fill="x", padx=10, pady=8)
            self.item_widgets.append(item_row)
            
            # Информация
            info_frame = ctk.CTkFrame(item_row, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True)
            
            name_lbl = ctk.CTkLabel(info_frame, text=item['name'], font=("Segoe UI", 14, "bold"), text_color="#f3f4f6")
            name_lbl.pack(anchor="w")
            
            src_lbl = ctk.CTkLabel(info_frame, text=f"{item['source']} | Путь: {item['path']}", font=("Segoe UI", 11), text_color="#9ca3af", justify="left")
            src_lbl.pack(anchor="w")
            
            # Переключатель состояния
            switch_var = ctk.BooleanVar(value=item['status'])
            switch = ctk.CTkSwitch(
                item_row, 
                text="Вкл" if item['status'] else "Выкл",
                variable=switch_var,
                command=lambda it=item, sv=switch_var, sw=None: self.toggle_startup_item(it, sv)
            )
            # Добавим ссылку на переключатель, чтобы менять текст
            switch.configure(command=lambda it=item, sv=switch_var, sw=switch: self.toggle_startup_item(it, sv, sw))
            switch.pack(side="right", padx=10)
            
            if index < len(items) - 1:
                sep = ctk.CTkFrame(self.scroll_frame, height=1, fg_color="#2d2d3d")
                sep.pack(fill="x", padx=10, pady=2)
                self.item_widgets.append(sep)
                
    def toggle_startup_item(self, item, switch_var, switch_widget):
        new_status = switch_var.get()
        switch_widget.configure(text="Вкл" if new_status else "Выкл")
        
        def task():
            import winreg
            settings = load_settings()
            disabled_items = settings.get('disabled_startup', {})
            
            success = False
            
            if not new_status:
                # Отключаем: удаляем из реестра, сохраняем в settings.json
                hive_const = winreg.HKEY_CURRENT_USER if item['hive'] == 'HKCU' else winreg.HKEY_LOCAL_MACHINE
                try:
                    key = winreg.OpenKey(hive_const, item['key_path'], 0, winreg.KEY_WRITE)
                    winreg.DeleteValue(key, item['name'])
                    winreg.CloseKey(key)
                    
                    # Сохраняем в настройки
                    disabled_items[item['name']] = {
                        'path': item['path'],
                        'source': item['source'],
                        'hive': item['hive'],
                        'key_path': item['key_path']
                    }
                    settings['disabled_startup'] = disabled_items
                    save_settings(settings)
                    success = True
                except Exception as e:
                    pass
            else:
                # Включаем обратно: записываем в реестр, удаляем из settings.json
                hive_const = winreg.HKEY_CURRENT_USER if item['hive'] == 'HKCU' else winreg.HKEY_LOCAL_MACHINE
                try:
                    key = winreg.OpenKey(hive_const, item['key_path'], 0, winreg.KEY_WRITE)
                    winreg.SetValueEx(key, item['name'], 0, winreg.REG_SZ, item['path'])
                    winreg.CloseKey(key)
                    
                    # Удаляем из настроек
                    if item['name'] in disabled_items:
                        del disabled_items[item['name']]
                    settings['disabled_startup'] = disabled_items
                    save_settings(settings)
                    success = True
                except Exception:
                    pass
                    
            def done():
                if success:
                    # Перезагружаем список
                    self.load_startup_items()
                else:
                    messagebox.showerror("Ошибка", "Не удалось изменить настройки автозагрузки.\nТребуются права Администратора.")
                    switch_var.set(not new_status)
                    switch_widget.configure(text="Вкл" if not new_status else "Выкл")
                    
            self.after(0, done)
            
        threading.Thread(target=task, daemon=True).start()


class SettingsFrame(ctk.CTkFrame):
    """
    Панель настроек приложения.
    """
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        # Заголовок
        self.title_label = ctk.CTkLabel(self, text="Настройки CanSpeed", font=("Segoe UI", 24, "bold"), text_color="#f3f4f6")
        self.title_label.pack(anchor="w", padx=25, pady=(20, 10))
        
        # Главный контейнер
        self.container = ctk.CTkFrame(self, fg_color="#181822", corner_radius=16, border_width=1, border_color="#2b2b3a")
        self.container.pack(fill="both", expand=True, padx=25, pady=(0, 20))
        
        # Подгружаем настройки
        self.settings = load_settings()
        
        # 1. Автозапуск приложения с Windows (через Планировщик)
        self.row_autostart = ctk.CTkFrame(self.container, fg_color="transparent")
        self.row_autostart.pack(fill="x", padx=20, pady=15)
        
        self.lbl_autostart = ctk.CTkLabel(
            self.row_autostart, 
            text="Запуск при старте Windows (без UAC)", 
            font=("Segoe UI", 14, "bold"), 
            text_color="#f3f4f6"
        )
        self.lbl_autostart.pack(side="left")
        
        self.var_autostart = ctk.BooleanVar(value=autostart.is_autostart_enabled())
        self.switch_autostart = ctk.CTkSwitch(
            self.row_autostart, 
            text="", 
            variable=self.var_autostart, 
            command=self.toggle_autostart
        )
        self.switch_autostart.pack(side="right")
        
        # Описание под строкой
        self.lbl_autostart_desc = ctk.CTkLabel(
            self.container, 
            text="Создает задачу в Планировщике задач Windows, которая запускает оптимизатор самым первым при входе пользователя, обеспечивая максимальные привилегии Администратора.", 
            font=("Segoe UI", 11), 
            text_color="#9ca3af", 
            justify="left", 
            wraplength=600
        )
        self.lbl_autostart_desc.pack(anchor="w", padx=20, pady=(0, 10))
        
        self.sep1 = ctk.CTkFrame(self.container, height=1, fg_color="#2d2d3d")
        self.sep1.pack(fill="x", padx=20, pady=5)
        
        # 2. Автоматическая очистка ОЗУ по порогу
        self.row_autoclean = ctk.CTkFrame(self.container, fg_color="transparent")
        self.row_autoclean.pack(fill="x", padx=20, pady=15)
        
        self.lbl_autoclean = ctk.CTkLabel(
            self.row_autoclean, 
            text="Умная фоновая очистка ОЗУ", 
            font=("Segoe UI", 14, "bold"), 
            text_color="#f3f4f6"
        )
        self.lbl_autoclean.pack(side="left")
        
        self.var_autoclean = ctk.BooleanVar(value=self.settings['auto_clean_enabled'])
        self.switch_autoclean = ctk.CTkSwitch(
            self.row_autoclean, 
            text="", 
            variable=self.var_autoclean, 
            command=self.save_config
        )
        self.switch_autoclean.pack(side="right")
        
        # Слайдер порога RAM
        self.row_threshold = ctk.CTkFrame(self.container, fg_color="transparent")
        self.row_threshold.pack(fill="x", padx=20, pady=5)
        
        self.lbl_threshold = ctk.CTkLabel(
            self.row_threshold, 
            text=f"Очищать при заполнении: {self.settings['ram_threshold']}%", 
            font=("Segoe UI", 12), 
            text_color="#9ca3af"
        )
        self.lbl_threshold.pack(side="left")
        
        self.slider_threshold = ctk.CTkSlider(
            self.row_threshold, 
            from_=50, 
            to=95, 
            number_of_steps=9,
            width=200,
            command=self.on_threshold_change
        )
        self.slider_threshold.set(self.settings['ram_threshold'])
        self.slider_threshold.pack(side="right")
        
        # Слайдер интервала проверки
        self.row_interval = ctk.CTkFrame(self.container, fg_color="transparent")
        self.row_interval.pack(fill="x", padx=20, pady=10)
        
        self.lbl_interval = ctk.CTkLabel(
            self.row_interval, 
            text=f"Интервал проверки: {self.settings['check_interval']} мин", 
            font=("Segoe UI", 12), 
            text_color="#9ca3af"
        )
        self.lbl_interval.pack(side="left")
        
        self.slider_interval = ctk.CTkSlider(
            self.row_interval, 
            from_=1, 
            to=60, 
            number_of_steps=12,
            width=200,
            command=self.on_interval_change
        )
        self.slider_interval.set(self.settings['check_interval'])
        self.slider_interval.pack(side="right")
        
        self.sep2 = ctk.CTkFrame(self.container, height=1, fg_color="#2d2d3d")
        self.sep2.pack(fill="x", padx=20, pady=5)
        
        # 3. Другие настройки (Трей, Уведомления)
        self.row_tray = ctk.CTkFrame(self.container, fg_color="transparent")
        self.row_tray.pack(fill="x", padx=20, pady=10)
        
        self.lbl_tray = ctk.CTkLabel(self.row_tray, text="Сворачивать в системный трей при закрытии", font=("Segoe UI", 13), text_color="#f3f4f6")
        self.lbl_tray.pack(side="left")
        
        self.var_tray = ctk.BooleanVar(value=self.settings['minimize_to_tray'])
        self.switch_tray = ctk.CTkSwitch(self.row_tray, text="", variable=self.var_tray, command=self.save_config)
        self.switch_tray.pack(side="right")
        
        self.row_notif = ctk.CTkFrame(self.container, fg_color="transparent")
        self.row_notif.pack(fill="x", padx=20, pady=10)
        
        self.lbl_notif = ctk.CTkLabel(self.row_notif, text="Включить всплывающие уведомления при очистке", font=("Segoe UI", 13), text_color="#f3f4f6")
        self.lbl_notif.pack(side="left")
        
        self.var_notif = ctk.BooleanVar(value=self.settings['notifications_enabled'])
        self.switch_notif = ctk.CTkSwitch(self.row_notif, text="", variable=self.var_notif, command=self.save_config)
        self.switch_notif.pack(side="right")
        
    def toggle_autostart(self):
        enable = self.var_autostart.get()
        if enable:
            success = autostart.enable_autostart()
            if not success:
                messagebox.showerror("Ошибка", "Не удалось настроить задачу автозапуска в Планировщике.\nТребуются права Администратора.")
                self.var_autostart.set(False)
        else:
            success = autostart.disable_autostart()
            if not success:
                messagebox.showerror("Ошибка", "Не удалось удалить задачу автозапуска из Планировщика.\nТребуются права Администратора.")
                self.var_autostart.set(True)
                
    def on_threshold_change(self, value):
        val = int(value)
        self.lbl_threshold.configure(text=f"Очищать при заполнении: {val}%")
        self.save_config()
        
    def on_interval_change(self, value):
        val = int(value)
        self.lbl_interval.configure(text=f"Интервал проверки: {val} мин")
        self.save_config()
        
    def save_config(self):
        self.settings['auto_clean_enabled'] = self.var_autoclean.get()
        self.settings['ram_threshold'] = int(self.slider_threshold.get())
        self.settings['check_interval'] = int(self.slider_interval.get())
        self.settings['minimize_to_tray'] = self.var_tray.get()
        self.settings['notifications_enabled'] = self.var_notif.get()
        
        save_settings(self.settings)
        save_settings(self.settings)
        # Оповещаем главный контроллер об обновлении настроек
        self.controller.on_settings_updated()


class SecurityFrame(ctk.CTkFrame):
    """
    Панель сканера безопасности (Антивирус).
    """
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        # Заголовок
        self.title_label = ctk.CTkLabel(self, text="Безопасность системы", font=("Segoe UI", 24, "bold"), text_color="#f3f4f6")
        self.title_label.pack(anchor="w", padx=25, pady=(20, 10))
        
        self.desc_label = ctk.CTkLabel(
            self, 
            text="Быстрый эвристический анализ процессов, автозагрузки и интеграция с Windows Defender.", 
            justify="left", 
            font=("Segoe UI", 12), 
            text_color="#9ca3af"
        )
        self.desc_label.pack(anchor="w", padx=25, pady=(0, 15))
        
        # Контейнер
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True, padx=25, pady=5)
        
        # Левая карточка (Статус)
        self.left_card = ctk.CTkFrame(self.content_container, fg_color="#181822", corner_radius=16, border_width=1, border_color="#2b2b3a")
        self.left_card.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)
        
        self.shield_canvas = tk.Canvas(self.left_card, width=120, height=120, bg="#181822", highlightthickness=0)
        self.shield_canvas.pack(pady=(30, 10))
        self.draw_shield_icon()
        
        self.status_title = ctk.CTkLabel(self.left_card, text="Система не сканировалась", font=("Segoe UI", 16, "bold"), text_color="#9ca3af")
        self.status_title.pack(pady=5)
        
        self.status_desc = ctk.CTkLabel(self.left_card, text="Рекомендуется запустить экспресс-анализ угроз.", font=("Segoe UI", 12), text_color="#6b7280")
        self.status_desc.pack(pady=5)
        
        # Правая карточка (Действия и Лог)
        self.right_card = ctk.CTkFrame(self.content_container, fg_color="#181822", corner_radius=16, border_width=1, border_color="#2b2b3a")
        self.right_card.pack(side="right", fill="both", expand=True, padx=(10, 0), pady=10)
        
        self.actions_title = ctk.CTkLabel(self.right_card, text="Инструменты защиты", font=("Segoe UI", 15, "bold"), text_color="#8b5cf6")
        self.actions_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        self.btn_scan = ctk.CTkButton(
            self.right_card,
            text="Экспресс-сканирование",
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            font=("Segoe UI", 13, "bold"),
            height=38,
            command=self.run_local_scan
        )
        self.btn_scan.pack(fill="x", padx=20, pady=5)
        
        self.btn_defender = ctk.CTkButton(
            self.right_card,
            text="Запустить Windows Defender",
            fg_color="transparent",
            border_width=1,
            border_color="#8b5cf6",
            text_color="#8b5cf6",
            hover_color="#1e1e2d",
            font=("Segoe UI", 13, "bold"),
            height=38,
            command=self.run_defender
        )
        self.btn_defender.pack(fill="x", padx=20, pady=5)
        
        self.log_title = ctk.CTkLabel(self.right_card, text="Результаты сканирования:", font=("Segoe UI", 12, "bold"), text_color="#f3f4f6")
        self.log_title.pack(anchor="w", padx=20, pady=(15, 2))
        
        self.log_box = ctk.CTkTextbox(self.right_card, fg_color="#101017", border_width=1, border_color="#2b2b3a", text_color="#9ca3af", font=("Consolas", 11))
        self.log_box.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        self.log_box.insert("0.0", "Нажмите 'Экспресс-сканирование' для проверки процессов и hosts...")
        self.log_box.configure(state="disabled")
        
    def draw_shield_icon(self, state="normal"):
        self.shield_canvas.delete("all")
        color = "#10b981" if state == "safe" else ("#ef4444" if state == "danger" else "#8b5cf6")
        
        # Отрисовка щита
        self.shield_canvas.create_polygon(
            [20, 20, 100, 20, 100, 60, 60, 100, 20, 60],
            fill=color,
            outline=""
        )
        self.shield_canvas.create_polygon(
            [30, 30, 90, 30, 90, 58, 60, 88, 30, 58],
            fill="#181822",
            outline=""
        )
        
        if state == "safe":
            self.shield_canvas.create_line(45, 55, 55, 68, fill="#10b981", width=5)
            self.shield_canvas.create_line(55, 68, 75, 45, fill="#10b981", width=5)
        elif state == "danger":
            self.shield_canvas.create_line(45, 45, 75, 75, fill="#ef4444", width=5)
            self.shield_canvas.create_line(75, 45, 45, 75, fill="#ef4444", width=5)
        else:
            self.shield_canvas.create_text(60, 55, text="?", fill="#8b5cf6", font=("Segoe UI", 32, "bold"))
            
    def run_local_scan(self):
        self.btn_scan.configure(state="disabled", text="Сканирование...")
        self.log_box.configure(state="normal")
        self.log_box.delete("0.0", "end")
        self.log_box.insert("0.0", "[*] Сканирование запущено...\n")
        self.log_box.configure(state="disabled")
        
        def task():
            issues = optimizer.check_security_issues()
            
            def done():
                self.btn_scan.configure(state="normal", text="Экспресс-сканирование")
                self.log_box.configure(state="normal")
                
                if not issues:
                    self.log_box.insert("end", "[+] Проверка файла hosts: угроз не обнаружено.\n")
                    self.log_box.insert("end", "[+] Проверка активных процессов: подозрительных процессов не найдено.\n")
                    self.log_box.insert("end", "[+] Сканирование завершено. Угроз не обнаружено!\n")
                    self.status_title.configure(text="Система защищена", text_color="#10b981")
                    self.status_desc.configure(text="Все запущенные процессы безопасны.")
                    self.draw_shield_icon("safe")
                else:
                    self.log_box.insert("end", f"[-] Найдено подозрений: {len(issues)}\n\n")
                    for issue in issues:
                        self.log_box.insert("end", f"⚠️ {issue}\n\n")
                    self.status_title.configure(text="Обнаружены проблемы!", text_color="#ef4444")
                    self.status_desc.configure(text="Рекомендуется проверить систему антивирусом.")
                    self.draw_shield_icon("danger")
                    
                self.log_box.configure(state="disabled")
                
            self.after(0, done)
            
        threading.Thread(target=task, daemon=True).start()
        
    def run_defender(self):
        success = optimizer.run_defender_quick_scan()
        if success:
            messagebox.showinfo("Windows Defender", "Быстрое сканирование Windows Defender успешно запущено в фоновом режиме.")
        else:
            messagebox.showerror("Ошибка", "Не удалось запустить Windows Defender.")


class DiagnosticsFrame(ctk.CTkFrame):
    """
    Панель диагностики и рекомендаций системы.
    """
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        # Заголовок
        self.title_label = ctk.CTkLabel(self, text="Диагностика и модернизация", font=("Segoe UI", 24, "bold"), text_color="#f3f4f6")
        self.title_label.pack(anchor="w", padx=25, pady=(20, 10))
        
        # Основной контейнер
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=25, pady=5)
        
        # 1. Верхняя панель (Характеристики)
        self.stats_card = ctk.CTkFrame(self.main_container, fg_color="#181822", corner_radius=16, border_width=1, border_color="#2b2b3a")
        self.stats_card.pack(fill="x", pady=(0, 10))
        
        self.stats_title = ctk.CTkLabel(self.stats_card, text="Аппаратные ресурсы", font=("Segoe UI", 15, "bold"), text_color="#06b6d4")
        self.stats_title.pack(anchor="w", padx=20, pady=(12, 5))
        
        self.info_layout = ctk.CTkFrame(self.stats_card, fg_color="transparent")
        self.info_layout.pack(fill="x", padx=20, pady=(0, 12))
        
        self.lbl_ram = ctk.CTkLabel(self.info_layout, text="Оперативная память: расчет...", font=("Segoe UI", 13), text_color="#f3f4f6")
        self.lbl_ram.pack(side="left", expand=True, anchor="w")
        
        self.lbl_disk_type = ctk.CTkLabel(self.info_layout, text="Тип диска (C:): расчет...", font=("Segoe UI", 13), text_color="#f3f4f6")
        self.lbl_disk_type.pack(side="left", expand=True, anchor="w")
        
        self.lbl_space = ctk.CTkLabel(self.info_layout, text="Свободно на C:: расчет...", font=("Segoe UI", 13), text_color="#f3f4f6")
        self.lbl_space.pack(side="left", expand=True, anchor="w")
        
        # 2. Нижний контейнер (Рекомендации слева, Оптимизация справа)
        self.bottom_layout = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.bottom_layout.pack(fill="both", expand=True, pady=5)
        
        # Левая карточка (Рекомендации)
        self.rec_card = ctk.CTkFrame(self.bottom_layout, fg_color="#181822", corner_radius=16, border_width=1, border_color="#2b2b3a")
        self.rec_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.rec_title = ctk.CTkLabel(self.rec_card, text="Чего не хватает вашему ПК:", font=("Segoe UI", 15, "bold"), text_color="#f59e0b")
        self.rec_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        self.rec_scroll = ctk.CTkScrollableFrame(self.rec_card, fg_color="transparent")
        self.rec_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 15))
        
        # Правая карточка (Оптимизация)
        self.opt_card = ctk.CTkFrame(self.bottom_layout, fg_color="#181822", corner_radius=16, border_width=1, border_color="#2b2b3a", width=300)
        self.opt_card.pack(side="right", fill="both", padx=(10, 0))
        self.opt_card.pack_propagate(False)
        
        self.opt_title = ctk.CTkLabel(self.opt_card, text="Глубокая оптимизация", font=("Segoe UI", 15, "bold"), text_color="#06b6d4")
        self.opt_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        self.opt_desc = ctk.CTkLabel(
            self.opt_card, 
            text="TRIM/Дефрагментация ускоряют чтение с диска. Глубокая очистка удаляет лог-файлы Windows и временный кэш обновлений.", 
            justify="left", 
            wraplength=260, 
            font=("Segoe UI", 11), 
            text_color="#9ca3af"
        )
        self.opt_desc.pack(anchor="w", padx=20, pady=5)
        
        self.btn_defrag = ctk.CTkButton(
            self.opt_card,
            text="Оптимизировать диски",
            fg_color="#06b6d4",
            hover_color="#0891b2",
            font=("Segoe UI", 13, "bold"),
            height=38,
            command=self.run_defrag
        )
        self.btn_defrag.pack(fill="x", padx=20, pady=10)
        
        self.btn_deep_clean = ctk.CTkButton(
            self.opt_card,
            text="Глубокая очистка диска",
            fg_color="transparent",
            border_width=1,
            border_color="#06b6d4",
            text_color="#06b6d4",
            hover_color="#1e1e2d",
            font=("Segoe UI", 13, "bold"),
            height=38,
            command=self.run_deep_clean
        )
        self.btn_deep_clean.pack(fill="x", padx=20, pady=5)
        
        self.refresh_diagnostics()
        
    def refresh_diagnostics(self):
        def task():
            diag = optimizer.get_system_diagnostics()
            
            def done():
                self.lbl_ram.configure(text=f"Оперативная память: {diag['total_ram']:.1f} ГБ")
                self.lbl_disk_type.configure(text=f"Тип диска: {diag['drive_type']}")
                self.lbl_space.configure(text=f"Свободно на C:: {diag['free_c']:.1f} ГБ из {diag['total_c']:.1f} ГБ")
                
                for widget in self.rec_scroll.winfo_children():
                    widget.destroy()
                    
                for rec in diag['recommendations']:
                    rec_frame = ctk.CTkFrame(self.rec_scroll, fg_color="#20202d", corner_radius=8)
                    rec_frame.pack(fill="x", padx=5, pady=5)
                    
                    lbl = ctk.CTkLabel(rec_frame, text=rec, font=("Segoe UI", 12), justify="left", wraplength=480)
                    lbl.pack(padx=12, pady=10, anchor="w")
                    
            self.after(0, done)
            
        threading.Thread(target=task, daemon=True).start()
        
    def run_defrag(self):
        self.btn_defrag.configure(state="disabled", text="Оптимизация...")
        
        def task():
            proc = optimizer.optimize_disk_drives()
            if proc:
                stdout, stderr = proc.communicate()
                success = proc.returncode == 0
            else:
                success = False
                
            def done():
                self.btn_defrag.configure(state="normal", text="Оптимизировать диски")
                if success:
                    messagebox.showinfo("Оптимизация дисков", "Оптимизация системного диска (TRIM/Дефрагментация) успешно выполнена!")
                else:
                    messagebox.showerror("Ошибка", "Не удалось запустить оптимизацию дисков.\nУбедитесь, что приложение запущено от имени Администратора.")
                self.refresh_diagnostics()
                
            self.after(0, done)
            
        threading.Thread(target=task, daemon=True).start()
        
    def run_deep_clean(self):
        self.btn_deep_clean.configure(state="disabled", text="Очистка...")
        
        def task():
            freed_mb = optimizer.clean_deep_junk()
            
            def done():
                self.btn_deep_clean.configure(state="normal", text="Глубокая очистка диска")
                messagebox.showinfo(
                    "Глубокая очистка",
                    f"Глубокая очистка завершена!\nОсвобождено места на диске: {freed_mb:.1f} МБ"
                )
                self.refresh_diagnostics()
                if hasattr(self.controller, 'frames') and 'dashboard' in self.controller.frames:
                    self.controller.frames['dashboard'].calculate_junk_size()
                    
            self.after(0, done)
            
        threading.Thread(target=task, daemon=True).start()


class MainWindow(ctk.CTk):
    """
    Главное окно приложения CanSpeed с современным дизайном, иконками и анимациями.
    """
    def __init__(self, on_close_callback=None):
        super().__init__()
        self.on_close_callback = on_close_callback
        
        # Настройка окна
        self.title("CanSpeed - Оптимизация систем с низким объемом ОЗУ")
        self.geometry("980x660")
        self.minsize(980, 660)
        self.configure(fg_color="#0f0f13")
        
        # Генерируем иконки для сайдбара (базовые при запуске)
        self.icons = {
            "dashboard_normal": get_icon("dashboard", color="#9ca3af"),
            "dashboard_active": get_icon("dashboard", color="#ffffff"),
            "services_normal": get_icon("services", color="#9ca3af"),
            "services_active": get_icon("services", color="#ffffff"),
            "startup_normal": get_icon("startup", color="#9ca3af"),
            "startup_active": get_icon("startup", color="#ffffff"),
            "security_normal": get_icon("shield", color="#9ca3af"),
            "security_active": get_icon("shield", color="#ffffff"),
            "diagnostics_normal": get_icon("pulse", color="#9ca3af"),
            "diagnostics_active": get_icon("pulse", color="#ffffff"),
            "settings_normal": get_icon("settings", color="#9ca3af"),
            "settings_active": get_icon("settings", color="#ffffff")
        }
            
        # Сетка главного окна
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Создаем сайдбар (левая панель)
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color="#13131b", border_width=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)
        
        # Логотип в сайдбаре
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="⚡ CanSpeed", 
            font=("Segoe UI", 24, "bold"), 
            text_color="#8b5cf6"
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(25, 30))
        
        # Кнопки навигации в сайдбаре с иконками
        self.btn_dashboard = ctk.CTkButton(
            self.sidebar_frame, 
            text="Состояние системы", 
            font=("Segoe UI", 13, "bold"),
            fg_color="transparent", 
            text_color="#9ca3af",
            hover_color="#1e1e2d",
            image=self.icons["dashboard_normal"],
            compound="left",
            anchor="w",
            height=42,
            command=lambda: self.select_frame("dashboard")
        )
        self.btn_dashboard.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        
        self.btn_services = ctk.CTkButton(
            self.sidebar_frame, 
            text="Оптимизация служб", 
            font=("Segoe UI", 13, "bold"),
            fg_color="transparent", 
            text_color="#9ca3af",
            hover_color="#1e1e2d",
            image=self.icons["services_normal"],
            compound="left",
            anchor="w",
            height=42,
            command=lambda: self.select_frame("services")
        )
        self.btn_services.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        
        self.btn_startup = ctk.CTkButton(
            self.sidebar_frame, 
            text="Автозагрузка программ", 
            font=("Segoe UI", 13, "bold"),
            fg_color="transparent", 
            text_color="#9ca3af",
            hover_color="#1e1e2d",
            image=self.icons["startup_normal"],
            compound="left",
            anchor="w",
            height=42,
            command=lambda: self.select_frame("startup")
        )
        self.btn_startup.grid(row=3, column=0, padx=15, pady=5, sticky="ew")
        
        self.btn_security = ctk.CTkButton(
            self.sidebar_frame, 
            text="Безопасность системы", 
            font=("Segoe UI", 13, "bold"),
            fg_color="transparent", 
            text_color="#9ca3af",
            hover_color="#1e1e2d",
            image=self.icons["security_normal"],
            compound="left",
            anchor="w",
            height=42,
            command=lambda: self.select_frame("security")
        )
        self.btn_security.grid(row=4, column=0, padx=15, pady=5, sticky="ew")
        
        self.btn_diagnostics = ctk.CTkButton(
            self.sidebar_frame, 
            text="Диагностика ПК", 
            font=("Segoe UI", 13, "bold"),
            fg_color="transparent", 
            text_color="#9ca3af",
            hover_color="#1e1e2d",
            image=self.icons["diagnostics_normal"],
            compound="left",
            anchor="w",
            height=42,
            command=lambda: self.select_frame("diagnostics")
        )
        self.btn_diagnostics.grid(row=5, column=0, padx=15, pady=5, sticky="ew")
        
        self.btn_settings = ctk.CTkButton(
            self.sidebar_frame, 
            text="Настройки программы", 
            font=("Segoe UI", 13, "bold"),
            fg_color="transparent", 
            text_color="#9ca3af",
            hover_color="#1e1e2d",
            image=self.icons["settings_normal"],
            compound="left",
            anchor="w",
            height=42,
            command=lambda: self.select_frame("settings")
        )
        self.btn_settings.grid(row=6, column=0, padx=15, pady=5, sticky="ew")
        
        # Информация о версии снизу
        self.version_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="Версия 1.2.0 (x64)\nРазработано для 6 ГБ ОЗУ", 
            font=("Segoe UI", 10), 
            text_color="#4b5563"
        )
        self.version_label.grid(row=8, column=0, padx=20, pady=15)
        
        # Создаем контейнеры под каждую вкладку
        self.frames = {}
        self.frames["dashboard"] = DashboardFrame(self, self)
        self.frames["services"] = ServicesFrame(self, self)
        self.frames["startup"] = StartupFrame(self, self)
        self.frames["security"] = SecurityFrame(self, self)
        self.frames["diagnostics"] = DiagnosticsFrame(self, self)
        self.frames["settings"] = SettingsFrame(self, self)
        
        # Отображаем стартовую вкладку
        self.current_frame_name = "dashboard"
        self.select_frame("dashboard")
        
        # Перехват кнопки закрытия
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Запускаем фоновое скачивание иконок шрифта Boxicons
        self.start_font_download()
        
    def start_font_download(self):
        """
        Запускает фоновое скачивание шрифта Boxicons и обновление иконок в GUI.
        """
        def task():
            download_font_if_needed()
            if os.path.exists(FONT_PATH):
                self.after(0, self.reload_all_icons)
        threading.Thread(target=task, daemon=True).start()
        
    def reload_all_icons(self):
        """
        Пересоздает иконки после скачивания шрифта и обновляет их на кнопках.
        """
        try:
            self.icons = {
                "dashboard_normal": get_icon("dashboard", color="#9ca3af"),
                "dashboard_active": get_icon("dashboard", color="#ffffff"),
                "services_normal": get_icon("services", color="#9ca3af"),
                "services_active": get_icon("services", color="#ffffff"),
                "startup_normal": get_icon("startup", color="#9ca3af"),
                "startup_active": get_icon("startup", color="#ffffff"),
                "security_normal": get_icon("shield", color="#9ca3af"),
                "security_active": get_icon("shield", color="#ffffff"),
                "diagnostics_normal": get_icon("pulse", color="#9ca3af"),
                "diagnostics_active": get_icon("pulse", color="#ffffff"),
                "settings_normal": get_icon("settings", color="#9ca3af"),
                "settings_active": get_icon("settings", color="#ffffff")
            }
            
            # Обновляем базовые иконки на кнопках навигации
            self.btn_dashboard.configure(image=self.icons["dashboard_normal"])
            self.btn_services.configure(image=self.icons["services_normal"])
            self.btn_startup.configure(image=self.icons["startup_normal"])
            self.btn_security.configure(image=self.icons["security_normal"])
            self.btn_diagnostics.configure(image=self.icons["diagnostics_normal"])
            self.btn_settings.configure(image=self.icons["settings_normal"])
            
            # Обновляем активную вкладку, чтобы применить цвет
            if hasattr(self, 'current_frame_name'):
                self.select_frame(self.current_frame_name)
        except Exception:
            pass
        
    def select_frame(self, frame_name):
        # Сохраняем имя текущей активной вкладки
        self.current_frame_name = frame_name
        
        # Деактивируем подсветку всех кнопок и сбрасываем иконки
        self.btn_dashboard.configure(fg_color="transparent", text_color="#9ca3af", image=self.icons["dashboard_normal"])
        self.btn_services.configure(fg_color="transparent", text_color="#9ca3af", image=self.icons["services_normal"])
        self.btn_startup.configure(fg_color="transparent", text_color="#9ca3af", image=self.icons["startup_normal"])
        self.btn_security.configure(fg_color="transparent", text_color="#9ca3af", image=self.icons["security_normal"])
        self.btn_diagnostics.configure(fg_color="transparent", text_color="#9ca3af", image=self.icons["diagnostics_normal"])
        self.btn_settings.configure(fg_color="transparent", text_color="#9ca3af", image=self.icons["settings_normal"])
        
        # Подсвечиваем активную кнопку и ставим активную иконку
        if frame_name == "dashboard":
            self.btn_dashboard.configure(fg_color="#8b5cf6", text_color="#ffffff", image=self.icons["dashboard_active"])
        elif frame_name == "services":
            self.btn_services.configure(fg_color="#8b5cf6", text_color="#ffffff", image=self.icons["services_active"])
            self.frames["services"].load_services()
        elif frame_name == "startup":
            self.btn_startup.configure(fg_color="#8b5cf6", text_color="#ffffff", image=self.icons["startup_active"])
            self.frames["startup"].load_startup_items()
        elif frame_name == "security":
            self.btn_security.configure(fg_color="#8b5cf6", text_color="#ffffff", image=self.icons["security_active"])
        elif frame_name == "diagnostics":
            self.btn_diagnostics.configure(fg_color="#8b5cf6", text_color="#ffffff", image=self.icons["diagnostics_active"])
            self.frames["diagnostics"].refresh_diagnostics()
        elif frame_name == "settings":
            self.btn_settings.configure(fg_color="#8b5cf6", text_color="#ffffff", image=self.icons["settings_active"])
            
        # Убираем все фреймы с экрана
        for name, frame in self.frames.items():
            frame.grid_forget()
            
        # Показываем выбранный с плавной анимацией "всплывания" снизу вверх
        frame = self.frames[frame_name]
        
        def animate_slide(current_pady):
            if current_pady > 10:
                new_pady = max(10, current_pady - 2)
                frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=(new_pady, 20 - new_pady))
                self.after(8, lambda: animate_slide(new_pady))
            else:
                frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
                
        frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=(32, 0))
        self.after(5, lambda: animate_slide(32))
        
    def on_settings_updated(self):
        if self.on_close_callback:
            self.on_close_callback("settings_updated")
            
    def on_close(self):
        settings = load_settings()
        if settings['minimize_to_tray']:
            self.withdraw()  # Просто прячем окно
        else:
            if self.on_close_callback:
                self.on_close_callback("exit")
            self.destroy()
            sys.exit(0)
