add_executable(ara_sensor_tests
    test_sensor_reader.cpp)

target_link_libraries(ara_sensor_tests
    PRIVATE
        ara::sensor
        GTest::gtest_main)

# Each TEST() is registered with CTest separately, so a crash in one case does
# not hide the results of the others.
gtest_discover_tests(ara_sensor_tests
    PROPERTIES
        ENVIRONMENT "ASAN_OPTIONS=detect_leaks=1:abort_on_error=0"
    DISCOVERY_TIMEOUT 60)
