#ifndef PLATFORM_ARA_LOG_INCLUDE_ARA_LOG_LOG_FORMATTER_H
#define PLATFORM_ARA_LOG_INCLUDE_ARA_LOG_LOG_FORMATTER_H

#include "ara/sensor/sensor_reader.h"

#include <string>

namespace telemetry
{

    enum class Severity
    {
        Debug,
        Info,
        Warning,
        Error
    };

    /// Renders samples as single-line log records.
    class LogFormatter
    {
    public:
        explicit LogFormatter(Severity minimum = Severity::Info);

        /// Formats one sample as "<LEVEL> <timestamp> <value><unit>".
        std::string format(const Sample& sample, Severity severity) const;

        /// True when a record at this severity would be emitted.
        bool enabled(Severity severity) const;

    private:
        Severity minimum_;
    };

    /// Stable textual name for a severity level.
    std::string to_string(Severity severity);

} // namespace telemetry

#endif // PLATFORM_ARA_LOG_INCLUDE_ARA_LOG_LOG_FORMATTER_H
