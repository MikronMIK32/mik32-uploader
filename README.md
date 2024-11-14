# Скрипт программирования памяти MIK32

Скрипт предназначен для записи программы в ОЗУ, EEPROM и внешнюю flash память, 
подключенную по интерфейсу SPIFI.

## Предварительные требования

Требуется операционная система Windows версии >= 7 или macOS версии >= 10.9 
или Linux.

Требуется версия Python >= 3.8 (https://www.python.org/downloads/).

Требуется версия OpenOCD >= 0.11.0 
(https://github.com/xpack-dev-tools/openocd-xpack/releases).

## Установка

Необходимо скачать или клонировать репозиторий программы, а также установить 
Python и OpenOCD 0.12.0.

Скрипт по умолчанию ищет исполняемый файл openocd по пути 
openocd\bin\openocd.exe относительно папки со скриптом.

### Установка в PlatformIO

Клонировать ветку репозитория master в директорию `tool-mik32-uploader` в
`~/.platformio/packages/`, либо скачать Source Code последнего релиза и 
распаковать содержимое папки `mik32-uploader-{версия}` в директорию 
`tool-mik32-uploader` в `~/.platformio/packages/`

## Запуск программы

Минимальная команда для запуска:

```
python mik32_upload.py firmware_name.hex
```

Команда для запуска OpenOCD при запуске скрипта:

```
python mik32_upload.py firmware_name.hex --run-openocd --openocd-exec="путь\к\openocd.exe"  --openocd-scripts="путь\к\папке\scripts" --openocd-interface="путь\к\настройкам\отладчика" --openocd-target="путь\к\настройкам\МК"
```

## Описание аргументов

```
positional arguments:
  filepath              Путь к файлу прошивки

optional arguments:
  -h, --help            show this help message and exit
  --run-openocd         Запуск openocd при прошивке МК
  --use-quad-spi        Использование режима QuadSPI при программировании внешней флеш памяти
  --openocd-host OPENOCD_HOST
                        Адрес для подключения к openocd. По умолчанию: 127.0.0.1
  --openocd-port OPENOCD_PORT
                        Порт tcl сервера openocd. По умолчанию: 6666
  --adapter-speed ADAPTER_SPEED
                        Скорость отладчика в кГц. По умолчанию: 500
  --openocd-exec OPENOCD_EXEC
                        Путь к исполняемому файлу openocd. По умолчанию: openocd\bin\openocd.exe
  --openocd-scripts OPENOCD_SCRIPTS
                        Путь к папке scripts. По умолчанию: openocd\share\openocd\scripts
  --openocd-interface OPENOCD_INTERFACE
                        Путь к файлу конфигурации отладчика относительно папки scripts или абсолютный путь. По
                        умолчанию: interface\ftdi\m-link.cfg
  --openocd-target OPENOCD_TARGET
                        Путь к файлу конфигурации целевого контроллера относительно папки scripts. По умолчанию:
                        target\mik32.cfg
  --open-console        Открывать OpenOCD в отдельной консоли
  --boot-mode {undefined,eeprom,ram,spifi}
                        Выбор типа памяти, который отображается на загрузочную область. Если тип не выбран, данные,
                        находящиеся в загрузочной области в hex файле отбрасываются. По умолчанию: undefined
  --log-path LOG_PATH   Путь к файлу журнала. По умолчанию: nul
  --post-action POST_ACTION
                        Команды OpenOCD, запускаемые после прошивки. По умолчанию: reset run
  -t {MIK32V0,MIK32V2}, --mcu-type {MIK32V0,MIK32V2}
                        Выбор микроконтроллера. По умолчанию: MIK32V2
  --no-driver           Отключает прошивку с использованием драйвера в ОЗУ
```

## Принцип работы

Для работы скрипта требуется подключение по JTAG и отладчик, 
поддерживающийся OpenOCD.

Программа принимает образы программы в формате hex и записывает данные 
в память МК через контроллер SPIFI, путем записи команд и настроек 
в регистры блока. Тип памяти и способ записи выбирается по адресу байт 
в hex файле, поэтому требуется правильное расположение секций, 
заданное в ld скрипте.

Скрипт работает через OpenOCD, подключаясь через tcl сервер к уже запущенному 
openocd, подключенному к МК. Скрипт может запустить openocd самостоятельно.

## Сборка в исполняемый файл

Для сборки в исполняемый файл и подготовки релиза используется 
модуль PyInstaller. 
Для его установки выполните команду:

```
pip install -U pyinstaller
```

Затем соберите программу с использованием файла с настройками mik32_upload.spec:

```
pyinstaller mik32_upload.spec
```

В директории `./dist` будет создан каталог `mik32_upload`, содержащий 
исполняемый файл `mik32_upload`, папки `_internal`, `openocd-scripts` и 
`upload-drivers`, а также архив с названием `mik32-uploader-{версия}`.

Для указания версии программы следует изменить значение переменной 
`applicaton_version` в файле `_version.py`. При редактировании файла следует 
сохранять форматирование! Также потребуется изменить номер версии в файле 
`.piopm` uploader'а и `platform.json` платформы для корректной работы системы 
управления пакетами platformio.
