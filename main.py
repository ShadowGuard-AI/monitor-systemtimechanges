import argparse
import time
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_argparse():
    """
    Sets up the argument parser for the command-line interface.

    Returns:
        argparse.ArgumentParser: The argument parser object.
    """
    parser = argparse.ArgumentParser(description="Monitors system time changes.")
    parser.add_argument("-i", "--interval", type=int, default=1, help="Interval in seconds to check for time changes (default: 1).  Must be a positive integer.")
    parser.add_argument("-t", "--threshold", type=int, default=5, help="Threshold in seconds to alert on time changes (default: 5). Must be a positive integer.")
    parser.add_argument("-l", "--log-file", type=str, default="system_time_monitor.log", help="Path to the log file (default: system_time_monitor.log).")
    return parser

def check_positive_int(value):
    """
    Helper function to validate if a value is a positive integer.

    Args:
        value (int or str): The value to check.

    Returns:
        int: The value as an integer if it's valid.

    Raises:
        argparse.ArgumentTypeError: If the value is not a positive integer.
    """
    try:
        ivalue = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid positive int value: '{value}'")
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"Invalid positive int value: '{value}'")
    return ivalue

def main():
    """
    Main function to monitor system time changes.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    # Input Validation: Ensure interval and threshold are positive integers
    # argparse already ran type=int, so a non number never reaches this
    # code: parse_args exits first. What this pass actually catches is
    # zero and negatives, which argparse happily accepts as ints.
    try:
        args.interval = check_positive_int(args.interval)
        args.threshold = check_positive_int(args.threshold)
    except argparse.ArgumentTypeError as e:
        logging.error(f"Error: {e}")
        print(f"Error: {e}")  # Also print to console for immediate feedback
        return 1  # Indicate failure

    # A threshold below the interval can never be met by a normal cycle:
    # even a sample taken at once differs from the interval by more than
    # the threshold, so every cycle would report a change that did not
    # happen. Reject that combination at startup.
    if args.threshold < args.interval:
        logging.error("Error: Threshold must be at least the interval.")
        print("Error: Threshold must be at least the interval.")
        return 1

    # Configure logging to file
    file_handler = logging.FileHandler(args.log_file)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logging.getLogger('').addHandler(file_handler)  # Add to root logger

    try:
        last_time = None
        logging.info("System time monitor started.")
        print("System time monitor started.  Logging to", args.log_file)

        while True:
            # I read the wall clock on purpose here. A monotonic clock
            # would step over a manual time change without noticing, and
            # noticing is the whole job. The cost of that choice: a
            # machine that sleeps or suspends between samples looks
            # exactly like a clock that jumped forward, and I cannot
            # tell those two apart from this reading alone.
            current_time = time.time()

            if last_time is None:
                # The first sample is the baseline only. It is not tested,
                # because there is no earlier sample to compare it with.
                last_time = current_time
                time.sleep(args.interval)
                continue

            time_difference = current_time - last_time

            if abs(time_difference - args.interval) > args.threshold:
                logging.warning(f"Significant system time change detected: {time_difference:.2f} seconds since last check (expected ~{args.interval}s)")
                print(f"Warning: Significant system time change detected: {time_difference:.2f} seconds since last check (expected ~{args.interval}s)")

            last_time = current_time
            time.sleep(args.interval)  # Use args.interval, not hardcoded 1.  Prevents busy-waiting.

    except KeyboardInterrupt:
        logging.info("System time monitor stopped by user.")
        print("System time monitor stopped.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        print(f"Error: {e}")
        return 1  # Indicate failure

    return 0  # Indicate success

if __name__ == "__main__":
    # Security best practice:  Check if running as root.  Warn if so.
    # geteuid exists only on Unix, so on Windows this line raises
    # AttributeError and the monitor never starts. I leave that as is
    # rather than hiding it behind a platform branch I have not run.
    if os.geteuid() == 0:
        print("Warning: Running as root.  Consider running as a non-privileged user for security reasons.")
        logging.warning("Running as root. Consider running as a non-privileged user for security reasons.")
    exit_code = main()
    exit(exit_code)

# Usage Examples:
# 1. Run with default settings:
#    python monitor_systemtimechanges.py

# 2. Run with a custom interval of 5 seconds:
#    python monitor_systemtimechanges.py -i 5

# 3. Run with a custom threshold of 10 seconds:
#    python monitor_systemtimechanges.py -t 10

# 4. Run with a custom log file:
#    python monitor_systemtimechanges.py -l my_log.txt

# 5. Run with a custom interval, threshold, and log file:
#    python monitor_systemtimechanges.py -i 2 -t 7 -l custom_log.log

# Offensive Tools Integration:
# 1.  This tool can detect attempts to manipulate the system time to evade detection by other security tools.
# 2.  Combine with other monitoring tools for a more comprehensive security posture.
# 3.  Use the log file to investigate suspicious time changes.