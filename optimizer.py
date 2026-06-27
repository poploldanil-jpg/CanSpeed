import ctypes
import os
import shutil
import subprocess
import sys
import psutil

# Константы для Windows API
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_SET_QUOTA = 0x0100

def trim_process_memory(pid):
    """
    Освобождает неиспользуемую память (рабочий набор) для конкретного процесса по PID.
    """
    try:
        h_process = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA,
            False,
            pid
        )
        if h_process:
            # Вызываем EmptyWorkingSet из psapi.dll
            result = ctypes.windll.psapi.EmptyWorkingSet(h_process)
            ctypes.windll.kernel32.CloseHandle(h_process)
            return bool(result)
    except Exception:
        pass
    return False

def optimize_ram():
    """
    Проходит по всем процессам и минимизирует их рабочий набор памяти.
    Возвращает кортеж (успешно_очищено_процессов, память_до_мб, память_после_мб).
    """
    mem_before = psutil.virtual_memory().used
    cleaned_count = 0
    
    # Очищаем память для всех процессов
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            # Пропускаем критические системные процессы с PID <= 4 (Idle, System)
            if proc.info['pid'] <= 4:
                continue
            if trim_process_memory(proc.info['pid']):
                cleaned_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
            
    # Также очищаем память текущего процесса CanSpeed
    trim_process_memory(os.getpid())
    
    mem_after = psutil.virtual_memory().used
    freed_bytes = max(0, mem_before - mem_after)
    freed_mb = freed_bytes / (1024 * 1024)
    
    return cleaned_count, mem_before / (1024 * 1024), mem_after / (1024 * 1024), freed_mb

def get_junk_paths():
    """
    Возвращает список директорий с временными файлами.
    """
    paths = []
    
    # Пользовательская папка Temp
    user_temp = os.environ.get('TEMP')
    if user_temp and os.path.exists(user_temp):
        paths.append(('User Temp', user_temp))
        
    # Системная папка Temp
    system_temp = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp')
    if os.path.exists(system_temp):
        paths.append(('System Temp', system_temp))
        
    # Папка Prefetch
    prefetch = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Prefetch')
    if os.path.exists(prefetch):
        paths.append(('Prefetch', prefetch))
        
    # Кэш обновлений Windows
    win_update = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'SoftwareDistribution\\Download')
    if os.path.exists(win_update):
        paths.append(('Windows Update Cache', win_update))
        
    return paths

def get_folder_size(path):
    """
    Возвращает размер папки в мегабайтах.
    """
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # Пропускаем символические ссылки
                if not os.path.islink(fp):
                    try:
                        total_size += os.path.getsize(fp)
                    except OSError:
                        pass
    except Exception:
        pass
    return total_size / (1024 * 1024)

def clean_junk():
    """
    Удаляет временные файлы из системных и пользовательских папок.
    Возвращает объем удаленных файлов в МБ.
    """
    total_freed_mb = 0
    paths = get_junk_paths()
    
    for name, path in paths:
        size_before = get_folder_size(path)
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception:
                    # Файлы могут быть заблокированы запущенными процессами
                    pass
        except Exception:
            pass
        size_after = get_folder_size(path)
        total_freed_mb += max(0.0, size_before - size_after)
        
    return total_freed_mb

# Список рекомендуемых к отключению служб для ноутбука с 6 ГБ ОЗУ
OPTIMIZABLE_SERVICES = {
    'DiagTrack': 'Телеметрия и сбор диагностических данных (Служба функциональных возможностей для подключенных пользователей и телеметрии)',
    'dmwappushservice': 'Служба маршрутизации сообщений push-уведомлений WAP (телеметрия)',
    'WerSvc': 'Служба регистрации ошибок Windows (отправляет отчеты об ошибках в Microsoft)',
    'XblAuthManager': 'Диспетчер проверки подлинности Xbox Live (если вы не играете в игры Xbox)',
    'XboxNetApiSvc': 'Сетевая служба Xbox Live',
    'XboxGipSvc': 'Вспомогательная служба IP Xbox Live',
    'MapsBroker': 'Диспетчер скачанных карт (если вы не используете встроенные карты Windows)',
    'Spooler': 'Диспетчер печати (можно отключить, если у вас нет принтера)',
    'SysMain': 'Служба оптимизации запуска приложений SysMain/Superfetch (часто перегружает диск на медленных HDD/SSD)',
}

