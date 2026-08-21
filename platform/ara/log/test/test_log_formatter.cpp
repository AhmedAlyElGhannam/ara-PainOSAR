#include "ara/log/log_formatter.h"
#include "ara/sensor/sensor_reader.h"

#include <gtest/gtest.h>
#include <string>
#include <vector>

namespace
{

    TEST(LogFormatterTest, SuppressesBelowMinimumSeverity)
    {
        const telemetry::LogFormatter formatter(telemetry::Severity::Warning);
        const telemetry::Sample sample{1, 2.0, "C"};

        EXPECT_TRUE(formatter.format(sample, telemetry::Severity::Debug).empty());
        EXPECT_FALSE(formatter.format(sample, telemetry::Severity::Error).empty());
    }

    TEST(LogFormatterTest, RendersSeverityName)
    {
        EXPECT_EQ(telemetry::to_string(telemetry::Severity::Warning), "WARN");
        EXPECT_EQ(telemetry::to_string(telemetry::Severity::Error), "ERROR");
    }

} // namespace
