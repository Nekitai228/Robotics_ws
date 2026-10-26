# ПР07 — одометрия и tf

Bridge: /model/course_ackermann/odometry -> /vehicle/odom_gz,
nav_msgs/msg/Odometry, reliable. Измеренные исходные frames:
course_ackermann/odom -> course_ackermann/base_link.

Единственный odom_adapter меняет их на odom -> base_link, сохраняя stamp,
pose, twist и обе covariance. Он публикует /vehicle/odom и совпадающий
TransformStamped в /tf. Чужие или уже нормализованные frames, NaN/Inf
и нулевой quaternion отклоняются без публикации.

| Связь | Владелец | Канал |
|---|---|---|
| odom -> base_link | /robot_a/odom_adapter | /tf |
| base_link -> camera_link | /robot_a/robot_state_publisher | /tf_static |
| base_link -> lidar_link | /robot_a/robot_state_publisher | /tf_static |
| base_link -> imu_link | /robot_a/robot_state_publisher | /tf_static |
| суставы колёс/руля, если придут joint_states | robot_state_publisher | /tf |

RSP объявляет издателя /tf даже без joint_states: у топика два издателя,
у ребра odom->base_link один. В URDF нет odom; Gazebo TF не пересылается
в ROS. В ПР08 при replay адаптер повторно не запускается.

Тест test_odometry_preserved использует ненулевые pose/twist, разные
covariance и stamp 12 с + 345 нс, проверяет сохранение данных и stamp.
В runtime найден один stamp одновременно в /vehicle/odom и /tf,
позиция и quaternion совпали. Сырые и выходные frames есть в sensors.json.

Независимая физическая проверка dynamic_pose/info: корпус прошёл 2.4161 м,
одометрия 2.4236 м. После удаления рулевого поворота и крепления цилиндра
остаточное вращение всех колёс идёт вокруг y. Передние knuckle повернулись
на 0.1591 и 0.1418 рад. Исходные данные: body-before.txt, body-after.txt;
расчёт: wheel-check.json.

Дефект bridge-defect.yaml: Gazebo-топик /vehicle/imu_typo вместо
/vehicle/imu. ROS-издатель виден, но echo best_effort завершается с 124;
Gazebo IMU читается. После остановки дефектного launch и запуска одного
исправного IMU доходит. Диагностика: defect.txt, diagnostics.txt.

fixtures/pr07-sensors: MCAP, --use-sim-time, 32.935 с симуляции.
Семь топиков непустые; содержимое прочитано rosbag2_py,
результат в bag-content-check.json. Метаданные и SHA256 сохранены,
бинарный bag остаётся локально вне Git.

Среда: WSL2 Ubuntu 24.04.5, Jazzy, Harmonic 8.15.0, OGRE2/EGL, llvmpipe.
Новый baseline kit Ubuntu 26.04/Lyrical/Jetty здесь не проверялся.
В workstation.txt исключён Windows PATH, чтобы code --version не запускал
установку VS Code Server. Docker для выбранного нативного WSL-пути не нужен.
