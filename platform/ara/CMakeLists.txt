# One add_subdirectory per module. Adding a module is one line here plus the
# module's own directory -- nothing else in the build needs to know.
add_subdirectory(sensor)
add_subdirectory(log)
add_subdirectory(heartbeat)
