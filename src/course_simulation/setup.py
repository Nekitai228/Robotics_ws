from pathlib import Path

from setuptools import setup

resources = ['launch', 'config', 'models', 'worlds']
data = [
    ('share/ament_index/resource_index/packages', ['resource/course_simulation']),
    ('share/course_simulation', ['package.xml', 'KIT_VERSION', 'KIT_LICENSE.md']),
]
for directory in resources:
    for folder in sorted({str(p.parent) for p in Path(directory).rglob('*') if p.is_file()}):
        data.append(('share/course_simulation/' + folder,
                     [str(p) for p in Path(folder).iterdir() if p.is_file()]))

setup(
    name='course_simulation', version='0.1.0', packages=['course_simulation'],
    data_files=data, install_requires=['setuptools'], zip_safe=True,
    maintainer='iakup', maintainer_email='nekitaikapov@gmail.com',
    description='Headless Ackermann simulation and guarded adapters',
    license='Apache-2.0', tests_require=['pytest'],
    entry_points={'console_scripts': [
        'drive_adapter = course_simulation.drive_adapter:main',
        'odom_adapter = course_simulation.odom_adapter:main',
        'test_drive = course_simulation.test_drive:main',
    ]},
)
