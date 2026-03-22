    status = updater.get_status()
    print(f"\n📊 Update Status:")
    print(f"  Current version: {status['current_version']}")
    print(f"  Last check: {status['state']['last_check']}")
    print(f"  Update available: {status['update_available']}")


if __name__ == "__main__":
    import sys
    example_usage()