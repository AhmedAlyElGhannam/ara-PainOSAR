add_executable(ara_heartbeat_tests
    test_heartbeat_monitor.cpp)

target_link_libraries(ara_heartbeat_tests
    PRIVATE
        ara::heartbeat
        GTest::gtest_main)

gtest_discover_tests(ara_heartbeat_tests
    PROPERTIES
        ENVIRONMENT "ASAN_OPTIONS=detect_leaks=1:abort_on_error=0"
    DISCOVERY_TIMEOUT 60)
