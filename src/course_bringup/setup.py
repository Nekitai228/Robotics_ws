from glob import glob

from setuptools import find_packages, setup

package_name = 'course_bringup'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='iakup',
    maintainer_email='nekitaikapov@gmail.com',
    description='Namespaced launch, pose relay and QoS experiment',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'pose_relay = course_bringup.pose_relay:main',
            'pose_listener = course_bringup.pose_listener:main',
        ],
    },
)
