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

## ПР04 — параметры patrol

Добавлены параметры linear_speed, turn_rate и publish_hz с проверкой диапазонов
и конечности. Неподходящие значения отклоняются до изменения состояния.
Смена частоты заменяет таймер; одновременно работает только один таймер.
Реальные результаты находятся в evidence/pr04/parameters.md.

Сборка: `colcon build --symlink-install --packages-select turtle_bringup patrol`.
После сборки: `source install/setup.bash`.
Запуск симулятора: `ros2 launch turtle_bringup sim.launch.py`.
Запуск ноды: `ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel`.
В обоих терминалах задайте `ROS_DOMAIN_ID=16`.
Проверка: `(cd src/patrol && python3 -m pytest test)`.
Подготовка отчёта с официальным course kit: `python3 tools/prepare_pr04_report.py`.

## ПР05 — launch, QoS и MCAP

Пакет `course_bringup` запускает один глобальный turtlesim и ноды
`/robot_a/patrol`, `/robot_a/pose_relay`, `/robot_a/pose_listener`.
Внутри нод топики относительные. Launch переназначает вход позы в
`/turtle1/pose`, выход команды в `/turtle1/cmd_vel`; сенсорный поток
остаётся `/robot_a/sensor_pose`.

Подготовка в каждом терминале:

```bash
cd ~/robotics_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=16
```

Сборка и тесты:

```bash
colcon build --symlink-install
source install/setup.bash
colcon test --event-handlers console_direct+
colcon test-result --verbose
```

Первый терминал — намеренно несовместимый подписчик, запись выключена:

```bash
ros2 launch course_bringup patrol.launch.py \
  namespace:=robot_a subscriber_reliability:=reliable record:=false
```

Во втором терминале:

```bash
ros2 node list
ros2 topic info /robot_a/sensor_pose --verbose
timeout --signal=INT 4s ros2 topic echo /robot_a/sensor_pose \
  --qos-reliability reliable --once
```

Ожидается таймаут (код 124): издатель best_effort несовместим с
подписчиком reliable. Остановите первый launch через Ctrl+C и запустите:

```bash
ros2 launch course_bringup patrol.launch.py \
  namespace:=robot_a subscriber_reliability:=best_effort record:=false
```

Теперь сообщение приходит:

```bash
ros2 topic echo /robot_a/sensor_pose --qos-reliability best_effort --once
```

Чтобы записать новую демонстрацию, перезапустите launch с `record:=true`
и новым, ещё не существующим каталогом `bag_dir`, например:

```bash
ros2 launch course_bringup patrol.launch.py \
  namespace:=robot_a subscriber_reliability:=best_effort \
  record:=true bag_dir:=/tmp/pr05-demo-bag
```

При record=false recorder не запускается: используется IfCondition.
После Ctrl+C запись завершается и создаётся metadata.yaml.
Готовая проверенная запись уже лежит в `evidence/pr05/bag`.

Для replay остановите живой launch целиком, затем в первом терминале:

```bash
ros2 bag play evidence/pr05/bag --loop \
  --qos-profile-overrides-path config/qos-overrides.yaml
```

Во втором повторите оба профиля на этой же записи:

```bash
timeout --signal=INT 4s ros2 topic echo /robot_a/sensor_pose \
  --qos-reliability reliable --once
ros2 topic echo /robot_a/sensor_pose --qos-reliability best_effort --once
ros2 bag info evidence/pr05/bag
```

При replay rosbag публикует сохранённую позу; запуск черепахи не требуется.
Файл config/qos-overrides.yaml задаёт издателю replay best_effort.
Один bag содержит один поток /robot_a/sensor_pose. Версии кода и аргументы
запуска записаны в отчёте и логах отдельно от MCAP.

Автоматический опыт `python3 tools/check_pr05_runtime.py` использует
изолированный ROS_DOMAIN_ID=118 и offscreen turtlesim. Он отказывается
перезаписывать уже существующую запись: перед новым опытом сохраните
или переименуйте предыдущую. Реальные доказательства: evidence/pr05/.