def get_service_status(service_name):
    """
    Возвращает статус службы и тип запуска: (is_running, startup_type)
    startup_type может быть: 'Automatic', 'Manual', 'Disabled', 'Unknown'
    """
    try:
        # Проверяем запущена ли служба
        query_cmd = ['sc', 'query', service_name]
        query_out = subprocess.check_output(query_cmd, startupinfo=get_startupinfo(), text=True, errors='ignore')
        is_running = 'RUNNING' in query_out
        
        # Проверяем тип автозапуска
        qc_cmd = ['sc', 'qc', service_name]
        qc_out = subprocess.check_output(qc_cmd, startupinfo=get_startupinfo(), text=True, errors='ignore')
        
        startup_type = 'Unknown'
        if 'DEMAND_START' in qc_out:
            startup_type = 'Manual'
        elif 'AUTO_START' in qc_out:
            startup_type = 'Automatic'
        elif 'DISABLED' in qc_out:
            startup_type = 'Disabled'
            
        return is_running, startup_type
    except Exception:
        return False, 'Unknown'

def set_service_state(service_name, target_state):
    """
    Изменяет состояние службы.
    target_state может быть: 'disable' (отключить автозапуск и остановить),
    'enable_manual' (поставить вручную), 'enable_auto' (поставить автоматически и запустить)
    """
    try:
        if target_state == 'disable':
            # Сначала останавливаем службу
            subprocess.run(['sc', 'stop', service_name], startupinfo=get_startupinfo(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Затем отключаем в автозагрузке
            res = subprocess.run(['sc', 'config', service_name, 'start=', 'disabled'], startupinfo=get_startupinfo(), capture_output=True, text=True)
            return res.returncode == 0
        elif target_state == 'enable_manual':
            res = subprocess.run(['sc', 'config', service_name, 'start=', 'demand'], startupinfo=get_startupinfo(), capture_output=True, text=True)
            return res.returncode == 0
        elif target_state == 'enable_auto':
            res = subprocess.run(['sc', 'config', service_name, 'start=', 'auto'], startupinfo=get_startupinfo(), capture_output=True, text=True)
            if res.returncode == 0:
                subprocess.run(['sc', 'start', service_name], startupinfo=get_startupinfo(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
    except Exception:
        pass
    return False

def get_startupinfo():
    """
    Возвращает STARTUPINFO структуру для скрытия окон консоли при вызове subprocess на Windows.
    """
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    return startupinfo

# --- Новые расширенные функции оптимизации ---

def clean_recycle_bin():
    """
    Очищает Корзину Windows без вывода диалогов и звуков.
    """
    try:
        if os.name == 'nt':
            shell32 = ctypes.windll.shell32
            # Флаги: SHERB_NOCONFIRMATION (0x01) | SHERB_NOPROGRESSUI (0x02) | SHERB_NOSOUND (0x04)
            result = shell32.SHEmptyRecycleBinW(None, None, 7)
            return result == 0
    except Exception:
        pass
    return False

def clean_clipboard():
    """
    Очищает системный буфер обмена Windows.
    """
    try:
        if os.name == 'nt':
            user32 = ctypes.windll.user32
            if user32.OpenClipboard(None):
                user32.EmptyClipboard()
                user32.CloseClipboard()
                return True
    except Exception:
        pass
    return False

def get_browser_cache_paths():
    """
    Возвращает список путей к папкам кэша популярных браузеров.
    """
    paths = []
    local_appdata = os.environ.get('LOCALAPPDATA')
    appdata = os.environ.get('APPDATA')
    
    if local_appdata:
        # Google Chrome
        chrome = os.path.join(local_appdata, r"Google\Chrome\User Data\Default\Cache\Cache_Data")
        chrome_code = os.path.join(local_appdata, r"Google\Chrome\User Data\Default\Code Cache")
        if os.path.exists(chrome):
            paths.append(('Chrome Cache', chrome))
        if os.path.exists(chrome_code):
            paths.append(('Chrome Code Cache', chrome_code))
            
        # Microsoft Edge
        edge = os.path.join(local_appdata, r"Microsoft\Edge\User Data\Default\Cache\Cache_Data")
        edge_code = os.path.join(local_appdata, r"Microsoft\Edge\User Data\Default\Code Cache")
        if os.path.exists(edge):
            paths.append(('Edge Cache', edge))
        if os.path.exists(edge_code):
            paths.append(('Edge Code Cache', edge_code))
            
        # Yandex Browser
        yandex = os.path.join(local_appdata, r"Yandex\YandexBrowser\User Data\Default\Cache\Cache_Data")
        yandex_code = os.path.join(local_appdata, r"Yandex\YandexBrowser\User Data\Default\Code Cache")
        if os.path.exists(yandex):
            paths.append(('Yandex Cache', yandex))
        if os.path.exists(yandex_code):
            paths.append(('Yandex Code Cache', yandex_code))

    if appdata:
        # Mozilla Firefox
        firefox_profiles = os.path.join(appdata, r"Mozilla\Firefox\Profiles")
        if os.path.exists(firefox_profiles):
            try:
                for profile in os.listdir(firefox_profiles):
                    profile_cache = os.path.join(local_appdata, r"Mozilla\Firefox\Profiles", profile, "cache2")
                    if os.path.exists(profile_cache):
                        paths.append((f'Firefox Cache ({profile})', profile_cache))
            except Exception:
                pass
                
    return paths

def clean_browser_cache():
    """
    Очищает кэш браузеров и возвращает количество освобожденных мегабайт.
    """
    total_freed_mb = 0
    paths = get_browser_cache_paths()
    for name, path in paths:
        size_before = get_folder_size(path)
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception:
                    pass
        except Exception:
            pass
        size_after = get_folder_size(path)
        total_freed_mb += max(0.0, size_before - size_after)
    return total_freed_mb

# --- Логика очистки Standby List (кэша файловой системы Windows) ---

def enable_privilege(privilege_name):
    """
    Включает привилегию для текущего процесса.
    """
    import ctypes
    from ctypes import wintypes
    
    TOKEN_ADJUST_PRIVILEGES = 0x0020
    TOKEN_QUERY = 0x0008
    SE_PRIVILEGE_ENABLED = 0x00000002
    
    class LUID(ctypes.Structure):
        _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]
        
    class LUID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]
        
    class TOKEN_PRIVILEGES(ctypes.Structure):
        _fields_ = [("PrivilegeCount", wintypes.DWORD), ("Privileges", LUID_AND_ATTRIBUTES * 1)]
        
    try:
        advapi32 = ctypes.windll.advapi32
        kernel32 = ctypes.windll.kernel32
        
        hToken = wintypes.HANDLE()
        if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(hToken)):
            return False
            
        luid = LUID()
        if not advapi32.LookupPrivilegeValueW(None, privilege_name, ctypes.byref(luid)):
            kernel32.CloseHandle(hToken)
            return False
            
        tp = TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges[0].Luid = luid
        tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
        
        result = advapi32.AdjustTokenPrivileges(hToken, False, ctypes.byref(tp), 0, None, None)
        kernel32.CloseHandle(hToken)
        return bool(result)
    except Exception:
        return False

def clean_system_cache_standby():
    """
    Очищает Standby List (кэш файловой системы) Windows через NtSetSystemInformation.
    Освобождает ОЗУ без вреда для работающих программ.
    """
    try:
        if os.name != 'nt':
            return False
            
        # Запрашиваем привилегии
        enable_privilege("SeProfileSingleProcessPrivilege")
        enable_privilege("SeIncreaseQuotaPrivilege")
        
        # Команда 4: MemoryPurgeStandbyList
        # Очищает список ожидания страниц памяти
        command = ctypes.c_ulong(4)
        status = ctypes.windll.ntdll.NtSetSystemInformation(
            80,  # SystemMemoryListInformation
            ctypes.byref(command),
            ctypes.sizeof(command)
        )
        return status == 0
    except Exception:
        return False

# --- Логика Игрового режима (управление приоритетами) ---

def apply_game_boost(enabled=True):
    """
    Применяет Игровой режим: повышает приоритет активного процесса до HIGH,
    понижает приоритет тяжелых фоновых приложений (браузеры, лаунчеры, мессенджеры) до IDLE.
    """
    try:
        if os.name != 'nt':
            return
            
        user32 = ctypes.windll.user32
        foreground_hwnd = user32.GetForegroundWindow()
        active_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(foreground_hwnd, ctypes.byref(active_pid))
        active_pid = active_pid.value
        
        heavy_bg_apps = [
            'chrome.exe', 'msedge.exe', 'yandex.exe', 'firefox.exe', 'opera.exe',
            'discord.exe', 'steam.exe', 'epicgameslauncher.exe', 'spotify.exe',
            'telegram.exe', 'skype.exe', 'battle.net.exe', 'viber.exe'
        ]
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pid = proc.info['pid']
                name = proc.info['name'].lower()
                
                # Пропускаем критически важные процессы
                if pid <= 4 or name == 'explorer.exe' or pid == os.getpid():
                    continue
                    
                p = psutil.Process(pid)
                
                # Если процесс активен и это не проводник и не фоновое приложение
                if pid == active_pid and active_pid != 0:
                    if name not in ['explorer.exe', 'cmd.exe', 'powershell.exe', 'conhost.exe', 'taskmgr.exe'] and name not in heavy_bg_apps:
                        if enabled:
                            # Повышаем приоритет игры/активной программы
                            p.nice(psutil.HIGH_PRIORITY_CLASS)
                        else:
                            p.nice(psutil.NORMAL_PRIORITY_CLASS)
                # Если процесс из списка тяжелых фоновых
                elif name in heavy_bg_apps:
                    if enabled:
                        p.nice(psutil.IDLE_PRIORITY_CLASS)
                    else:
                        p.nice(psutil.NORMAL_PRIORITY_CLASS)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass

# --- Новые функции: Сканер безопасности (антивирус) ---

def run_defender_quick_scan():
    """
    Запускает быстрое сканирование через Windows Defender в фоновом режиме.
    """
    try:
        if os.name == 'nt':
            cmd = ['powershell', '-NoProfile', '-Command', "Start-MpScan -ScanType QuickScan"]
            subprocess.Popen(cmd, startupinfo=get_startupinfo())
            return True
    except Exception:
        pass
    return False

def check_security_issues():
    """
    Эвристический сканер безопасности: ищет аномальные запущенные процессы и изменения hosts.
    """
    issues = []
    
    # 1. Проверка файла hosts
    hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
    if os.path.exists(hosts_path):
        try:
            with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            suspicious_domains = ["google", "yandex", "vk.com", "mail.ru", "youtube", "microsoft", "github"]
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    for domain in suspicious_domains:
                        if domain in line and not ("127.0.0.1" in line and "localhost" in line):
                            issues.append(f"Файл hosts: Подозрительное перенаправление в строке '{line}'")
                            break
        except Exception:
            pass
            
    # 2. Проверка запущенных процессов
    try:
        system_root = os.environ.get('SystemRoot', 'C:\\Windows').lower()
        temp_dirs = [
            os.environ.get('TEMP', '').lower(),
            os.path.join(os.environ.get('USERPROFILE', ''), 'appdata\\local\\temp').lower(),
            os.path.join(os.environ.get('USERPROFILE', ''), 'appdata\\roaming').lower(),
        ]
        temp_dirs = [d for d in temp_dirs if d]
        
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                pid = proc.info['pid']
                name = proc.info['name'].lower()
                exe = proc.info['exe']
                
                if not exe:
                    continue
                    
                exe_lower = exe.lower()
                
                # Проверка запуска из временных папок
                is_in_temp = False
                for temp_dir in temp_dirs:
                    if exe_lower.startswith(temp_dir):
                        is_in_temp = True
                        break
                        
                if is_in_temp:
                    # Разрешенные популярные программы в AppData
                    allowed_apps = ["discord", "telegram", "spotify", "chrome", "yandex", "update", "teams", "roblox", "code"]
                    is_allowed = any(app in exe_lower for app in allowed_apps)
                    if not is_allowed:
                        issues.append(f"Подозрительный файл: {name} (PID: {pid}) запущен из временной папки ({exe})")
                        
                # Проверка маскировки под системные файлы
                system_procs = ["svchost.exe", "lsass.exe", "taskhost.exe", "csrss.exe", "services.exe", "winlogon.exe", "smss.exe"]
                if name in system_procs:
                    allowed_sys_path = os.path.join(system_root, "system32")
                    allowed_sys_path2 = os.path.join(system_root, "syswow64")
                    if not (exe_lower.startswith(allowed_sys_path) or exe_lower.startswith(allowed_sys_path2)):
                        issues.append(f"Критическая угроза: Процесс {name} (PID: {pid}) запущен не из системной папки ({exe})!")
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
        
    return issues

# --- Новые функции: Оптимизация и диагностика дисков ---

def optimize_disk_drives():
    """
    Запускает оптимизацию дисков (TRIM для SSD / Дефрагментация для HDD).
    """
    try:
        if os.name == 'nt':
            cmd = ['defrag', 'C:', '/O']
            # Запуск defrag (требует прав админа)
            proc = subprocess.Popen(cmd, startupinfo=get_startupinfo(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return proc
    except Exception:
        pass
    return None

def clean_deep_junk():
    """
    Выполняет глубокую очистку диска (Delivery Optimization, системные логи, дампы).
    """
    total_freed_mb = 0
    paths = []
    
    # Кэш оптимизации доставки обновлений
    del_opt = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'SoftwareDistribution\\DeliveryOptimization')
    if os.path.exists(del_opt):
        paths.append(('Delivery Optimization Cache', del_opt))
        
    # Лог-файлы Windows
    win_logs = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Logs')
    if os.path.exists(win_logs):
        paths.append(('Windows Logs', win_logs))
        
    # Системные дампы ошибок
    win_dumps = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Minidump')
    if os.path.exists(win_dumps):
        paths.append(('System Minidumps', win_dumps))
        
    for name, path in paths:
        size_before = get_folder_size(path)
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception:
                    pass
        except Exception:
            pass
        size_after = get_folder_size(path)
        total_freed_mb += max(0.0, size_before - size_after)
        
    return total_freed_mb

def get_drive_type():
    """
    Определяет тип системного накопителя C: (SSD или HDD).
    """
    try:
        if os.name == 'nt':
            ps_cmd = "Get-Partition -DriveLetter C | Get-Disk | Select-Object -ExpandProperty MediaType"
            cmd = ['powershell', '-NoProfile', '-Command', ps_cmd]
            out = subprocess.check_output(cmd, startupinfo=get_startupinfo(), text=True, errors='ignore').strip()
            if "SSD" in out:
                return "SSD (Высокоскоростной)"
            elif "HDD" in out:
                return "HDD (Медленный)"
            return out if out else "Неизвестно"
    except Exception:
        pass
    return "Неизвестно"

def get_system_diagnostics():
    """
    Собирает диагностику ПК и формирует список рекомендаций по модернизации.
    """
    mem = psutil.virtual_memory()
    total_ram_gb = mem.total / (1024**3)
    
    c_disk = psutil.disk_usage('C:\\')
    free_c_gb = c_disk.free / (1024**3)
    total_c_gb = c_disk.total / (1024**3)
    
    drive_type = get_drive_type()
    recommendations = []
    
    # 1. Анализ ОЗУ
    if total_ram_gb < 7.5:
        recommendations.append(
            "⚠️ Недостаточно ОЗУ: Установлено всего {:.1f} ГБ оперативной памяти. "
            "Для плавной работы рекомендуется увеличить объем до 8 или 16 ГБ.".format(total_ram_gb)
        )
    else:
        recommendations.append("✅ Объем оперативной памяти в норме: {:.1f} ГБ.".format(total_ram_gb))
        
    # 2. Анализ накопителя (SSD/HDD)
    if "HDD" in drive_type:
        recommendations.append(
            "⚠️ Системный диск типа HDD: Windows установлена на медленном жестком диске. "
            "Замена системного диска на SSD ускорит запуск и отзывчивость системы в 5-10 раз!"
        )
    elif "SSD" in drive_type:
        recommendations.append("✅ Системный диск типа SSD: обеспечивает максимальное быстродействие системы.")
        
    # 3. Анализ свободного места
    if free_c_gb < 15:
        recommendations.append(
            "⚠️ Мало места на диске C: Свободно всего {:.1f} ГБ из {:.1f} ГБ. "
            "Освободите место для корректной работы файла подкачки и исключения тормозов Windows.".format(free_c_gb, total_c_gb)
        )
    else:
        recommendations.append("✅ Свободное место на диске C в норме: свободно {:.1f} ГБ.".format(free_c_gb))
        
    # 4. Анализ автозапуска
    try:
        import json
        settings_file = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'CanSpeed', 'settings.json')
        startup_count = 0
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                
            import winreg
            for hive, path in [(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
                                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run")]:
                try:
                    key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
                    info = winreg.QueryInfoKey(key)
                    startup_count += info[0]
                    winreg.CloseKey(key)
                except Exception:
                    pass
                    
            if startup_count > 5:
                recommendations.append(
                    "⚠️ Много программ в автозагрузке: Найдено {} активных элементов. "
                    "Отключите лишние программы во вкладке 'Автозагрузка программ'.".format(startup_count)
                )
    except Exception:
        pass
        
    return {
        "total_ram": total_ram_gb,
        "free_c": free_c_gb,
        "total_c": total_c_gb,
        "drive_type": drive_type,
        "recommendations": recommendations
    }


