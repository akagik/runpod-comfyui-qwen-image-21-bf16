#!/usr/bin/env python3
"""Generate two 16:9 adult visual-novel character material tests in full BF16."""

import argparse
import importlib.metadata
import json
import os
import subprocess
import threading
import time
from pathlib import Path

import torch
from diffusers import QwenImage21Pipeline


MODEL_ID = "Qwen/Qwen-Image-2.1"
MODEL_REVISION = "790c92633540aa0cb11d9abf19eb46d861714758"
ROOT = Path(os.environ.get("RUNPOD_VOLUME_ROOT", "/workspace")) / "qwen-image-2.1-bf16"
OUT = ROOT / "outputs" / "novel-game-16x9"
WIDTH = 2752
HEIGHT = 1536
STEPS = 40

PROMPTS = [
    {
        "name": "direct_ja",
        "seed": 42,
        "prompt": """
リアルで高品質な日本の恋愛ノベルゲーム用の一枚絵。舞台は現代の日本、秋葉原。
UI、字幕、文章、ロゴ、透かし、看板の文字は一切描かない。
登場人物は20歳の成人の日本人女性。超かわいく華やかな美人で、身長156cmほど、
豊かな胸元とスレンダーな体型。カメラへ視線を向けている。
頭から太ももまでが画面内に入る、目線の高さの16:9横長構図。
彼女は秋葉原の猫耳コンセプトカフェ店内で、カウンター席の丸いバースツールに座っている。
背景にはピンク調のカウンターテーブル、カラフルなカクテルグラス、
上品でかわいい猫モチーフの内装が見える。
人気の黒猫キャストらしい、少しあざとく魅力的な仕草。首をわずかに傾げ、
愛らしく親しみのある微笑み。
艶やかな黒髪のショートボブ、ふわふわの黒い猫耳カチューシャ。
首元には小さな金色の鈴が付いた細い黒革のチョーカー。
黒のタイトなノースリーブのミニワンピース。胸元は深いスリット状のネックラインで、
自然な谷間が見える。腰の後ろから黒い猫の尻尾が伸びている。
自然でリアルな肌、繊細な髪、整った手指、柔らかなピンクの店内照明、
シネマティックな被写界深度、実写写真のような質感。
""".strip(),
    },
    {
        "name": "qwen_refined_ja",
        "seed": 43,
        "prompt": """
日本の成人向け恋愛ビジュアルノベルで使う、実写調のキャラクター立ち絵に近いイベントCG。
画面比率は16:9。カメラは人物と同じ目線の高さ。20歳の成人の日本人女性を、
頭頂から太ももまで余裕を持って画面内に収める。人物の全身を切り過ぎず、
顔と衣装が読み取りやすい構図。彼女はレンズをまっすぐ見つめる。

場所は秋葉原にある高級感とかわいさを両立した猫耳コンセプトカフェ。
ピンク色のカウンター、丸いバースツール、色鮮やかなカクテルグラス、
さりげない猫型の装飾。背景は人物を邪魔しない程度にぼかす。

女性は店の看板キャスト。小柄でスレンダー、華やかで非常にかわいい顔立ち、
豊かな胸元。丸いバースツールに自然に腰掛け、片手を頬の近くへ添える
少しあざとい仕草。首を軽く傾けて、親密で愛らしい微笑みを見せる。
艶のある黒髪ショートボブ、左右対称でふわふわした黒い猫耳カチューシャ。
小さな金の鈴が付いた細い黒革チョーカー。
衣装は黒いタイトなノースリーブのミニワンピース。
深いスリット状のネックラインから自然な谷間が見える。
黒い猫の尻尾は腰の後ろに正しく取り付けられ、椅子の横へ自然にカーブする。

日本人女性らしい自然な顔と肌、左右の目と手指の形を正確に描く。
ピンクと暖色の柔らかな店内照明、瞳の小さなキャッチライト、
繊細な髪の毛、現実的な布地、上品で艶のある恋愛ゲーム用ビジュアル。
画面内にUI、会話ウィンドウ、文字、字幕、ロゴ、透かしを置かない。
""".strip(),
    },
    {
        "name": "production_refined_ja",
        "seed": 44,
        "prompt": """
日本の恋愛ノベルゲームで使う、実写写真のように精密で魅力的なイベントCG。16:9横長。
登場人物は20歳の成人の日本人女性。カメラは人物から十分に離れた目線の高さに置き、
黒い猫耳の先端から両方の太ももの中ほどまでを余裕を持って完全に画面内へ収める。
丸いバースツールの座面も見せる。顔、両手、衣装、座っている姿勢が明瞭に読める。
人物は画面中央より少し右に配置し、レンズをまっすぐ見つめる。

秋葉原の上品でかわいい猫耳コンセプトカフェ。背景は無地のピンクの壁面、
文字のないピンク色のカウンター、ラベルのないカラフルなカクテルグラス、
シンプルな猫型の装飾と柔らかな間接照明だけで構成する。
メニュー、看板、黒板、ポスター、額、ラベル、文字が入りそうな物を店内に置かない。

女性は小柄でスレンダー、豊かな胸元、華やかで非常にかわいい顔立ちの看板キャスト。
丸いバースツールへ自然に腰掛け、片手の指先を頬の近くへ添え、もう一方の手は太ももに置く。
首を少し傾け、親密で愛らしい微笑みを見せる。
艶やかな黒髪の短いボブ、左右対称のふわふわした黒い猫耳カチューシャ。
装飾は首中央の、小さな金の鈴が一つだけ付いた細い黒革チョーカー。
猫耳には鈴やアクセサリーを付けない。
黒いタイトなノースリーブのミニワンピース。胸元は深いスリット状のネックラインで、
自然な谷間が見える。黒い猫の尻尾は腰の後ろから一本だけ伸び、椅子の横へ自然に曲がる。

自然な日本人女性の顔と肌、正しい左右の目、左右それぞれ五本の自然な指、
繊細な髪、現実的な黒い布地、ピンクと暖色の柔らかな照明、瞳のキャッチライト、
背景は浅い被写界深度。UI、会話欄、字幕、文字、ロゴ、透かしは一切描かない。
""".strip(),
    },
]


