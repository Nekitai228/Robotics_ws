# ПР04 — изменение параметров движения

## Среда и реализация

Ubuntu 24.04, WSL2, ROS 2 Jazzy. Проверено автоматически приложением Codex
на реальных процессах ROS 2 в отдельном домене ROS_DOMAIN_ID=116.
Turtlesim работал с QT_QPA_PLATFORM=offscreen; визуальный показ выполняется
пользователем в обычном домене 16; команды запуска приведены в README.md.

Параметры: linear_speed=0.5 (0–1), turn_rate=0.3 (−1–1),
publish_hz=10.0 (1–30). Значения должны быть конечными числами.
Чистая функция parameter_error проверяет всю предлагаемую конфигурацию.
Callback on-set только проверяет; callback post-set применяет уже принятые
значения. При смене частоты прежний таймер уничтожается перед созданием
нового. При смене скоростей прежний таймер сохраняется.

## Дефект и исправление

Ветка с намеренным дефектом: pr04-defect.
Коммит: `7f51252638a384a0f7803af79f60477939693466`.
В этой версии при проверке запрашиваемая частота подменяется прежней,
поэтому недопустимый ноль проходит проверку. В callback применения
старый таймер уничтожается, а расчёт периода 1/0 вызывает ZeroDivisionError.
Команда установки параметра не получает ответ и завершается по таймауту;
процесс ноды завершается с кодом 1. Это ожидаемый отказ дефектной версии.
Разница сохранена в defect.patch, traceback — в defect-node.txt.

В исправленной версии та же команда с 0.0 отклоняется до применения.
Значение остаётся 5.0, нода жива и поток остаётся около 5 Гц.
Тесты дополнительно проверяют ноль, отрицательные значения, NaN,
бесконечности, границы диапазонов и неизменность таймера/состояния
при отклонении всей заявки с несколькими параметрами.

## Измерения

```text
10 Hz measured: 10.0
5 Hz measured: 5.0
After rejected zero: 5.0 Hz
```

Каждый замер частоты выполнялся отдельной командой ros2 topic hz в течение
10 секунд. Код 124 у измерения означает штатное завершение по таймауту.
На исправной ноде ros2 param set возвращает код 0 даже при отклонении:
фактический результат виден в строке Setting parameter failed.

## Сервис и действие

Запрос сервиса /clear выполняет короткую операцию очистки и возвращает
один ответ. Цель действия /turtle1/rotate_absolute описывает длительный
поворот, для которого предусмотрены обратная связь, результат и отмена.
Собственный IDL и action-сервер не добавлялись.

## Реальные команды и вывод дефектной версии

```text
$ ros2 param get /patrol publish_hz
Double value is: 10.0

exit=0

$ ros2 param set /patrol publish_hz 0.0

exit=124

Deliberate defect process log:
Traceback (most recent call last):
  File "/home/iakup/robotics_ws/install/patrol/lib/patrol/patrol", line 33, in <module>
    sys.exit(load_entry_point('patrol', 'console_scripts', 'patrol')())
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/tmp/robotics-pr04-defect-gmn697ds/src/patrol/patrol/patrol.py", line 84, in main
    rclpy.spin(node)
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/__init__.py", line 247, in spin
    executor.spin_once()
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/executors.py", line 926, in spin_once
    self._spin_once_impl(timeout_sec)
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/executors.py", line 918, in _spin_once_impl
    raise handler.exception()
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/task.py", line 286, in _execute_coroutine_step
    result = coro.send(None)
             ^^^^^^^^^^^^^^^
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/executors.py", line 592, in handler
    await call_coroutine()
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/executors.py", line 531, in _execute
    response = await await_or_execute(srv.callback, request, srv.srv_type.Response())
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/executors.py", line 115, in await_or_execute
    return callback(*args)
           ^^^^^^^^^^^^^^^
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/parameter_service.py", line 117, in _set_parameters_callback
    result = node.set_parameters_atomically([param])
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py", line 839, in set_parameters_atomically
    return self._set_parameters_atomically(parameter_list)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py", line 859, in _set_parameters_atomically
    return self._set_parameters_atomically_common(parameter_list)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py", line 962, in _set_parameters_atomically_common
    self._call_post_set_parameters_callback(parameter_list)
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py", line 1055, in _call_post_set_parameters_callback
    callback(parameter_list)
  File "/tmp/robotics-pr04-defect-gmn697ds/src/patrol/patrol/patrol.py", line 61, in apply_update
    1.0 / candidate['publish_hz'], self.timer_callback,
    ~~~~^~~~~~~~~~~~~~~~~~~~~~~~~
ZeroDivisionError: float division by zero
[ros2run]: Process exited with failure 1
```

