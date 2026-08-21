#include "ara/sensor/sensor_reader.h"

#include <charconv>
#include <sstream>

namespace telemetry
{

    namespace
    {

        bool parse_u64(const std::string& text, std::uint64_t& out)
        {
            const char* first = text.data();
            const char* last = text.data() + text.size();
            const std::from_chars_result result = std::from_chars(first, last, out);
            return result.ec == std::errc() && result.ptr == last;
        }

        bool parse_double(const std::string& text, double& out)
        {
            try
            {
                std::size_t consumed = 0;
                out = std::stod(text, &consumed);
                return consumed == text.size();
            }
            catch (const std::exception&)
            {
                return false;
            }
        }

    } // namespace

    std::optional<Sample> SensorReader::parse_line(const std::string& line) const
    {
        if (line.empty())
        {
            return std::nullopt;
        }

        std::istringstream stream(line);
        std::string timestamp_text;
        std::string value_text;
        std::string unit_text;

        if (!std::getline(stream, timestamp_text, ','))
        {
            return std::nullopt;
        }
        if (!std::getline(stream, value_text, ','))
        {
            return std::nullopt;
        }
        if (!std::getline(stream, unit_text))
        {
            return std::nullopt;
        }

        Sample sample;
        if (!parse_u64(timestamp_text, sample.timestamp_ms))
        {
            return std::nullopt;
        }
        if (!parse_double(value_text, sample.value))
        {
            return std::nullopt;
        }

        sample.unit = unit_text;
        return sample;
    }

    std::vector<Sample> SensorReader::parse_buffer(const std::string& buffer) const
    {
        std::vector<Sample> samples;
        std::istringstream stream(buffer);
        std::string line;

        rejected_ = 0;
        while (std::getline(stream, line))
        {
            if (line.empty())
            {
                continue;
            }
            const std::optional<Sample> parsed = parse_line(line);
            if (parsed.has_value())
            {
                samples.push_back(*parsed);
            }
            else
            {
                ++rejected_;
            }
        }

        return samples;
    }

    std::size_t SensorReader::rejected_count() const
    {
        return rejected_;
    }

} // namespace telemetry
