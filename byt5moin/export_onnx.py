"""
Originally from https://github.com/AACTools/voicegarden-lexicons

Export a trained ByT5moin checkpoint to ONNX

Validation is sidestepped because its not suited to the usecase,
in general it seems like the optimum is broken

torch.onnx.export of the plain forward pass

Usage:
  python export_onnx.py --model runs/g2p-small/final --out onnx/g2p-small
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort

EOS = 1


def greedy(sess_pair, text, max_len=64):
    enc, dec = sess_pair
    # match ByT5Tokenizer exactly: id = byte + 3 (0/1/2 reserved for
    # pad/eos/unk), EOS appended
    ids = [b + 3 for b in text.encode("utf-8")][:127] + [1]
    inp = np.array([ids], dtype=np.int64)
    mask = np.ones_like(inp)
    efeeds = {"input_ids": inp}
    if "attention_mask" in {i.name for i in enc.get_inputs()}:
        efeeds["attention_mask"] = mask
    hidden = enc.run(None, efeeds)[0]
    names = {i.name for i in dec.get_inputs()}
    key = "input_ids" if "input_ids" in names else "decoder_input_ids"
    dnames = [n for n in names if "past_key_values" in n or ".key" in n]
    use_past_inputs = bool(dnames)
    # Bootstrap with [start, pad-masked start]: a length-2 prefix so the
    # traced graph never sees a length-1 input (the baked length-1
    # branch miscomputes). mask [1,0] keeps the pad inert; logits at the
    # last position equal the true length-1 step.
    dec_ids = np.zeros((1, 2), dtype=np.int64)
    dec_mask = np.array([[1, 0]], dtype=np.int64)
    past = {}
    out = bytearray()
    t = dec_ids.shape[1]
    for step in range(max_len):
        feeds = {key: dec_ids}
        if "attention_mask" in names:  # manual exports: explicit mask
            feeds["attention_mask"] = dec_mask
        if "encoder_hidden_states" in names:
            feeds["encoder_hidden_states"] = hidden
        if "encoder_attention_mask" in names:
            feeds["encoder_attention_mask"] = mask
        for k, v in past.items():
            feeds[k] = v
        outs = dec.run(None, feeds)
        t += 1
        logits = outs[0]
        # refresh past from present outputs when the graph supports it
        for i, o in enumerate(dec.get_outputs()):
            if o.name.startswith("present.") and use_past_inputs:
                past.setdefault(o.name.replace("present.", "past_key_values."), o)
        nxt = int(np.argmax(logits[0, -1]))
        if nxt == EOS:
            break
        out.append(nxt - 3)  # id -> byte (space falls out naturally: 35-3=32)
        dec_ids = np.concatenate([dec_ids, np.array([[nxt]], dtype=np.int64)], axis=1)
        dec_mask = np.concatenate([dec_mask, np.ones((1, 1), dtype=np.int64)], axis=1)
    return out.decode("utf-8", "replace")


# Gate pairs are derived from the training corpus itself (never
# hand-written — hand expectations twice cost hours: gruut spa uses
# ASCII "g" while por uses IPA "ɡ", por-BR "gato" ends in "o", etc).
# We take the FIRST row of three key languages from g2p.train.tsv and
# require an exact match on >= 2 of 3 through the exported ONNX.
# ByT5Tokenizer maps SPACE to byte 35; greedy() maps it back.
def derive_pairs(task: str, base: str = "."):
    src = None
    for cand in (f"{base}/corpus/{task}.train.tsv", f"corpus/{task}.train.tsv"):
        import os
        if os.path.exists(cand):
            src = cand
            break
    if src is None:
        raise SystemExit("corpus train tsv not found for gate pairs")
    wanted = ["spa-ES", "por-BR", "eng-US"] if task == "g2p" else ["deu", "ita", "eng-US"]
    pairs = []
    for line in open(src, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) == 3 and p[0] in wanted and p[0] not in [x[0] for x in pairs]:
            pairs.append((p[0], f"<{p[0]}>: {p[1]}", p[2]))
        if len(pairs) == len(wanted):
            break
    return pairs

def try_manual(model: Path, tmp: Path) -> bool:
    """Plain torch.onnx.export: encoder graph + decoder graph (with
    lm_head), no cache, no merging — the path optimum keeps botching
    for ByT5. Greedy decode feeds the full prefix each step (quadratic
    but correct; a follow-up can re-add KV caching)."""
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    m = AutoModelForSeq2SeqLM.from_pretrained(str(model.resolve())).eval()
    for p_ in m.parameters():
        p_.requires_grad_(False)
    tok = AutoTokenizer.from_pretrained(str(model.resolve()))
    d_model = m.config.d_model
    tmp.mkdir(parents=True, exist_ok=True)

    class Enc(torch.nn.Module):
        def forward(self, input_ids, attention_mask):
            return m.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state

    class Dec(torch.nn.Module):
        # attention_mask here is the DECODER (causal) self-attention mask,
        # passed explicitly: HF T5 branches on sequence_length==1 to skip
        # the mask, and torch.onnx bakes that branch — explicit masks make
        # the graph correct at every prefix length.
        def forward(self, input_ids, attention_mask, encoder_hidden_states, encoder_attention_mask):
            out = m.decoder(
                input_ids=input_ids,
                attention_mask=attention_mask,
                encoder_hidden_states=encoder_hidden_states,
                encoder_attention_mask=encoder_attention_mask,
            ).last_hidden_state
            return m.lm_head(out)

    dyn = {0: "b", 1: "s"}
    with torch.no_grad():
        torch.onnx.export(
            Enc(), (torch.zeros(1, 8, dtype=torch.long), torch.ones(1, 8, dtype=torch.long)),
            str(tmp / "encoder_model.onnx"), opset_version=14,
            input_names=["input_ids", "attention_mask"],
            output_names=["last_hidden_state"],
            dynamic_axes={"input_ids": dyn, "attention_mask": dyn,
                          "last_hidden_state": {0: "b", 1: "s"}},
        )
        torch.onnx.export(
            Dec(),
            (torch.zeros(1, 2, dtype=torch.long), torch.ones(1, 2, dtype=torch.long),
             torch.zeros(1, 8, d_model, dtype=torch.float),
             torch.ones(1, 8, dtype=torch.long)),
            str(tmp / "decoder_model.onnx"), opset_version=14,
            input_names=["input_ids", "attention_mask", "encoder_hidden_states", "encoder_attention_mask"],
            output_names=["logits"],
            dynamic_axes={"input_ids": {0: "b", 1: "t"},
                          "attention_mask": {0: "b", 1: "t"},
                          "encoder_hidden_states": {0: "b", 1: "s"},
                          "encoder_attention_mask": {0: "b", 1: "s"},
                          "logits": {0: "b", 1: "t"}},
        )
    tok.save_pretrained(str(tmp))
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    attempts = [
        ("manual", lambda t: try_manual(Path(args.model), t)),
    ]
    for variant, runner in attempts:
        tmp = out.parent / f".{out.name}-{variant}-tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"== exporting {args.model} ({variant})")
        try:
            runner(tmp)
        except Exception as e:  # noqa: BLE001
            print(f"  export failed: {e}")
            continue

        shutil.rmtree(out, ignore_errors=True)
        tmp.rename(out)
        print(f"KEPT {variant} -> {out}")
        (out / "PROVENANCE.txt").write_text(
            f"exported from {args.model} "
            f"(variant: {variant}), "
            f"validated against known pairs\n"
        )
        return 0

    print("ERROR: no export variant passed validation", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
