
import subprocess
import time
import sys
import logging
import random
import os

logging.basicConfig(
    filename='orchestrator.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

PYTHON_EXECUTABLE = sys.executable

def run_scraper(script_path, user_data_dir=None, extra_args=None):
    """Run a Zillow scraper script as a subprocess with a unique user data dir and optional extra args."""
    logging.info(f"Starting {script_path}")
    cmd = [PYTHON_EXECUTABLE, script_path]
    process = subprocess.Popen(cmd)
    return process

def main():
    logging.info("Orchestrator starting scrapers sequentially...")
    scraper_scripts = [
        'zillow_scraper.py',
        'realtor_scraper.py',
        'redfin_scraper.py'
    ]
    processes = []
    for idx, script in enumerate(scraper_scripts):
        logging.info(f"Starting {script}...")
        proc = run_scraper(script)
        processes.append(proc)
        if idx < len(scraper_scripts) - 1:
            logging.info(f"Waiting 30 seconds before starting next scraper...")
            time.sleep(30)
    # Wait for all scrapers to finish
    for idx, proc in enumerate(processes):
        proc.wait()
        logging.info(f"{scraper_scripts[idx]} exited with code {proc.returncode}")

    # Run listings_compiler.py after all scrapers are done
    logging.info("Running listings_compiler.py...")
    compiler_proc = subprocess.Popen([PYTHON_EXECUTABLE, 'listings_compiler.py'])
    compiler_proc.wait()
    logging.info(f"listings_compiler.py exited with code {compiler_proc.returncode}")

    # Run nestfully_bot.py after listings_compiler.py is done
    logging.info("Running nestfully_bot.py...")
    nestfully_proc = subprocess.Popen([PYTHON_EXECUTABLE, 'nestfully_bot.py'])
    nestfully_proc.wait()
    logging.info(f"nestfully_bot.py exited with code {nestfully_proc.returncode}")
    logging.info("Orchestration complete.")

if __name__ == "__main__":
    main()
