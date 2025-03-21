
# Журнал изменений
Все заметные изменения в проекте будут задокументированы в этом файле.

## Типы изменений
- **Добавлено** — для новых функций.
- **Изменено** — для изменений в существующей функциональности.
- **Устарело** — для функций, которые скоро будут удалены.
- **Удалено** — для удалённых на данный момент.
- **Исправлено** — для любых исправлений багов.
- **Безопасность** — на случай уязвимостей.

## [Невыпущенное] - yyyy-mm-dd
 
В этот раздел следует заносить изменения, которые ещё не были добавлены в новый релиз.
 
### Добавлено
  
### Изменено
 
### Исправлено

### Удалено

## [v0.3.3] - 2025-03-17
 
### Исправлено
- Добавлен id для TCB блока МК, Добавление нестандартного CSR-регистра MCOUNTEN (@cryptozoy)
- Ошибка записи eeprom при boot=1 (ram)
- Выбор порта аргументом --openocd-port

## [v0.3.2] - 2024-12-28
 
### Добавлено
- Базовая обработка ошибок
- Сброс внешней флеш-памяти из всех режимов в стандартный Single SPI (@cryptozoy)
- Остановка прошивки, если загрузка данных не удалась
 
### Исправлено
- Ошибка в функции прошивки SPIFI
- Ошибка при настройке тактирования - не происходило отключение блоков

## [v0.3.1] - 2024-11-14
 
### Добавлено
- Добавлен скрипт поддержки программатора на основе FT2232D
- Добавлено отключение прерываний ядра перед запуском драйвера для прошивки

## [v0.3.0] - 2024-11-05
 
Релиз поддержки платы START-MIK32-V1.
Добавлена прошивка с использованием драйвера, можно отключить с использованием
аргумента --no-driver
 
### Добавлено
 - Загрузка прошивки с использованием драйвера в ОЗУ
 - Конфигурация для программатора платы START-MIK32-V1

### Изменено
 - Драйверы, смещения и маски регистров и битовых полей перенесены в модуль mik32_debug_hal

### Исправлено
 - Результат прошивки не выводился в коде возврата

### Удалено
 - Краткий вариант аргумента --boot-mode

## [v0.2.1] - 2024-09-10
 
В версии 0.2.1 исправлены пути конфигурационных файлов по умолчанию, файлов лога OpenOCD и добавлен скрипт сборки
исполняемого файла
 
### Добавлено
- Добавлен скрипт сборки исполняемого файла
 
### Исправлено
- Исправлены пути конфигурационных файлов по умолчанию, файлов лога OpenOCD
 
## [v0.2.0] - 2024-08-13
  
В версии 0.2.0 добавлены правки Сообщества, связанные с корректной работой с флеш-памятью, находящейся в режимах QPI и XIP
 
### Добавлено
 
- [Update mik32_spifi.py](https://github.com/MikronMIK32/mik32-uploader/commit/1201ab7228b5b0f5a0b58b71933204b6e2bae0f6)
  Добавлен программный сброс микросхемы флеш-памяти из режимов QPI и XIP, чтение и печать JEDEC ID (@cryptozoy)
 
### Изменено
  
- [Update mik32_spifi.py](https://github.com/MikronMIK32/mik32-uploader/commit/1201ab7228b5b0f5a0b58b71933204b6e2bae0f6)
  Убрано отключение Quad SPI режима после прошивки флеш-памяти (@cryptozoy)
 
### Исправлено
 
- [Update mikron-link.cfg](https://github.com/MikronMIK32/mik32-uploader/commit/094a94276878d72564566a1481b6cddccf1e4b81)
  Заменена устаревшая команда и добавлена отсутствующая скорость по-умолчанию для конфигурации отладчика Программатор MIK32 (@cryptozoy)
 
## [v0.1.0] - 2024-07-17
 
 Первоначальный выпуск. До этого коммита версия программы не менялась и не отслеживалась.
 
### Добавлено
 
### Изменено
 
### Исправлено
 