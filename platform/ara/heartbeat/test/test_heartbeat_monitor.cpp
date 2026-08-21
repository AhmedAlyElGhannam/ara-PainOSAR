#include "ara/heartbeat/heartbeat_monitor.h"

#include <gtest/gtest.h>

namespace
{

    TEST(HeartbeatMonitorTest, FirstBeatIsAlwaysAccepted)
    {
        telemetry::HeartbeatMonitor monitor(100.0);

        EXPECT_TRUE(monitor.record(1000));
        EXPECT_TRUE(monitor.is_alive());
        EXPECT_EQ(monitor.stats().beats, 1u);
        EXPECT_EQ(monitor.stats().missed, 0u);
    }

    TEST(HeartbeatMonitorTest, AcceptsBeatsInsideTheWindow)
    {
        telemetry::HeartbeatMonitor monitor(100.0);

        EXPECT_TRUE(monitor.record(0));
        EXPECT_TRUE(monitor.record(100));
        EXPECT_TRUE(monitor.record(240));

        EXPECT_TRUE(monitor.is_alive());
        EXPECT_EQ(monitor.stats().missed, 0u);
    }

    TEST(HeartbeatMonitorTest, FlagsABeatBeyondTheWindow)
    {
        telemetry::HeartbeatMonitor monitor(100.0);

        EXPECT_TRUE(monitor.record(0));
        EXPECT_FALSE(monitor.record(400));

        EXPECT_EQ(monitor.stats().missed, 1u);
        EXPECT_FALSE(monitor.is_alive());
    }

    TEST(HeartbeatMonitorTest, AveragesOnlyTheGapsBetweenBeats)
    {
        telemetry::HeartbeatMonitor monitor(100.0);

        monitor.record(0);
        monitor.record(100);
        monitor.record(220);

        EXPECT_EQ(monitor.stats().beats, 3u);
        EXPECT_DOUBLE_EQ(monitor.stats().mean_interval_ms, 110.0);
    }

    TEST(HeartbeatMonitorTest, TreatsBackwardsTimeAsAMissedBeat)
    {
        telemetry::HeartbeatMonitor monitor(100.0);

        EXPECT_TRUE(monitor.record(5000));
        EXPECT_FALSE(monitor.record(4000));

        EXPECT_EQ(monitor.stats().missed, 1u);
    }

    TEST(HeartbeatMonitorTest, ResetClearsHistory)
    {
        telemetry::HeartbeatMonitor monitor(100.0);

        monitor.record(0);
        monitor.record(400);
        monitor.reset();

        EXPECT_EQ(monitor.stats().beats, 0u);
        EXPECT_EQ(monitor.stats().missed, 0u);
        EXPECT_DOUBLE_EQ(monitor.stats().mean_interval_ms, 0.0);
        EXPECT_FALSE(monitor.is_alive());
    }

    // INTENTIONALLY FAILING: one late beat clears is_alive(), so this
    // expectation is wrong. Kept to prove the unit stage actually goes red.
    TEST(HeartbeatMonitorTest, ToleratesASingleLateBeat)
    {
        telemetry::HeartbeatMonitor monitor(100.0);

        monitor.record(0);
        monitor.record(400);

        EXPECT_TRUE(monitor.is_alive());
    }

} // namespace
