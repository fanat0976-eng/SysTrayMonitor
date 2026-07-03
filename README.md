# SysTray Monitor

> Иконка в трее: CPU, RAM, Disk, Ollama статус

## Что это

Мини-монитор системы в системном трее Windows. Показывает:
- **CPU** — загрузка (зелёный <50%, жёлтый <80%, красный >80%)
- **RAM** — использовано / всего
- **Disk C:** — свободное место
- **Ollama** — статус (ON/OFF) + количество моделей

Обновляется каждые 3 секунды.

## Запуск

```bat
start.bat
```

Или:

```bash
python monitor.py
```

## Зависимости

```bash
pip install pystray psutil Pillow httpx
```

## Использование

- **Иконка в трее** — цвет = загрузка CPU
- **Tooltip** — наведи мышку → полная статистика
- **Клик правой кнопкой** — меню с詳細ами + Exit
- **Exit** — закрыть монитор

## Структура

```
SysTrayMonitor/
├── monitor.py    # Основной скрипт
├── start.bat     # Windows launcher
└── README.md
```
