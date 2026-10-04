# ПР03 — подписка, таймер и remap

Пакет patrol создан рядом с turtle_bringup.
Минимальная нода была собрана и обнаружена как /patrol.

Подписка на /turtle1/pose сохраняет последнюю позу.
Таймер с периодом 0.1 с публикует Twist в относительный cmd_vel.
До первой позы команда нулевая. После получения позы:
linear.x = 0.5, angular.z = 0.3, остальные поля равны нулю.

Выбор команды вынесен в функцию command_from_pose.
Тесты проверяют отсутствие позы и обычное сообщение Pose.

## Опыт и исправление

Без turtlesim поза отсутствовала и публиковалась нулевая команда.
После запуска turtlesim нода получала позу, но черепаха стояла:
издатель использовал /cmd_vel, подписчик — /turtle1/cmd_vel.

Исправление выполнено при запуске:
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel

После remap издатель и подписчик соединены, черепаха двигалась.
Частота команды измерялась командой ros2 topic hz в течение 10 секунд.
Фактические выводы сохранены ниже.

## Роли функций и остановка

rclpy.init создаёт контекст ROS 2.
rclpy.spin обрабатывает поступающие сообщения и события таймера.
Callback подписки сохраняет позу, callback таймера публикует команду.

Ctrl+C прерывает spin. Затем нода уничтожается и контекст закрывается.
Остановка издателя не является мгновенной командой торможения.
После прекращения команд turtlesim останавливается по своему таймауту.

## Команда до получения позы

```text
linear:
  x: 0.0
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: 0.0
---
```

## Связи ноды до remap

```text
/patrol
  Subscribers:
    /turtle1/pose: turtlesim/msg/Pose
  Publishers:
    /cmd_vel: geometry_msgs/msg/Twist
    /parameter_events: rcl_interfaces/msg/ParameterEvent
    /rosout: rcl_interfaces/msg/Log
  Service Servers:
    /patrol/describe_parameters: rcl_interfaces/srv/DescribeParameters
    /patrol/get_parameter_types: rcl_interfaces/srv/GetParameterTypes
    /patrol/get_parameters: rcl_interfaces/srv/GetParameters
    /patrol/get_type_description: type_description_interfaces/srv/GetTypeDescription
    /patrol/list_parameters: rcl_interfaces/srv/ListParameters
    /patrol/set_parameters: rcl_interfaces/srv/SetParameters
    /patrol/set_parameters_atomically: rcl_interfaces/srv/SetParametersAtomically
  Service Clients:

  Action Servers:

  Action Clients:
```

## Команда в неверном топике

```text
linear:
  x: 0.5
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: 0.3
---
```

## Неверный топик

```text
Type: geometry_msgs/msg/Twist

Publisher count: 1

Node name: patrol
Node namespace: /
Topic type: geometry_msgs/msg/Twist
Topic type hash: RIHS01_9c45bf16fe0983d80e3cfe750d6835843d265a9a6c46bd2e609fcddde6fb8d2a
Endpoint type: PUBLISHER
GID: 01.0f.a3.ab.30.04.6e.d5.00.00.00.00.00.00.14.03
QoS profile:
  Reliability: RELIABLE
  History (Depth): UNKNOWN
  Durability: VOLATILE
  Lifespan: Infinite
  Deadline: Infinite
  Liveliness: AUTOMATIC
  Liveliness lease duration: Infinite

Subscription count: 0
```

## Топик черепахи до remap

```text
Type: geometry_msgs/msg/Twist

Publisher count: 0

Subscription count: 1

Node name: turtlesim
Node namespace: /
Topic type: geometry_msgs/msg/Twist
Topic type hash: RIHS01_9c45bf16fe0983d80e3cfe750d6835843d265a9a6c46bd2e609fcddde6fb8d2a
Endpoint type: SUBSCRIPTION
GID: 01.0f.a3.ab.06.04.f9.fa.00.00.00.00.00.00.1d.04
QoS profile:
  Reliability: RELIABLE
  History (Depth): UNKNOWN
  Durability: VOLATILE
  Lifespan: Infinite
  Deadline: Infinite
  Liveliness: AUTOMATIC
  Liveliness lease duration: Infinite
```

