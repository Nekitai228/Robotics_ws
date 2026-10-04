# Практические работы по ROS 2

Работа выполняется в WSL2: Ubuntu 24.04, ROS 2 Jazzy. Для опыта нужны три Bash-терминала в одной среде. Ниже используются домены 16 и 17; если преподаватель назначил другую пару, замените оба значения. Исходные результаты этого прогона находятся в [evidence/pr01/graph.md](evidence/pr01/graph.md).

## Подготовка

В каждом терминале:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=16
```

В терминале C перейдите в корень этого репозитория:

```bash
cd ~/robotics_ws
mkdir -p evidence/pr01
ros2 doctor --report > evidence/pr01/doctor.txt 2>&1
```

## Исправный граф

Терминал A:

```bash
ros2 run turtlesim turtlesim_node
```

Терминал B:

```bash
ros2 run turtlesim turtle_teleop_key
```

Стрелки управляют черепахой, когда фокус ввода находится в терминале B. Терминал C:

```bash
ros2 node list --no-daemon --spin-time 2
ros2 topic list -t
ros2 node info /turtlesim
ros2 topic type /turtle1/pose
POSE_TYPE=$(ros2 topic type /turtle1/pose)
ros2 topic echo /turtle1/pose --once
ros2 topic hz /turtle1/pose
```

Измеряйте частоту не меньше 10 секунд, затем остановите последнюю команду через Ctrl+C.

## Разрыв связи

Оставьте симулятор в A работающим в домене 16. В B остановите teleop через Ctrl+C и запустите его заново:

```bash
export ROS_DOMAIN_ID=17
ros2 run turtlesim turtle_teleop_key
```

В C:

```bash
export ROS_DOMAIN_ID=17
ros2 node list --no-daemon --spin-time 2
timeout 5s ros2 topic echo /turtle1/pose "$POSE_TYPE" --once \
  > evidence/pr01/pose-broken.txt 2>&1
printf 'exit=%s\n' "$?"
```

Ожидаются /teleop_turtle без /turtlesim, отсутствие позы и exit=124.

## Восстановление

В B остановите teleop через Ctrl+C и перезапустите его в исходном домене:

```bash
export ROS_DOMAIN_ID=16
ros2 run turtlesim turtle_teleop_key
```

В C повторите тот же тест:

```bash
export ROS_DOMAIN_ID=16
ros2 node list --no-daemon --spin-time 2
timeout 5s ros2 topic echo /turtle1/pose "$POSE_TYPE" --once \
  > evidence/pr01/pose-fixed.txt 2>&1
printf 'exit=%s\n' "$?"
```

Ожидаются обе ноды, полученная поза и exit=0. Наблюдения и объяснение приведены в graph.md.

## Проверка отчёта

Скачайте course kit выпуска v1-w03 по инструкции курса, проверьте SHA-256 и распакуйте в .course-kit/v1. Затем:

```bash
python3 -m json.tool evidence/pr01/environment.json > /dev/null
python3 -m json.tool evidence/pr01/report.json > /dev/null
python3 .course-kit/v1/tools/check_practice.py PR01 --submission .
```

Для ПР01 собственный ROS-пакет и сборка colcon не требуются.

## ПР02 — пакет turtle_bringup

Работа выполняется в WSL2 с Ubuntu 24.04 и ROS 2 Jazzy. Исходники
пакета находятся в `src/turtle_bringup/`, результаты — в `evidence/pr02/`.

### Сборка

Из корня репозитория в Bash:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select turtle_bringup
source install/setup.bash
ros2 pkg prefix turtle_bringup
```

Установленный launch-файл находится в
`share/turtle_bringup/launch/sim.launch.py`.

### Запуск

В первом терминале:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=16
ros2 launch turtle_bringup sim.launch.py
```

Во втором терминале с тем же `ROS_DOMAIN_ID`:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=16
ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'
ros2 topic echo /turtle1/pose --once
```

Для воспроизведения сбоя отправьте тот же Twist в `/cmd_vel`.
У этого топика нет подписчика turtlesim. Подробные команды, выводы
и объяснение исправления находятся в `evidence/pr02/commands.md`,
типы сообщений — в `evidence/pr02/types.md`.

### Локальная проверка

```bash
python3 -m py_compile src/turtle_bringup/launch/sim.launch.py
python3 .course-kit/v1/tools/check_practice.py PR02 --submission .
```

## ПР03 — нода patrol

Пакет patrol получает /turtle1/pose и публикует Twist по таймеру 0.1 с.
До получения позы команда нулевая, после — linear.x=0.5, angular.z=0.3.

Сборка: `colcon build --symlink-install --packages-select turtle_bringup patrol`.
После сборки выполните `source install/setup.bash`.

Тесты: `(cd src/patrol && python3 -m pytest test)`.

В первом терминале запустите `ros2 launch turtle_bringup sim.launch.py`.
Во втором: `ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel`.
Оба терминала должны использовать `ROS_DOMAIN_ID=16`.

Запуск patrol без remap воспроизводит ошибку имени топика.
Выводы опытов и объяснения находятся в `evidence/pr03/demo.md`.
