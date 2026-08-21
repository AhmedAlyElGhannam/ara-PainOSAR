#include "ara/heartbeat/heartbeat_monitor.h"

namespace telemetry
{

    namespace
    {

        /// A beat counts as missed once the gap exceeds this multiple of the
        /// expected period. 1.5 leaves room for ordinary scheduling jitter
        /// without letting a genuinely skipped beat through.
        constexpr double kLateFactor = 1.5;

    } // namespace

    HeartbeatMonitor::HeartbeatMonitor(double expected_period_ms)
        : expected_period_ms_(expected_period_ms)
    {
    }

    bool HeartbeatMonitor::record(std::uint64_t timestamp_ms)
    {
        ++stats_.beats;

        if (!has_previous_)
        {
            has_previous_ = true;
            previous_timestamp_ms_ = timestamp_ms;
            return true;
        }

        // Time never runs backwards on a healthy bus. Treat it as a missed
        // beat rather than letting the unsigned subtraction wrap into a
        // multi-billion-millisecond interval.
        if (timestamp_ms < previous_timestamp_ms_)
        {
            previous_timestamp_ms_ = timestamp_ms;
            ++stats_.missed;
            return false;
        }

        const double interval_ms = static_cast<double>(timestamp_ms - previous_timestamp_ms_);
        previous_timestamp_ms_ = timestamp_ms;

        ++intervals_;
        total_interval_ms_ += interval_ms;
        stats_.mean_interval_ms = total_interval_ms_ / static_cast<double>(intervals_);

        if (interval_ms > expected_period_ms_ * kLateFactor)
        {
            ++stats_.missed;
            return false;
        }

        return true;
    }

    bool HeartbeatMonitor::is_alive() const
    {
        return stats_.beats > 0 && stats_.missed == 0;
    }

    HeartbeatStats HeartbeatMonitor::stats() const
    {
        return stats_;
    }

    void HeartbeatMonitor::reset()
    {
        has_previous_ = false;
        previous_timestamp_ms_ = 0;
        intervals_ = 0;
        total_interval_ms_ = 0.0;
        stats_ = HeartbeatStats{};
    }

} // namespace telemetry
