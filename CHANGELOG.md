
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
 
## [0.2.0] - 2024-08-13
  
В версии 0.2.0 добавлены правки Сообщества, связанные с корректной работой с флеш-памятью, находящейся в режимах QPI и XIP
 
### Добавлено
 
- [Update mik32_spifi.py](https://github.com/MikronMIK32/mik32-uploader/commit/1201ab7228b5b0f5a0b58b71933204b6e2bae0f6)
  Добавлен программный сброс микросхемы флеш-памяти из режимов QPI и XIP, чтение и печать JEDEC ID
 
### Изменено
  
- [Update mik32_spifi.py](https://github.com/MikronMIK32/mik32-uploader/commit/1201ab7228b5b0f5a0b58b71933204b6e2bae0f6)
  Убрано отключение Quad SPI режима после прошивки флеш-памяти
 
### Исправлено
 
- [Update mikron-link.cfg](https://github.com/MikronMIK32/mik32-uploader/commit/094a94276878d72564566a1481b6cddccf1e4b81)
  Заменена устаревшая команда и добавлена отсутствующая скорость по-умолчанию для конфигурации отладчика Программатор MIK32
 
## [0.1.0] - 2024-07-17
 
 Первоначальный выпуск. До этого коммита версия программы не менялась и не отслеживалась.
 
### Добавлено
 
### Изменено
 
### Исправлено
 