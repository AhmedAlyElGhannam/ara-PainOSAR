#ifndef ARA_HEARTBEAT_HEARTBEAT_MONITOR_H
#define ARA_HEARTBEAT_HEARTBEAT_MONITOR_H

#include <cstddef>
#include <cstdint>

namespace telemetry
{

    /// Aggregate view of what the monitor has seen since the last reset.
    struct HeartbeatStats
    {
        std::size_t beats = 0;
        std::size_t missed = 0;
        double mean_interval_ms = 0.0;
    };



    /// Watches a periodic signal and reports beats that arrived too late.
    class HeartbeatMonitor
    {
    public:
        explicit  HeartbeatMonitor(double expected_period_ms);

        /// Records a beat. Returns false when the gap since the previous beat
        /// exceeded the tolerated window, or when time ran backwards.
        bool record(std::uint64_t timestamp_ms);

        /// True while at least one beat has been seen and none were missed.
        bool  is_alive() const;

        /// Counters accumulated since construction or the last reset().
        HeartbeatStats stats() const;

        /// Drops all history; the next beat starts a fresh sequence.
        void reset();

    private:
        double expected_period_ms_;
        bool has_previous_ = false;
        std::uint64_t previous_timestamp_ms_ = 0;
        std::size_t intervals_ = 0;
        double total_interval_ms_ = 0.0;
        HeartbeatStats stats_;
    };

} // namespace telemetry

#endif // ARA_HEARTBEAT_HEARTBEAT_MONITOR_H