## Реальные команды и вывод исправленной версии

```text
$ ros2 param list /patrol
  linear_speed
  publish_hz
  start_type_description_service
  turn_rate
  use_sim_time

exit=0

$ ros2 param get /patrol linear_speed
Double value is: 0.5

exit=0

$ ros2 param get /patrol turn_rate
Double value is: 0.3

exit=0

$ ros2 param get /patrol publish_hz
Double value is: 10.0

exit=0

$ ros2 topic echo /turtle1/pose --once
x: 7.072674751281738
y: 7.8668928146362305
theta: 1.9728000164031982
linear_velocity: 0.5
angular_velocity: 0.30000001192092896
---

exit=0

$ ros2 topic hz /turtle1/cmd_vel
average rate: 10.001
	min: 0.100s max: 0.100s std dev: 0.00020s window: 12
average rate: 10.000
	min: 0.100s max: 0.100s std dev: 0.00016s window: 22
average rate: 9.999
	min: 0.100s max: 0.100s std dev: 0.00015s window: 32
average rate: 10.000
	min: 0.100s max: 0.100s std dev: 0.00015s window: 43
average rate: 10.000
	min: 0.100s max: 0.100s std dev: 0.00016s window: 53
average rate: 10.000
	min: 0.100s max: 0.100s std dev: 0.00016s window: 64
average rate: 10.000
	min: 0.099s max: 0.101s std dev: 0.00023s window: 75
average rate: 10.000
	min: 0.099s max: 0.101s std dev: 0.00022s window: 85

exit=124

$ ros2 param set /patrol linear_speed 0.8
Set parameter successful

exit=0

$ ros2 param set /patrol turn_rate -0.5
Set parameter successful

exit=0

$ ros2 topic echo /turtle1/cmd_vel --once
linear:
  x: 0.8
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: -0.5
---

exit=0

$ ros2 param set /patrol publish_hz 5.0
Set parameter successful

exit=0

$ ros2 topic hz /turtle1/cmd_vel
average rate: 4.999
	min: 0.200s max: 0.201s std dev: 0.00023s window: 6
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00027s window: 12
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00029s window: 17
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00026s window: 22
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00024s window: 27
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00024s window: 33
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00024s window: 39

exit=124

$ ros2 param set /patrol publish_hz 0.0
Setting parameter failed: publish_hz must be in [1.0, 30.0]

exit=0

$ ros2 param get /patrol publish_hz
Double value is: 5.0

exit=0

$ ros2 topic hz /turtle1/cmd_vel
average rate: 5.001
	min: 0.200s max: 0.200s std dev: 0.00018s window: 6
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00031s window: 11
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00027s window: 17
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00027s window: 22
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00025s window: 28
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00023s window: 33
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00022s window: 39
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00021s window: 44

exit=124

$ ros2 service call /clear std_srvs/srv/Empty '{}'
waiting for service to become available...
requester: making request: std_srvs.srv.Empty_Request()

response:
std_srvs.srv.Empty_Response()


exit=0

$ ros2 action list -t
/turtle1/rotate_absolute [turtlesim/action/RotateAbsolute]

exit=0

$ ros2 topic echo /turtle1/pose --once
x: 5.535612106323242
y: 3.9320809841156006
theta: -1.7792147397994995
linear_velocity: 0.800000011920929
angular_velocity: -0.5
---

exit=0
```

## Официальная проверка комплекта

Установлен официальный course kit v1-w06. SHA256 архива:
`6eda53e1c566f7f0a7e09d7afe1e5a6f3b98397175a7e57dede9a84c6d14d0fe`.
Архив и его файлы проверены по контрольным суммам.

```text
$ python3 tools/prepare_pr04_report.py
PR04: контракт evidence выполнен
Official kit installed, report prepared and PR04 contract passed.
```

Метаданные report.json обновлены. Проверка выполнена официальным checker
с официальным манифестом PR04; собственный манифест не создавался.
