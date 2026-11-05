import importlib
m = importlib.import_module("main")
assert hasattr(m, "main") and callable(m.main), "main() missing in main"
print("selftest OK: main importable, main() callable")
