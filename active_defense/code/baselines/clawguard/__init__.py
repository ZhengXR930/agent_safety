try:
    from code.baselines.clawguard.runner import RUNNER
except ModuleNotFoundError:
    try:
        from baselines.clawguard.runner import RUNNER
    except ModuleNotFoundError:
        RUNNER = None

try:
    from code.baselines.clawguard.adapter import ClawGuardScanner
except ModuleNotFoundError:
    from baselines.clawguard.adapter import ClawGuardScanner
