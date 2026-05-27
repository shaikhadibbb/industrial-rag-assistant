import json
import os

test_set = [
    {
        "question": "What is the definition of mechanical work?",
        "ground_truth": "Mechanical work is defined as the product of a force and the distance over which the force operates on a body.",
        "reference_context": "Mechanical work may be defined as the product of a force and the distance over which the force operates on a body. Exactly as for heat, work is energy that is transferred from one body to another."
    },
    {
        "question": "Who can produce and maintain standards?",
        "ground_truth": "Standards can be produced, issued and maintained by standardization organizations on national, supra-national (European) and international levels, as well as by specific trade associations.",
        "reference_context": "Standards may be produced, issued and maintained by standardization organizations on national, supra-national (European) and international levels, but equally by specific trade associations focusing on specific industrial sectors."
    }
]

os.makedirs("data", exist_ok=True)
with open("data/test_set.json", "w") as f:
    json.dump(test_set, f, indent=2)

print("Manually created data/test_set.json for evaluation.")
