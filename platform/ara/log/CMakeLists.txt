add_library(ara_log
    src/log_formatter.cpp)

target_include_directories(ara_log
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>)

# ara::log uses ara::sensor's Sample type in its public header, so the
# dependency is PUBLIC -- anything linking ara::log also needs ara::sensor's
# headers. PRIVATE here would compile and then fail at the consumer.
target_link_libraries(ara_log
    PUBLIC
        ara::sensor
        telemetry_flags)

add_library(ara::log ALIAS ara_log)

if(TELEMETRY_BUILD_TESTS AND BUILD_TESTING)
    add_subdirectory(test)
endif()