class SmiSampler:
    def __init__(self):
        self.stop = threading.Event()
        self.max_mib = 0
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self.stop.is_set():
            try:
                value = subprocess.check_output(
                    [
                        "nvidia-smi",
                        "--query-gpu=memory.used",
                        "--format=csv,noheader,nounits",
                        "-i",
                        "0",
                    ],
                    text=True,
                    timeout=5,
                ).strip().splitlines()[0]
                self.max_mib = max(self.max_mib, int(value))
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
            self.stop.wait(0.5)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(timeout=6)


def gib(value):
    return round(value / 1024**3, 3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--only",
        choices=[item["name"] for item in PROMPTS],
        help="Generate one named prompt instead of the full comparison.",
    )
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    assert torch.cuda.is_available()
    assert torch.cuda.is_bf16_supported()

    pipe = QwenImage21Pipeline.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        torch_dtype=torch.bfloat16,
        cache_dir=ROOT / "hf-cache" / "hub",
    ).to("cuda")
    dtypes = {
        "transformer": str(pipe.transformer.dtype),
        "text_encoder": str(next(pipe.text_encoder.parameters()).dtype),
        "vae": str(next(pipe.vae.parameters()).dtype),
    }
    assert pipe.transformer.dtype == torch.bfloat16

    metrics = {
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "precision": "BF16",
        "gpu": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "transformers": importlib.metadata.version("transformers"),
        "diffusers": importlib.metadata.version("diffusers"),
        "width": WIDTH,
        "height": HEIGHT,
        "steps": STEPS,
        "dtypes": dtypes,
        "images": [],
    }

    selected_prompts = [
        item for item in PROMPTS if args.only is None or item["name"] == args.only
    ]
    for item in selected_prompts:
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()
        start = time.perf_counter()
        with SmiSampler() as smi, torch.inference_mode():
            image = pipe(
                prompt=item["prompt"],
                width=WIDTH,
                height=HEIGHT,
                num_inference_steps=STEPS,
                generator=torch.Generator(device="cuda").manual_seed(item["seed"]),
            ).images[0]
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - start
        path = OUT / f"qwen21_novel_game_16x9_{item['name']}_seed{item['seed']}.png"
        image.save(path)
        result = {
            "name": item["name"],
            "seed": item["seed"],
            "prompt": item["prompt"],
            "path": str(path),
            "seconds": round(elapsed, 3),
            "peak_allocated_gib": gib(torch.cuda.max_memory_allocated()),
            "peak_reserved_gib": gib(torch.cuda.max_memory_reserved()),
            "nvidia_smi_peak_mib": smi.max_mib,
            "output_size": list(image.size),
            "output_mode": image.mode,
        }
        metrics["images"].append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)

    metrics["status"] = "complete"
    metrics_name = f"metrics_{args.only}.json" if args.only else "metrics.json"
    (OUT / metrics_name).write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
