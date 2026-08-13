import streamlit as st
import subprocess
import json
import tempfile
import sys
from pathlib import Path
import os

def run_script(script_path: str, config: dict, cwd: str = None):
    """
    Executes a python script as a subprocess, passing config as a temporary JSON file via --config.
    Streams the output (stdout and stderr) to a Streamlit placeholder.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
        config_file = f.name
    
    # We use the same python executable that is running Streamlit (.venv)
    cmd = [sys.executable, script_path, "--config", config_file]
    
    st.markdown(f"**Executando:** `{script_path}`")
    
    log_placeholder = st.empty()
    logs = []
    
    try:
        # Start the subprocess
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=cwd,
            encoding='utf-8',
            errors='replace'
        )
        
        # Stream the output
        for line in iter(process.stdout.readline, ''):
            clean_line = line.rstrip()
            logs.append(clean_line)
            # Update log display
            # To avoid severe performance issues with huge logs, we only keep the last 500 lines in the UI while running
            display_logs = logs[-500:] if len(logs) > 500 else logs
            log_placeholder.code('\n'.join(display_logs), language='shell')
            
        process.stdout.close()
        return_code = process.wait()
        
        if return_code == 0:
            st.success("✅ Execução concluída com sucesso!")
        else:
            st.error(f"❌ Falha na execução. Código de saída: {return_code}")
            
    except Exception as e:
        st.error(f"Erro fatal ao tentar rodar o script: {e}")
    finally:
        # Cleanup temp file
        try:
            os.remove(config_file)
        except OSError:
            pass
