# ПР01 — граф ROS 2 и проверка доменов

## Среда и запуск

Среда: WSL2, Ubuntu 24.04, ROS 2 Jazzy.
Домен исправной системы: `ROS_DOMAIN_ID=16`.
Другой домен для опыта: `ROS_DOMAIN_ID=17`.

В терминале A:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=16
ros2 run turtlesim turtlesim_node
```

Нода `/turtlesim` запустилась, появилось окно с черепахой.

В терминале B:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=16
ros2 run turtlesim turtle_teleop_key
```

Черепаха двигалась при нажатии стрелок

## Исправный граф

В терминале C, также в домене 16:

```bash
ros2 node list --no-daemon --spin-time 2
```

Вывод:

```text
/teleop_turtle
/turtlesim
```

`/turtlesim` — симулятор черепахи. `/teleop_turtle` — управление с клавиатуры.

```bash
ros2 topic list -t
```

Вывод:

```text
/parameter_events [rcl_interfaces/msg/ParameterEvent]
/rosout [rcl_interfaces/msg/Log]
/turtle1/cmd_vel [geometry_msgs/msg/Twist]
/turtle1/color_sensor [turtlesim/msg/Color]
/turtle1/pose [turtlesim/msg/Pose]
```

`/turtle1/cmd_vel` передаёт команды движения симулятору.
`/turtle1/pose` публикует положение черепахи.
`/turtle1/color_sensor` публикует данные датчика цвета.

Команда `ros2 node info /turtlesim` показала, что симулятор подписан на
`/turtle1/cmd_vel` и публикует `/turtle1/pose` и
`/turtle1/color_sensor`.

```bash
ros2 topic type /turtle1/pose
```

Вывод: `turtlesim/msg/Pose`.

```bash
ros2 topic echo /turtle1/pose --once
```

Получена поза:

```text
x: 6.446971416473389
y: 6.638950824737549
theta: 0.527999997138977
linear_velocity: 0.0
angular_velocity: 0.0
```

```bash
ros2 topic hz /turtle1/pose
```

Устойчивая измеренная частота — около 62,5 Гц. Измерение продолжалось
20 с.
В начале команда кратко вывела предупреждение об отсутствии публикации,
после обнаружения издателя появились регулярные измерения. Позже в выводе
встречается отрицательный интервал `-0.965 s` и частота выше 64 Гц;
этот участок не использую как оценку нормальной частоты.

## Разрыв связи: домен 17

Симулятор в A оставлен работающим в домене 16. Управление в B остановлено
через Ctrl+C и запущено заново с `ROS_DOMAIN_ID=17`. В C также установлен
домен 17, после чего выполнено:

```bash
ros2 node list --no-daemon --spin-time 2
timeout 5s ros2 topic echo /turtle1/pose "$POSE_TYPE" --once \
  > evidence/pr01/pose-broken.txt 2>&1
printf 'exit=%s\n' "$?"
```

Наблюдение:
```text
/teleop_turtle
```
Черепаха не двигалась от стрелок.
Код завершения: exit=124.
За 5 секунд поза не поступила.

## Восстановление: домен 16

Управление в B снова остановлено и запущено с `ROS_DOMAIN_ID=16`.
В C установлен домен 16 и повторена та же проверка:

```bash
ros2 node list --no-daemon --spin-time 2
timeout 5s ros2 topic echo /turtle1/pose "$POSE_TYPE" --once \
  > evidence/pr01/pose-fixed.txt 2>&1
printf 'exit=%s\n' "$?"
```

Наблюдение: 
```text
/teleop_turtle
/turtlesim
```
Получена поза:
```text
x: 2.051177501678467
y: 9.241907119750977
theta: 2.9711852073669434
linear_velocity: 0.0
angular_velocity: 0.0
---
```
Код завершения: exit=0
Черепаха двигалась от стрелок.

## Вывод

Участники ROS 2 обнаруживают друг друга в одном домене. Когда симулятор
работал в домене 16, а управление и проверяющий подписчик — в домене 17,
они не обнаруживали симулятор и сообщение о позе не приходило. После
возврата в домен 16 связь восстановилась. `ROS_DOMAIN_ID` считывается
при запуске ноды, поэтому после изменения переменной управление нужно
было остановить и запустить заново.
