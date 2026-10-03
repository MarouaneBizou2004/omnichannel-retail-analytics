"""
End-to-End Orchestrator Pipeline
Executes data generation, cleaning, relational Star Schema ETL,
exploratory analysis, feature engineering, ML model training, and batch scoring.
"""

import sys
import time
from pathlib import Path
import logging

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from src.data.make_dataset import main as generate_raw_data
from src.data.clean_data import DataCleaningPipeline
from src.utils.database import WarehouseManager
from src.analysis.eda import EDAViewer
from src.features.build_features import FeatureBuilder
from src.models.train_model import ChurnModelTrainer
from src.models.predict import BatchChurnPredictor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("PipelineOrchestrator")

def run_pipeline() -> None:
    start_time = time.time()
    print("=" * 80)
    print("      AURA RETAIL GROUP - OMNICHANNEL ANALYTICS & ML PLATFORM")
    print("                 END-TO-END PIPELINE ORCHESTRATION")
    print("=" * 80)
    
    # Step 1: Raw Data Generation
    logger.info(">>> Step 1/7: Generating Raw Multi-Source Data...")
    generate_raw_data()
    
    # Step 2: Data Cleaning & Processing
    logger.info(">>> Step 2/7: Executing Data Cleaning & Validation Pipeline...")
    cleaner = DataCleaningPipeline()
    cleaner.run()
    
    # Step 3: Relational Warehouse ETL
    logger.info(">>> Step 3/7: Initializing Kimball Star Schema Database & Loading Facts/Dims...")
    wh_manager = WarehouseManager()
    wh_manager.execute_full_etl()
    
    # Step 4: Exploratory Analysis & Publication Figures
    logger.info(">>> Step 4/7: Generating Business Intelligence Figures & Visualizations...")
    eda = EDAViewer()
    eda.run_all()
    
    # Step 5: Feature Engineering & Target Formulation
    logger.info(">>> Step 5/7: Building Leakage-Proof RFM & Velocity Feature Matrix...")
    builder = FeatureBuilder()
    builder.run()
    
    # Step 6: ML Training, Benchmark, Tuning & Financial Threshold Optimization
    logger.info(">>> Step 6/7: Training Churn Models & Optimizing Campaign Threshold...")
    trainer = ChurnModelTrainer()
    trainer.run()
    
    # Step 7: Batch Retention Scoring & Action Prescription
    logger.info(">>> Step 7/7: Scoring Customer Base & Generating Targeted Interventions...")
    predictor = BatchChurnPredictor()
    predictor.run()
    
    elapsed = time.time() - start_time
    print("=" * 80)
    print(f" PIPELINE COMPLETED SUCCESSFULLY IN {elapsed:.2f} SECONDS!")
    print(" All processed tables, figures, SQL schemas, and models are production-ready.")
    print("=" * 80)

if __name__ == "__main__":
    run_pipeline()
