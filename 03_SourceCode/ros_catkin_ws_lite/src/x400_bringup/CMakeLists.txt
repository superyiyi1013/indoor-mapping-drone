cmake_minimum_required(VERSION 3.0.2)
project(x400_bringup)

find_package(catkin REQUIRED)

catkin_package()

install(DIRECTORY config launch scripts
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
  USE_SOURCE_PERMISSIONS
)
