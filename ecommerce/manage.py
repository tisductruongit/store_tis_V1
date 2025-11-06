#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')
    # NEW: đọc từ settings để tự gắn addr:port và --insecure nếu cần
    try:
        from django.conf import settings
    except Exception:
        from django.core.management import execute_from_command_line
        execute_from_command_line(sys.argv)
        return

    # Nếu chạy đúng lệnh "python manage.py runserver" (không kèm đối số addr:port)
    if len(sys.argv) == 2 and sys.argv[1] == 'runserver':
        addrport = getattr(settings, 'RUNSERVER_DEFAULT_ADDRPORT', None)
        if addrport:
            sys.argv.append(addrport)

        # Nếu muốn tự thêm --insecure khi DEBUG=False (để phục vụ static khi dev)
        auto_insecure = getattr(settings, 'RUNSERVER_AUTO_INSECURE', False)
        if auto_insecure and not getattr(settings, 'DEBUG', True):
            if '--insecure' not in sys.argv:
                sys.argv.append('--insecure')

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
