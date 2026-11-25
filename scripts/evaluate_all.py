from train_all import RESULTS
import json

for name in ("uk_retail_benchmark", "twin2k_pricing_fidelity", "sandbox_choice_benchmark", "choice_experiments", "bayes_diagnostics"):
    path = RESULTS / f"{name}.json"
    print(name)
    print(path.read_text(encoding="utf-8") if path.exists() else json.dumps({"status": "pending"}))