## Поза до remap

```text
x: 5.544444561004639
y: 5.544444561004639
theta: 0.0
linear_velocity: 0.0
angular_velocity: 0.0
---
```

## Повторная поза до remap

```text
x: 5.544444561004639
y: 5.544444561004639
theta: 0.0
linear_velocity: 0.0
angular_velocity: 0.0
---
```

## Связи ноды после remap

```text
/patrol
  Subscribers:
    /turtle1/pose: turtlesim/msg/Pose
  Publishers:
    /parameter_events: rcl_interfaces/msg/ParameterEvent
    /rosout: rcl_interfaces/msg/Log
    /turtle1/cmd_vel: geometry_msgs/msg/Twist
  Service Servers:
    /patrol/describe_parameters: rcl_interfaces/srv/DescribeParameters
    /patrol/get_parameter_types: rcl_interfaces/srv/GetParameterTypes
    /patrol/get_parameters: rcl_interfaces/srv/GetParameters
    /patrol/get_type_description: type_description_interfaces/srv/GetTypeDescription
    /patrol/list_parameters: rcl_interfaces/srv/ListParameters
    /patrol/set_parameters: rcl_interfaces/srv/SetParameters
    /patrol/set_parameters_atomically: rcl_interfaces/srv/SetParametersAtomically
  Service Clients:

  Action Servers:

  Action Clients:
```

## Топик после remap

```text
Type: geometry_msgs/msg/Twist

Publisher count: 1

Node name: patrol
Node namespace: /
Topic type: geometry_msgs/msg/Twist
Topic type hash: RIHS01_9c45bf16fe0983d80e3cfe750d6835843d265a9a6c46bd2e609fcddde6fb8d2a
Endpoint type: PUBLISHER
GID: 01.0f.a3.ab.a6.04.ce.1f.00.00.00.00.00.00.14.03
QoS profile:
  Reliability: RELIABLE
  History (Depth): UNKNOWN
  Durability: VOLATILE
  Lifespan: Infinite
  Deadline: Infinite
  Liveliness: AUTOMATIC
  Liveliness lease duration: Infinite

Subscription count: 1

Node name: turtlesim
Node namespace: /
Topic type: geometry_msgs/msg/Twist
Topic type hash: RIHS01_9c45bf16fe0983d80e3cfe750d6835843d265a9a6c46bd2e609fcddde6fb8d2a
Endpoint type: SUBSCRIPTION
GID: 01.0f.a3.ab.06.04.f9.fa.00.00.00.00.00.00.1d.04
QoS profile:
  Reliability: RELIABLE
  History (Depth): UNKNOWN
  Durability: VOLATILE
  Lifespan: Infinite
  Deadline: Infinite
  Liveliness: AUTOMATIC
  Liveliness lease duration: Infinite
```

## Команда после remap

```text
linear:
  x: 0.5
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: 0.3
---
```

## Измеренная частота

```text
WARNING: topic [/turtle1/cmd_vel] does not appear to be published yet
average rate: 9.998
	min: 0.100s max: 0.100s std dev: 0.00016s window: 11
average rate: 9.998
	min: 0.100s max: 0.100s std dev: 0.00019s window: 21
average rate: 9.999
	min: 0.100s max: 0.100s std dev: 0.00018s window: 31
average rate: 9.999
	min: 0.100s max: 0.100s std dev: 0.00018s window: 42
average rate: 9.999
	min: 0.099s max: 0.101s std dev: 0.00020s window: 52
average rate: 9.999
	min: 0.099s max: 0.101s std dev: 0.00020s window: 63
```

## Поза после движения

```text
x: 4.746150493621826
y: 5.745884418487549
theta: -0.4991559088230133
linear_velocity: 0.5
angular_velocity: 0.30000001192092896
---
```

## Поза после остановки patrol

```text
x: 4.763648986816406
y: 8.685683250427246
theta: -2.6591413021087646
linear_velocity: 0.0
angular_velocity: 0.0
---
```

## Ноды после остановки patrol

```text
/turtlesim
```