Проверка отчёта:

```bash
python3 .course-kit/v1/tools/check_practice.py PR05 --submission .
```

## ПР06 — модель, координаты и QoS tf

Пакет `course_description`, Xacro: `src/course_description/urdf/vehicle.urdf.xacro`.
Размеры взяты из course kit v1-w08: база 0.8 м, колея 0.62 м, радиус 0.12 м.
Оси REP-103: x вперёд, y влево, z вверх. Ветку `pr06-defect` использовать
только для демонстрации: у лидара неверный parent `camera_link`.

```bash
cd ~/robotics_ws
git switch pr06
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select course_description
source install/setup.bash
export ROS_DOMAIN_ID=16
ros2 launch course_description display.launch.py
```

RViz: Fixed Frame=`base_link`, RobotModel и TF уже включены конфигурацией.
Фиксированные сенсоры видны сразу. Для колёс и рулевых звеньев во втором
терминале с тем же окружением опубликуйте положения:

```bash
ros2 topic pub -r 10 /joint_states sensor_msgs/msg/JointState \
  '{header: auto, name: [front_left_steering_joint, front_right_steering_joint, front_left_wheel_joint, front_right_wheel_joint, rear_left_wheel_joint, rear_right_wheel_joint], position: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}'
ros2 run tf2_ros tf2_echo base_link lidar_link
```

Остановите публикацию через Ctrl+C перед следующей командой. Ожидаемое
положение лидара: `(0.28, 0, 0.38)` м. На дефектной ветке offset складывается
с offset камеры и даёт `(0.56, 0, 0.76)`. `check_urdf` принимает оба дерева,
а `test_sensor_parents` обнаруживает смысловую ошибку.

```bash
ros2 topic info /tf_static --verbose
ros2 topic echo /tf_static --once --qos-durability transient_local --qos-reliability reliable
timeout 4 ros2 topic echo /tf_static --once --qos-durability volatile --qos-reliability reliable
# Последняя команда завершается с 124: поздний volatile не читает историю.
xacro src/course_description/urdf/vehicle.urdf.xacro > /tmp/vehicle.urdf
check_urdf /tmp/vehicle.urdf
colcon test --packages-select course_description
colcon test-result --test-result-base build/course_description --verbose
python3 .course-kit/v1/tools/check_practice.py PR06 --submission .
```

Полный повтор эксперимента с остановленными пользовательскими launch:
`python3 tools/check_pr06_runtime.py` (отдельный домен 119, перезаписывает
только evidence ПР06). Результаты: `evidence/pr06/`.

## ПР07 — Gazebo, мост и адаптеры

Исходный мир и модель скопированы из официального kit v1-w08, SHA256 и
изменения перечислены в `src/course_simulation/KIT_VERSION`. Модель содержит
одного робота; дополнительный spawn не нужен. IMU изменён со 100 на 50 Гц.
Используется установленная Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic 8.15.0;
новый нормативный baseline kit Lyrical/Jetty здесь не запускался.

### Сборка и запуск

```bash
cd ~/robotics_ws
git switch pr07
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-up-to course_simulation
source install/setup.bash
export ROS_DOMAIN_ID=16
ros2 launch course_simulation simulation.launch.py headless:=true namespace:=robot_a
```

Launch остаётся активным. В нём один Gazebo, один мост, robot_state_publisher,
drive_adapter и odom_adapter. Ресурсы берутся из установленного share, путь к
моделям добавляется автоматически с сохранением GZ_SIM_RESOURCE_PATH.
`headless:=true` передаёт `-s -r --headless-rendering` для OGRE2/EGL.
Для программного рендеринга при проблемах GPU перед launch можно выполнить:

```bash
export LIBGL_ALWAYS_SOFTWARE=1
export EGL_PLATFORM=surfaceless
```

Во втором терминале подключите те же source и ROS_DOMAIN_ID, затем:

