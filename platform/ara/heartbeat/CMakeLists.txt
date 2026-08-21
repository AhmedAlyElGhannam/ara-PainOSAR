add_library(ara_heartbeat
    src/heartbeat_monitor.cpp)

# PUBLIC so consumers inherit the include path. Headers live under
# include/ara/heartbeat/, so the include directive mirrors the namespace:
#     #include "ara/heartbeat/heartbeat_monitor.h"
target_include_directories(ara_heartbeat
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>)

# telemetry_flags carries the mandated compile and link flags.
target_link_libraries(ara_heartbeat PUBLIC telemetry_flags)

add_library(ara::heartbeat ALIAS ara_heartbeat)

if(TELEMETRY_BUILD_TESTS AND BUILD_TESTING)
    add_subdirectory(test)
endif()
