#include "ara/log/log_formatter.h"
#include "ara/sensor/sensor_reader.h"

#include <iostream>
#include <sstream>
#include <string>

namespace
{

    telemetry::Severity severity_for(double value)
    {
        if (value > 100.0)
        {
            return telemetry::Severity::Error;
        }
        if (value > 50.0)
        {
            return telemetry::Severity::Warning;
        }
        return telemetry::Severity::Info;
    }

} // namespace

/// Reads "timestamp,value,unit" records on stdin and writes log lines on stdout.
/// Exits 1 when any record was rejected, so the integration tests can assert on it.
int main()
{
    std::ostringstream buffer;
    buffer << std::cin.rdbuf();

    const telemetry::SensorReader reader;
    const telemetry::LogFormatter formatter(telemetry::Severity::Info);

    const std::vector<telemetry::Sample> samples = reader.parse_buffer(buffer.str());
    for (const telemetry::Sample& sample : samples)
    {
        const std::string line = formatter.format(sample, severity_for(sample.value));
        if (!line.empty())
        {
            std::cout << line << '\n';
        }
    }

    if (reader.rejected_count() > 0)
    {
        std::cerr << "rejected " << reader.rejected_count() << " malformed record(s)\n";
        return 1;
    }
    return 0;
}
