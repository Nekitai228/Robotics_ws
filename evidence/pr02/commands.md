# ПР02 — команды и проверка запуска

## Три команды Linux

1. `cd src` — перешёл из корня workspace в каталог исходников.
   Результат: приглашение терминала показывало `~/robotics_ws/src`.

2. `ls -la src` — просмотрел содержимое каталога исходников.
   Результат: до создания пакета каталог был пустым; после создания
   появился `src/turtle_bringup`.

3. `mkdir -p evidence/pr02` — создал каталог для результатов ПР02.
   Результат: в нём сохранены `build-empty.txt` и `build.txt`.

Оператор `>` записывает stdout команды в файл, заменяя прежнее содержимое.
Оператор `|` передаёт stdout первой команды на вход следующей.
В сборке `2>&1 | tee evidence/pr02/build.txt` оба потока одновременно
показывались в терминале и сохранялись в файл.

`source /opt/ros/jazzy/setup.bash` меняет окружение текущего Bash:
после него доступны команды и пакеты ROS 2. Запуск `ros2 launch ...`
создаёт отдельный процесс; он не заменяет окружение текущего Bash.

## Создание и сборка пакета

Пакет создан командой:

```bash
ros2 pkg create --build-type ament_python --license Apache-2.0 \
  turtle_bringup --dependencies launch launch_ros turtlesim
```

Первая сборка без launch-файла:

```bash
set -o pipefail
colcon build --symlink-install --packages-select turtle_bringup \
  2>&1 | tee evidence/pr02/build-empty.txt
```

Результат: `1 package finished`, код выхода 0.
После `source install/setup.bash` команда
`ros2 pkg prefix turtle_bringup` вернула
`/home/iakup/robotics_ws/install/turtle_bringup`.
Сборка и `source` установили и обнаружили пакет, но не запустили ноду.

После добавления `launch/sim.launch.py` и записи в `setup.py`
пакет пересобран той же командой с логом `evidence/pr02/build.txt`.
Результат: `1 package finished`, код выхода 0.
В установленном пакете найден `share/turtle_bringup/launch/sim.launch.py`.

## Запуск и остановка

```bash
ros2 launch turtle_bringup sim.launch.py
ros2 node list --no-daemon --spin-time 2
```

Во время работы launch список нод содержал `/turtlesim`.
После `Ctrl+C` повторная проверка больше не показывала `/turtlesim`.

## Исправная доставка команды

Тип позы: `turtlesim/msg/Pose`.
Тип команды движения: `geometry_msgs/msg/Twist`.
Начальная поза: x=5.5444, y=5.5444, theta=0.0.

```bash
ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'
ros2 topic echo /turtle1/pose --once
```

После команды поза стала x=6.5093, y=5.7970, theta=0.5040.
Положение и угол изменились: сообщение дошло до симулятора.
После одиночной публикации скорости снова были равны нулю.

## Сбой: неверное имя топика

```bash
ros2 topic pub --rate 1 --wait-matching-subscriptions 0 \
  /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'
ros2 topic info /cmd_vel --verbose
ros2 topic info /turtle1/cmd_vel --verbose
```

У `/cmd_vel` был 1 издатель и 0 подписчиков.
У `/turtle1/cmd_vel` было 0 издателей и 1 подписчик — `turtlesim`.
Черепаха стояла. Тип сообщения совпадал, но полное имя топика
не совпадало с именем, на которое подписан симулятор.

## Исправление и повторная проверка

Изменено только имя `/cmd_vel` на `/turtle1/cmd_vel`:

```bash
ros2 topic pub --rate 1 --wait-matching-subscriptions 0 \
  /turtle1/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'
ros2 topic info /turtle1/cmd_vel --verbose
```

Теперь у `/turtle1/cmd_vel` 1 издатель и 1 подписчик.
После публикации поза изменилась до x=3.8012, y=6.5499,
theta=-1.0544. Издатель остановлен через `Ctrl+C`, затем черепаха
остановилась. Обнаружение издателя само по себе не означает доставку:
для неё нужен подходящий подписчик на том же полном имени топика.
