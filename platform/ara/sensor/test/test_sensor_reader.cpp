#include "ara/sensor/sensor_reader.h"

#include <gtest/gtest.h>
#include <string>
#include <vector>

namespace
{

    TEST(SensorReaderTest, ParsesWellFormedRecord)
    {
        const telemetry::SensorReader reader;
        const std::optional<telemetry::Sample> sample = reader.parse_line("1700000000,21.5,C");

        ASSERT_TRUE(sample.has_value());
        EXPECT_EQ(sample->timestamp_ms, 1700000000u);
        EXPECT_DOUBLE_EQ(sample->value, 21.5);
        EXPECT_EQ(sample->unit, "C");
    }

    TEST(SensorReaderTest, RejectsNonNumericTimestamp)
    {
        const telemetry::SensorReader reader;
        EXPECT_FALSE(reader.parse_line("not-a-number,21.5,C").has_value());
    }

    TEST(SensorReaderTest, RejectsMissingField)
    {
        const telemetry::SensorReader reader;
        EXPECT_FALSE(reader.parse_line("1700000000,21.5").has_value());
    }

    TEST(SensorReaderTest, RejectsEmptyLine)
    {
        const telemetry::SensorReader reader;
        EXPECT_FALSE(reader.parse_line("").has_value());
    }

    TEST(SensorReaderTest, CountsRejectedRecords)
    {
        const telemetry::SensorReader reader;
        const std::string buffer = "1,1.0,C\nbroken\n2,2.0,C\nalso broken\n";
        const std::vector<telemetry::Sample> samples = reader.parse_buffer(buffer);

        EXPECT_EQ(samples.size(), 2u);
        EXPECT_EQ(reader.rejected_count(), 2u);
    }

    TEST(SensorReaderTest, SkipsBlankLinesWithoutRejecting)
    {
        const telemetry::SensorReader reader;
        const std::vector<telemetry::Sample> samples =
            reader.parse_buffer("1,1.0,C\n\n\n2,2.0,C\n");

        EXPECT_EQ(samples.size(), 2u);
        EXPECT_EQ(reader.rejected_count(), 0u);
    }

} // namespace
