add_executable(ara_log_tests
    test_log_formatter.cpp)

target_link_libraries(ara_log_tests
    PRIVATE
        ara::log
        GTest::gtest_main)

gtest_discover_tests(ara_log_tests
    PROPERTIES
        ENVIRONMENT "ASAN_OPTIONS=detect_leaks=1:abort_on_error=0"
    DISCOVERY_TIMEOUT 60)
