# The shipped executable. It is not a module -- it composes modules -- so it
# lives beside ara/ rather than inside it. platform/test/ drives this binary.
add_executable(telemetry_cli
    src/main.cpp)

target_link_libraries(telemetry_cli
    PRIVATE
        ara::log
        ara::sensor)