```bash
ros2 topic echo /clock --once
ros2 topic info /vehicle/imu --verbose
ros2 topic echo /vehicle/scan --once --field header --qos-reliability best_effort
ros2 run course_simulation test_drive --ros-args -p use_sim_time:=true -p speed:=0.3 -p steering:=0.15
```

Источник test_drive публикует свежий stamp из /clock. Ctrl+C останавливает
источник; через 0.25 с симуляционного времени watchdog выдаёт нулевой Twist.
Чтобы явно отправлять нулевую команду, запустите тот же источник с speed:=0.0.
В третьем терминале, пока источник работает:

```bash
ros2 topic echo /vehicle/gz_cmd_vel --once
gz topic -e -t /model/course_ackermann/cmd_vel -n 1
ros2 topic echo /vehicle/odom --once
ros2 run tf2_ros tf2_echo odom base_link --ros-args -p use_sim_time:=true
```

Для speed=0.3 и steering=0.15 ожидаются linear.x=0.3 и
angular.z=0.3*tan(0.15)/0.8. Адаптер ограничивает скорость [0,1.2], угол
[-0.45,0.45]; нечисловая или старая команда немедленно сбрасывает выход и
сохранённую команду. /drive/raw не связан с мостом.

### Дефект и владельцы tf

Остановите исправный launch, затем запустите один экземпляр с копией YAML:

```bash
ros2 launch course_simulation simulation.launch.py headless:=true \
  bridge_config:=$PWD/src/course_simulation/config/bridge-defect.yaml
```

В нём опечатка /vehicle/imu_typo на стороне Gazebo. `ros2 topic info -v
/vehicle/imu` всё ещё показывает издателя; `timeout 4 ros2 topic echo
/vehicle/imu --once --qos-reliability best_effort` завершается с 124.
При этом `gz topic -e -t /vehicle/imu -n 1` читает исходный сенсор.
После Ctrl+C перезапустите обычный launch с bridge.yaml. Второй мост
одновременно не запускайте.

Исходная одометрия: /vehicle/odom_gz, course_ackermann/odom →
course_ackermann/base_link. Единственный odom_adapter сохраняет stamp, pose,
twist и covariance, меняет frames на odom → base_link, публикует /vehicle/odom
и совпадающий /tf. robot_state_publisher владеет фиксированными связями сенсоров;
динамические колёсные связи публикуются им только при joint_states. Наличие
двух издателей топика /tf допустимо: у каждого ребра один владелец.

### Запись для ПР08 и проверки

Готовая проверенная запись сохранена локально в fixtures/pr07-sensors.
Её MCAP исключён из Git; метаданные, число сообщений и SHA256 находятся в
evidence/pr07. Используйте этот bag для ПР08 без повторного odom_adapter.
Для новой записи задайте другой, ещё не существующий каталог:

```bash
ros2 bag record -s mcap --use-sim-time -o /tmp/pr07-demo-bag --topics \
  /vehicle/camera/image_raw /vehicle/scan /vehicle/imu /vehicle/odom /tf /tf_static /clock
# Через >=30 секунд именно симуляционного времени: Ctrl+C, затем
ros2 bag info /tmp/pr07-demo-bag
colcon test --packages-select course_simulation
colcon test-result --test-result-base build/course_simulation --verbose
python3 .course-kit/v1/tools/check_practice.py PR07 --submission .
```

Скрипт `python3 tools/check_pr07_runtime.py` повторяет реальный эксперимент
в домене 120 и отдельном GZ_PARTITION, проверяет путь команды и физическую
позу корпуса, QoS, отказы, tf и записывает >=30 секунд симуляции. Он отказывается
перезаписывать существующий fixtures/pr07-sensors. Сначала сохраните старый
каталог под другим именем, если действительно требуется повторить запись.
Измеренные частоты сравниваются с update_rate через stamp и real-time factor;
частоты по часам компьютера зависят от рендера и нагрузки.
