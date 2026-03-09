from setuptools import setup

package_name = "oakd_face_publisher"

setup(
    name=package_name,
    version="0.0.1",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="todo",
    maintainer_email="todo@example.com",
    description="On-device face detection and ROS2 publisher.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "face_publisher = oakd_face_publisher.face_publisher:main",
        ],
    },
)
