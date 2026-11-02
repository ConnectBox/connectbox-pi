# These are stand-alone harnesses (run_all.sh runs them with the file under test as an argument),
# not pytest tests: keep pytest from collecting them.
collect_ignore_glob = ["*.py"]
