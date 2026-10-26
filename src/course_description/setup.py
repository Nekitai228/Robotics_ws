from glob import glob

from setuptools import setup

setup(
    name='course_description', version='0.1.0', packages=['course_description'],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/course_description']),
        ('share/course_description', ['package.xml']),
        ('share/course_description/urdf', glob('urdf/*.xacro')),
        ('share/course_description/launch', glob('launch/*.py')),
        ('share/course_description/rviz', glob('rviz/*.rviz')),
    ],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='iakup', maintainer_email='nekitaikapov@gmail.com',
    description='Ackermann description and sensor frames', license='Apache-2.0',
    tests_require=['pytest'],
)
