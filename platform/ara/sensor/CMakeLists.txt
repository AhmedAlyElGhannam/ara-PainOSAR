add_library(ara_sensor
    src/sensor_reader.cpp)

# PUBLIC so consumers inherit the include path. Headers live under
# include/ara/sensor/, so the include directive mirrors the namespace:
#     #include "ara/sensor/sensor_reader.h"
target_include_directories(ara_sensor
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>)

# telemetry_flags carries the mandated compile and link flags.
target_link_libraries(ara_sensor PUBLIC telemetry_flags)

add_library(ara::sensor ALIAS ara_sensor)

if(TELEMETRY_BUILD_TESTS AND BUILD_TESTING)
    add_subdirectory(test)
endif()
