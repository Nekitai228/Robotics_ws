# ПР06 — координаты и владельцы tf

Единицы: м, кг, с; REP-103: x вперёд, y влево, z вверх.
Корень URDF: base_link. map и odom в ПР06 не публикуются.

| Parent | Child | xyz, м | Тип / ось | Единственный владелец |
|---|---|---|---|---|
| base_link | camera_link | 0.28, 0, 0.38 | fixed, rpy=0 | robot_state_publisher, /tf_static |
| base_link | lidar_link | 0.28, 0, 0.38 | fixed, rpy=0 | robot_state_publisher, /tf_static |
| base_link | imu_link | 0.28, 0, 0.38 | fixed, rpy=0 | robot_state_publisher, /tf_static |
| base_link | front_left_knuckle | 0.4, 0.31, 0 | revolute, z | robot_state_publisher, /tf при joint_states |
| base_link | front_right_knuckle | 0.4, -0.31, 0 | revolute, z | robot_state_publisher, /tf при joint_states |
| front_left_knuckle | front_left_wheel | 0, 0, 0 | continuous, y | robot_state_publisher, /tf при joint_states |
| front_right_knuckle | front_right_wheel | 0, 0, 0 | continuous, y | robot_state_publisher, /tf при joint_states |
| base_link | rear_left_wheel | -0.4, 0.31, 0 | continuous, y | robot_state_publisher, /tf при joint_states |
| base_link | rear_right_wheel | -0.4, -0.31, 0 | continuous, y | robot_state_publisher, /tf при joint_states |

Геометрия и poses сенсоров взяты из models/course_ackermann/model.sdf
официального kit v1-w08. Колёсная база, колея и радиус заданы Xacro-аргументами.
Visual и collision объявлены раздельно. Цилиндры колёс развёрнуты вокруг x,
ось вращения суставов остаётся y в родительской системе координат.

Дефект: ветка pr06-defect, commit 31b659f; lidar_joint получил parent
camera_link при прежнем offset. tf2_echo показал (0.56, 0, 0.76) вместо
(0.28, 0, 0.38). check_urdf принял оба дерева, но test_sensor_parents
упал для дефекта и прошёл для исправления (model-check.txt).
Деревья view_frames и фактические tf сохранены до и после.

RViz запущен с конфигурацией vehicle.rviz и Fixed Frame=base_link;
инициализация OpenGL подтверждена rviz.log. Колёса требуют joint_states,
ручная команда для всех шести суставов приведена в README. Фиксированные
сенсоры доступны без joint_state_publisher. Предупреждение KDL о root inertia
не мешает публикации fixed transforms; значение инерции сохранено в URDF.

Фактическое окружение: WSL2, Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic 8.15.0.
Новый baseline kit — Ubuntu 26.04/Lyrical/Jetty; это выполненная и проверенная
адаптация к имеющейся системе, а не заявление о запуске нормативного образа.
