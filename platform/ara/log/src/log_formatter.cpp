#include "ara/log/log_formatter.h"

#include <sstream>

namespace telemetry
{

    LogFormatter::LogFormatter(Severity minimum) : minimum_(minimum)
    {
    }

    bool LogFormatter::enabled(Severity severity) const
    {
        return static_cast<int>(severity) >= static_cast<int>(minimum_);
    }

    std::string LogFormatter::format(const Sample& sample, Severity severity) const
    {
        if (!enabled(severity))
        {
            return {};
        }

        std::ostringstream stream;
        stream << to_string(severity) << ' ' << sample.timestamp_ms << ' ' << sample.value
               << sample.unit;
        return stream.str();
    }

    std::string to_string(Severity severity)
    {
        switch (severity)
        {
            case Severity::Debug:
                return "DEBUG";
            case Severity::Info:
                return "INFO";
            case Severity::Warning:
                return "WARN";
            case Severity::Error:
                return "ERROR";
        }
        return "UNKNOWN";
    }

} // namespace telemetry
