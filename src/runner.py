import streamlit as st
import subprocess
import json
import tempfile
import sys
import os
import math
import queue
import threading
import time

# The scripts do not emit numeric progress, so the bar advances by wall-clock
# time using an asymptotic curve approaching _PROGRESS_CAP. This keeps the bar
# moving even during long silent operations (e.g. a heavy pandas step that
# prints nothing for tens of seconds), and only reaches 100% when the process
# actually ends.
_PROGRESS_CAP = 0.95      # never reach 100% until the process finishes
_PROGRESS_TAU = 90.0      # seconds to (1-1/e) of the cap; ~63% by 90s
_POLL_TIMEOUT = 0.3       # seconds between progress-bar refreshes

# Distinct EOF sentinel pushed onto the queue by the reader thread when stdout
# closes. Using a unique object (not None) avoids ambiguity with empty lines.
_EOF = object()


def run_script(script_path: str, config: dict, cwd: str = None):
    """
    Executes a python script as a subprocess, passing config as a temporary JSON
    file via --config. Streams stdout/stderr to a Streamlit placeholder below a
    progress bar that advances by elapsed time and completes when the script ends.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
        config_file = f.name

    # We use the same python executable that is running Streamlit (.venv)
    cmd = [sys.executable, script_path, "--config", config_file]

    st.markdown(f"**Executando:** `{script_path}`")

    progress_bar = st.progress(0.0, text="Iniciando execução…")
    log_placeholder = st.empty()
    logs = []

    # Force the subprocess to use UTF-8 for stdin/stdout/stderr regardless of the
    # system locale. On Windows the default ANSI codepage (cp1252) can't encode the
    # box-drawing characters (╔═╗) the scripts print, which raised UnicodeEncodeError.
    sub_env = os.environ.copy()
    sub_env["PYTHONIOENCODING"] = "utf-8"

    start = time.monotonic()
    process = None
    try:
        # Start the subprocess
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=cwd,
            env=sub_env,
            encoding='utf-8',
            errors='replace'
        )

        # Read lines on a daemon thread into a queue so the main loop can poll with
        # a timeout: this lets the progress bar advance by elapsed time even when no
        # new output has arrived (a blocking readline would freeze the bar).
        out_q = queue.Queue()

        def _reader():
            try:
                for line in iter(process.stdout.readline, ''):
                    out_q.put(line.rstrip("\r\n"))
            finally:
                process.stdout.close()
                out_q.put(_EOF)  # EOF sentinel

        reader = threading.Thread(target=_reader, daemon=True)
        reader.start()

        def _bar_fraction(elapsed: float) -> float:
            return _PROGRESS_CAP * (1.0 - math.exp(-elapsed / _PROGRESS_TAU))

        # Stream the output while advancing the bar by wall-clock time.
        saw_eof = False
        while not saw_eof:
            try:
                item = out_q.get(timeout=_POLL_TIMEOUT)
            except queue.Empty:
                # No new output this tick; refresh the bar by elapsed time only.
                elapsed = time.monotonic() - start
                frac = min(_bar_fraction(elapsed), 0.99)
                progress_bar.progress(frac, text=f"Executando… {int(frac * 100)}% · {elapsed:.0f}s")
                continue

            # item is either a real line (str, possibly empty) or the _EOF sentinel.
            if item is _EOF:
                saw_eof = True
                break

            elapsed = time.monotonic() - start
            logs.append(item)
            # To avoid severe performance issues with huge logs, we only keep the
            # last 500 lines in the UI while running.
            display_logs = logs[-500:] if len(logs) > 500 else logs
            log_placeholder.code('\n'.join(display_logs), language='shell')
            frac = min(_bar_fraction(elapsed), 0.99)
            progress_bar.progress(frac, text=f"Executando… {int(frac * 100)}% · {elapsed:.0f}s")

        reader.join(timeout=2.0)
        return_code = process.wait()
        elapsed = time.monotonic() - start

        if return_code == 0:
            progress_bar.progress(1.0, text=f"Concluído · {elapsed:.0f}s")
            st.success("✅ Execução concluída com sucesso!")
        else:
            # Don't fake 100% on failure: leave the bar where time put it.
            frac = min(_bar_fraction(elapsed), 0.99)
            progress_bar.progress(frac, text=f"Execução falhou (código {return_code}) · {elapsed:.0f}s")
            st.error(f"❌ Falha na execução. Código de saída: {return_code}")

    except Exception as e:
        elapsed = time.monotonic() - start
        frac = min(_PROGRESS_CAP * (1.0 - math.exp(-elapsed / _PROGRESS_TAU)), 0.99)
        try:
            progress_bar.progress(frac, text="Erro ao iniciar a execução")
        except Exception:
            pass
        st.error(f"Erro fatal ao tentar rodar o script: {e}")
    finally:
        # Cleanup temp file
        try:
            os.remove(config_file)
        except OSError:
            pass
