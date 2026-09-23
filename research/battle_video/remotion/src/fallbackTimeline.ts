// A short stand-in so `remotion studio` and a toolchain render work before the battle
// record exists.  The real timeline is passed with --props at render time.
import type { Beat } from "./Documentary";

export const beats: Beat[] = [
  {
    id: "fallback",
    chapter: "占位",
    narration: "真正的解说词由对局记录生成。",
    seconds: 4,
    visual: { kind: "title", title: "等待时间线", subtitle: "build_timeline.py 尚未运行" },
  },
];
