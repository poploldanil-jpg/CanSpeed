import os
import sys
import time
import threading
import psutil
from PIL import Image, ImageDraw
import pystray

import optimizer
import autostart
import gui

# Глобальные переменные для трея и потоков
icon_instance = None
window_instance = None
stop_event = threading.Event()
background_thread = None

def create_tray_icon_image():
    """
    Генерирует красивую иконку для системного трея (фиолетовый круг с молнией) динамически.
    """
    image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    
    # Рисуем красивый фиолетовый круг (цвет бренда CanSpeed #8b5cf6)
    dc.ellipse([4, 4, 60, 60], fill=(139, 92, 246, 255))
    
    # Рисуем белую молнию по центру
    dc.polygon([
        (32, 10),  # Верх
        (44, 28),  # Право
        (34, 28),  # Центр-право
        (38, 54),  # Низ
        (20, 34),  # Лево
        (30, 34)   # Центр-лево
    ], fill=(255, 255, 255, 255))
    
    return image

def show_notification(message, title="⚡ CanSpeed"):
    """
    Показывает всплывающее уведомление Windows.
    """
    try:
        global icon_instance
        settings = gui.load_settings()
        if icon_instance and settings.get('notifications_enabled', True):
            icon_instance.notify(message, title)
    except Exception:
        pass

def on_tray_action(icon, item):
    """
    Обработчик кликов по меню трея.
    """
    global window_instance
    action = str(item)
    
    if action == "Открыть CanSpeed":
        if window_instance:
            window_instance.after(0, lambda: restore_window())
    elif action == "Оптимизировать ОЗУ":
        # Запускаем в отдельном потоке, чтобы не вешать трей
        def task():
            cleaned_count, before_mb, after_mb, freed_mb = optimizer.optimize_ram()
            show_notification(
                f"Ручная оптимизация: освобождено {freed_mb:.1f} МБ ОЗУ.",
                "Оптимизация ОЗУ"
            )
            if window_instance and window_instance.winfo_exists():
                window_instance.after(0, lambda: window_instance.frames["dashboard"].update_stats())
        threading.Thread(target=task, daemon=True).start()
    elif action == "Выход":
        exit_application()

def restore_window():
    """
    Восстанавливает скрытое окно приложения на передний план.
    """
    global window_instance
    if window_instance:
        window_instance.deiconify()
        window_instance.state("normal")
        window_instance.lift()
        window_instance.focus_force()

def exit_application():
    """
    Полностью останавливает фоновые потоки и завершает программу.
    """
    global icon_instance, window_instance, stop_event
    stop_event.set()
    
    if icon_instance:
        icon_instance.stop()
        
    if window_instance:
        try:
            window_instance.destroy()
        except Exception:
            pass
            
    sys.exit(0)

def background_optimizer_loop():
    """
    Фоновый цикл проверки оперативной памяти, автоочистки и поддержания Игрового режима.
    """
    last_game_boost_state = False
    
    # Ожидание 30 секунд после запуска системы с проверкой на завершение
    for _ in range(6):
        if stop_event.is_set():
            return
        time.sleep(5)
    
    while not stop_event.is_set():
        settings = gui.load_settings()
        game_boost_enabled = settings.get('game_boost_enabled', False)
        
        # Если режим отключили, возвращаем приоритеты
        if not game_boost_enabled and last_game_boost_state:
            optimizer.apply_game_boost(False)
        elif game_boost_enabled:
            optimizer.apply_game_boost(True)
            
        last_game_boost_state = game_boost_enabled
        
        # Автоматическая очистка по порогу
        if settings.get('auto_clean_enabled', True):
            mem = psutil.virtual_memory()
            threshold = settings.get('ram_threshold', 80)
            
            if mem.percent >= threshold:
                cleaned_count, before_mb, after_mb, freed_mb = optimizer.optimize_ram()
                
                # Дополнительно очищаем Standby List в фоне, если включено
                if settings.get('clean_standby_enabled', True):
                    optimizer.clean_system_cache_standby()
                
                if freed_mb > 50:
                    show_notification(
                        f"Освобождено {freed_mb:.0f} МБ ОЗУ.\nИспользование снижено до {psutil.virtual_memory().percent:.0f}%.",
                        "Автоматическая очистка памяти"
                    )
                
                if window_instance and window_instance.winfo_exists():
                    window_instance.after(0, lambda: window_instance.frames["dashboard"].update_stats())
                    
        # Интервальный сон с проверкой игрового режима каждые 5 секунд
        check_interval_minutes = settings.get('check_interval', 15)
        check_interval_seconds = max(10, check_interval_minutes * 60)
        
        slept = 0
        while slept < check_interval_seconds:
            if stop_event.is_set():
                return
            
            curr_settings = gui.load_settings()
            curr_gb_enabled = curr_settings.get('game_boost_enabled', False)
            
            if not curr_gb_enabled and last_game_boost_state:
                optimizer.apply_game_boost(False)
            elif curr_gb_enabled:
                optimizer.apply_game_boost(True)
                
            last_game_boost_state = curr_gb_enabled
            
            time.sleep(5)
            slept += 5

def on_gui_callback(event_type):
    """
    Коллбек от GUI окна (например, при выходе или обновлении настроек).
    """
    if event_type == "exit":
        exit_application()
    elif event_type == "settings_updated":
        # Быстрая реакция на изменение игрового режима из GUI
        settings = gui.load_settings()
        enabled = settings.get('game_boost_enabled', False)
        threading.Thread(target=lambda: optimizer.apply_game_boost(enabled), daemon=True).start()

def start_tray():
    """
    Инициализирует и запускает системный трей.
    """
    global icon_instance
    menu = pystray.Menu(
        pystray.MenuItem("Открыть CanSpeed", on_tray_action, default=True),
        pystray.MenuItem("Оптимизировать ОЗУ", on_tray_action),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Выход", on_tray_action)
    )
    
    icon_image = create_tray_icon_image()
    icon_instance = pystray.Icon(
        "CanSpeed", 
        icon_image, 
        "CanSpeed Optimizer", 
        menu
    )
    icon_instance.run()

def main():
    global window_instance, background_thread
    
    # 1. Запускаем системный трей в фоновом потоке
    tray_thread = threading.Thread(target=start_tray, daemon=True)
    tray_thread.start()
    
    # 2. Запускаем фоновый мониторинг ОЗУ в фоновом потоке
    background_thread = threading.Thread(target=background_optimizer_loop, daemon=True)
    background_thread.start()
    
    # 3. Инициализируем GUI
    window_instance = gui.MainWindow(on_close_callback=on_gui_callback)
    
    # Проверяем, запущен ли со специальным флагом для автозагрузки (чтобы не открывать окно на весь экран)
    if "--startup" in sys.argv:
        # Запуск скрытым в трее
        window_instance.withdraw()
    else:
        # Обычный запуск: отображаем окно по центру
        window_instance.update()
        
    # Запускаем цикл обработки событий Tkinter
    window_instance.mainloop()

if __name__ == '__main__':
    # Гарантируем, что запущена только одна копия программы
    # С помощью именованного мьютекса Windows
    import ctypes
    mutex_name = "Global\\CanSpeedOptimizerMutex"
    # CreateMutexW возвращает дескриптор или NULL при ошибке.
    # Если мьютекс уже существует, GetLastError вернет ERROR_ALREADY_EXISTS (183).
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    last_error = kernel32.GetLastError()
    
    if last_error == 183: # ERROR_ALREADY_EXISTS
        # Если программа уже запущена, выходим
        sys.exit(0)
        
    main()
