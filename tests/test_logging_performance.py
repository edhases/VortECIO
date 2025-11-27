import time
from advanced_logging import DetailedLogger

def test_logging_overhead():
    # Test without logging
    start = time.perf_counter()
    for i in range(1000):
        pass # Simulate control loop
    baseline = time.perf_counter() - start

    # Test with logging enabled
    logger = DetailedLogger(enabled=True)
    start = time.perf_counter()
    for i in range(1000):
        logger.log_fan_state(0, 65.0, 50, 2500, 'auto')
    with_logging = time.perf_counter() - start
    logger.shutdown()

    overhead = (with_logging - baseline) / baseline * 100
    print(f"Baseline: {baseline*1000:.2f}ms")
    print(f"With logging: {with_logging*1000:.2f}ms")
    print(f"Overhead: {overhead:.1f}%")

    assert overhead < 10, f"Logging overhead too high: {overhead}%"
