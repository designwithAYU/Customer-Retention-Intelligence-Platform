"""
nb_utils.py
Lightweight notebook builder that ACTUALLY EXECUTES each code cell (in a
shared namespace, just like a real Jupyter kernel) and embeds the genuine
stdout and matplotlib figure outputs into a valid nbformat v4 .ipynb file.

This environment has no Jupyter/nbformat package installed and no network
access to install one, so this utility hand-builds the notebook JSON
structure directly rather than faking pre-written "outputs".
"""
import io
import base64
import contextlib
import json
import traceback

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


class NotebookBuilder:
    def __init__(self):
        self.cells = []
        self.namespace = {"__name__": "__notebook__"}
        self._exec_count = 0

    def markdown(self, text):
        self.cells.append({
            "cell_type": "markdown",
            "metadata": {},
            "source": text.splitlines(keepends=True),
        })

    def code(self, source, capture_plots=True):
        self._exec_count += 1
        outputs = []
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                exec(compile(source, "<notebook_cell>", "exec"), self.namespace)
            text = buf.getvalue()
            if text:
                outputs.append({
                    "output_type": "stream",
                    "name": "stdout",
                    "text": text.splitlines(keepends=True),
                })
            if capture_plots:
                fignums = plt.get_fignums()
                for num in fignums:
                    fig = plt.figure(num)
                    img_buf = io.BytesIO()
                    fig.savefig(img_buf, format="png", dpi=110, bbox_inches="tight")
                    img_buf.seek(0)
                    b64 = base64.b64encode(img_buf.read()).decode("ascii")
                    outputs.append({
                        "output_type": "display_data",
                        "data": {"image/png": b64, "text/plain": ["<Figure>"]},
                        "metadata": {},
                    })
                    plt.close(fig)
        except Exception as e:
            tb = traceback.format_exc()
            outputs.append({
                "output_type": "error",
                "ename": type(e).__name__,
                "evalue": str(e),
                "traceback": tb.splitlines(),
            })
            print(f"[NOTEBOOK CELL ERROR] {e}\n{tb}")

        self.cells.append({
            "cell_type": "code",
            "execution_count": self._exec_count,
            "metadata": {},
            "outputs": outputs,
            "source": source.splitlines(keepends=True),
        })

    def write(self, path):
        nb = {
            "cells": self.cells,
            "metadata": {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python", "version": "3.12"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        with open(path, "w") as f:
            json.dump(nb, f, indent=1)
        print(f"Notebook written: {path}")
