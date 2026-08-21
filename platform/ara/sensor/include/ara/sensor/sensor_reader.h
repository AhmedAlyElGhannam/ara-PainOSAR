#ifndef PLATFORM_ARA_SENSOR_INCLUDE_ARA_SENSOR_SENSOR_READER_H
#define PLATFORM_ARA_SENSOR_INCLUDE_ARA_SENSOR_SENSOR_READER_H

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace telemetry
{

    /// A single reading lifted off a sensor bus.
    struct Sample
    {
        std::uint64_t timestamp_ms = 0;
        double value = 0.0;
        std::string unit;
    };

    /// Parses newline-delimited "timestamp,value,unit" records.
    class SensorReader
    {
    public:
        SensorReader() = default;

        /// Parses a single record. Returns nullopt when the record is malformed.
        std::optional<Sample> parse_line(const std::string& line) const;

        /// Parses a whole buffer, skipping malformed records.
        std::vector<Sample> parse_buffer(const std::string& buffer) const;

        /// Number of records rejected by the most recent parse_buffer call.
        std::size_t rejected_count() const;

    private:
        mutable std::size_t rejected_ = 0;
    };

} // namespace telemetry

#endif // PLATFORM_ARA_SENSOR_INCLUDE_ARA_SENSOR_SENSOR_READER_H
