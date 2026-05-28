import logging
import yaml
import mlflow
import sys

logger = logging.getLogger(__name__)

def check_quality(config_path: str = "configs/config.yaml"):
    """Checks latest MLflow metrics against thresholds."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        
    thresholds = config['evaluation']
    
    # Connect to MLflow
    mlflow.set_tracking_uri(config['mlflow']['tracking_uri'])
    client = mlflow.tracking.MlflowClient()
    experiment = client.get_experiment_by_name(config['mlflow']['experiment_name'])
    
    if not experiment:
        logger.error(f"Experiment {config['mlflow']['experiment_name']} not found.")
        sys.exit(1)
        
    runs = client.search_runs(experiment.experiment_id, order_by=["attributes.start_time DESC"], max_results=1)
    
    if not runs:
        logger.error("No runs found in MLflow.")
        sys.exit(1)
        
    latest_run = runs[0]
    metrics = latest_run.data.metrics
    
    passed = True
    print("\n--- Quality Gate ---")
    
    check_map = {
        "faithfulness": thresholds['faithfulness_threshold'],
        "answer_relevancy": thresholds['answer_relevancy_threshold'],
        "context_recall": thresholds['context_recall_threshold']
    }
    
    for metric, threshold in check_map.items():
        val = metrics.get(metric, 0)
        status = "PASS" if val >= threshold else "FAIL"
        print(f"{metric}: {val:.4f} (Threshold: {threshold}) -> {status}")
        if status == "FAIL":
            passed = False
            
    if passed:
        print("\nALL METRICS PASSED")
        sys.exit(0)
    else:
        print("\nQUALITY GATE FAILED")
        sys.exit(1)

if __name__ == "__main__":
    check_quality()
