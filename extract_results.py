import json
import os

base_dir = "MTSS/evaluation_output"
configs = [
    "btms_routing_fixed-50-50",
    "btms_routing_exp2-hybrid-balanced",
    "btms_routing_exp5-size-heavy",
    "btms_routing_exp1-hybrid-default",
    "btms_routing_exp3-ppl-heavy",
    "btms_routing_exp4-vote-heavy",
    "btms_routing_baseline1-ppl-only",
    "btms_routing_baseline2-vote-only",
    "btms_routing_baseline3-size-adjusted"
]

print("| Config | Fixed Bugs | Failed Bugs | Success Rate | Edit Success | Gen Success |")
print("|---|---|---|---|---|---|")

for config in configs:
    json_path = os.path.join(base_dir, config, "btms_routing_results.json")
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            total = data.get("total_bugs", 0)
            fixed = data.get("fixed_bugs", 0)
            failed = data.get("failed_bugs", 0)
            success_rate = (fixed / total * 100) if total > 0 else 0
            edit_s = data.get("edit_success", 0)
            gen_s = data.get("gen_success", 0)
            
            name = config.replace("btms_routing_", "")
            print(f"| {name} | {fixed} | {failed} | {success_rate:.1f}% | {edit_s} | {gen_s} |")
    except Exception as e:
        print(f"| {config} | Error: {e} | | | | |")
