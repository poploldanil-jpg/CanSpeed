import os
import sys
import subprocess

TASK_NAME = "CanSpeedOptimizer"

def get_startupinfo():
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    return startupinfo

def is_autostart_enabled():
    """
    Проверяет, создана ли уже задача автозапуска в Планировщике задач Windows.
    """
    try:
        cmd = ['schtasks', '/query', '/tn', TASK_NAME]
        res = subprocess.run(cmd, startupinfo=get_startupinfo(), capture_output=True, text=True, errors='ignore')
        return res.returncode == 0
    except Exception:
        return False

def enable_autostart():
    """
    Создает задачу в Планировщике задач Windows для запуска программы при входе пользователя
    с правами Администратора (чтобы не было UAC-запроса при каждой загрузке)
    и с отключенными ограничениями на питание от батареи.
    """
    try:
        if getattr(sys, 'frozen', False):
            # Запущено как скомпилированный EXE
            executable = sys.executable
            arguments = "--startup"
        else:
            # Запущено как скрипт Python
            python_exe = sys.executable
            executable = python_exe.replace("python.exe", "pythonw.exe")
            if not os.path.exists(executable):
                executable = python_exe
            main_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main.py')
            arguments = f'"{main_py}" --startup'
            
        # Формируем скрипт PowerShell для создания задачи с нужными параметрами питания
        ps_script = f"""
        $action = New-ScheduledTaskAction -Execute '{executable}' -Argument '{arguments}'
        $trigger = New-ScheduledTaskTrigger -AtLogOn
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Compatibility Win8
        $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\\$env:USERNAME" -RunLevel Highest
        Register-ScheduledTask -TaskName '{TASK_NAME}' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force
        """
        
        # Выполняем PowerShell скрипт
        cmd = ['powershell', '-NoProfile', '-WindowStyle', 'Hidden', '-Command', ps_script]
        res = subprocess.run(cmd, startupinfo=get_startupinfo(), capture_output=True, text=True, errors='ignore')
        return res.returncode == 0
    except Exception as e:
        return False

def disable_autostart():
    """
    Удаляет задачу автозапуска из Планировщика задач Windows.
    """
    try:
        cmd = ['schtasks', '/delete', '/tn', TASK_NAME, '/f']
        res = subprocess.run(cmd, startupinfo=get_startupinfo(), capture_output=True, text=True, errors='ignore')
        return res.returncode == 0
    except Exception:
        return False

if __name__ == '__main__':
    # Тест работы автозапуска
    print("Автозапуск включен?", is_autostart_enabled())
    if not is_autostart_enabled():
        print("Включаем автозапуск...")
        success = enable_autostart()
        print("Результат:", success)
        print("Автозапуск включен?", is_autostart_enabled())
    else:
        print("Отключаем автозапуск...")
        success = disable_autostart()
        print("Результат:", success)
        print("Автозапуск включен?", is_autostart_enabled())
