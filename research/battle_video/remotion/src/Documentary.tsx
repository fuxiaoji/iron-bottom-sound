import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  staticFile,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

/** One beat: a chapter of the record, its narration, and what the frame shows. */
export type Beat = {
  id: string;
  chapter: string;
  narration: string;
  seconds: number;
  audio?: string | null;
  thinking?: string;
  overlays?: { text: string; kind?: string }[];
  visual: {
    kind: string;
    title?: string;
    subtitle?: string;
    footer?: string;
    lines?: string[];
    bars?: { label: string; value: number }[];
    board?: { turn: number; phase: string };
    viewpoint?: string;
    side?: string;
    labels?: string[];
  };
};

export type DocumentaryProps = {
  beats: Beat[];
  title: string;
};

const OCEAN = "#0d1f30";
const PANEL = "#14283c";
const TEXT = "#e1e8f0";
const DIM = "#8fa3b8";
const AXIS = "#c0503c";
const ALLIES = "#4a7fd4";
const ACCENT = "#d8b25a";

const FONT = "Songti SC, Noto Serif CJK SC, STSong, serif";
const MONO = "SF Mono, Menlo, monospace";

const frameName = (turn: number, phase: string, viewpoint: string, crop = true) =>
  `${crop ? "crop-" : ""}t${String(turn).padStart(2, "0")}-${phase}-${viewpoint}.png`;

const KenBurns: React.FC<{
  src: string;
  zoom?: number;
  pan?: number;
  fit?: "width" | "height";
}> = ({ src, zoom = 0.08, pan = 18, fit = "height" }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const t = interpolate(frame, [0, durationInFrames], [0, 1], {
    extrapolateRight: "clamp",
  });
  const scale = 1 + zoom * t;
  const x = -pan * t;
  return (
    <Img
      src={staticFile(src)}
      style={{
        width: "100%",
        height: "100%",
        objectFit: fit === "height" ? "contain" : "cover",
        transform: `scale(${scale}) translateX(${x}px)`,
        transformOrigin: "center",
      }}
    />
  );
};

const Caption: React.FC<{ text: string; chapter: string }> = ({ text, chapter }) => (
  <div
    style={{
      position: "absolute",
      left: 0,
      right: 0,
      bottom: 0,
      padding: "26px 64px 40px",
      background: "linear-gradient(to top, rgba(6,14,22,0.94), rgba(6,14,22,0))",
    }}
  >
    <div style={{ color: ACCENT, fontFamily: FONT, fontSize: 22, letterSpacing: 2 }}>
      {chapter}
    </div>
    <div
      style={{
        color: TEXT,
        fontFamily: FONT,
        fontSize: 38,
        lineHeight: 1.5,
        marginTop: 10,
        maxWidth: 1660,
      }}
    >
      {text}
    </div>
  </div>
);

const TitleCard: React.FC<{ visual: Beat["visual"] }> = ({ visual }) => (
  <AbsoluteFill
    style={{
      background: `radial-gradient(circle at 30% 20%, #16324a 0%, ${OCEAN} 60%)`,
      justifyContent: "center",
      alignItems: "center",
      textAlign: "center",
      padding: 80,
    }}
  >
    <div style={{ color: TEXT, fontFamily: FONT, fontSize: 76, lineHeight: 1.3 }}>
      {visual.title}
    </div>
    {visual.subtitle ? (
      <div style={{ color: DIM, fontFamily: FONT, fontSize: 34, marginTop: 28 }}>
        {visual.subtitle}
      </div>
    ) : null}
    {visual.footer ? (
      <div
        style={{
          color: ACCENT,
          fontFamily: MONO,
          fontSize: 22,
          marginTop: 56,
          letterSpacing: 1,
        }}
      >
        {visual.footer}
      </div>
    ) : null}
  </AbsoluteFill>
);

const Card: React.FC<{ visual: Beat["visual"] }> = ({ visual }) => (
  <AbsoluteFill style={{ background: OCEAN, padding: "90px 120px" }}>
    <div
      style={{
        color: ACCENT,
        fontFamily: FONT,
        fontSize: 30,
        letterSpacing: 3,
        borderBottom: `2px solid ${ACCENT}`,
        paddingBottom: 18,
        alignSelf: "flex-start",
      }}
    >
      {visual.title}
    </div>
    <div style={{ marginTop: 56 }}>
      {(visual.lines || []).map((line, index) => (
        <div
          key={index}
          style={{
            color: TEXT,
            fontFamily: FONT,
            fontSize: 40,
            lineHeight: 1.65,
            marginBottom: 18,
            display: "flex",
            gap: 20,
          }}
        >
          <span style={{ color: ACCENT, fontFamily: MONO }}>{`0${index + 1}`}</span>
          <span>{line.replace(/\*\*/g, "")}</span>
        </div>
      ))}
    </div>
  </AbsoluteFill>
);

const Oob: React.FC<{ visual: Beat["visual"] }> = ({ visual }) => (
  <AbsoluteFill style={{ background: OCEAN, padding: "80px 100px" }}>
    <div style={{ color: ACCENT, fontFamily: FONT, fontSize: 34, letterSpacing: 3 }}>
      {visual.title}
    </div>
    <div style={{ display: "flex", marginTop: 48, gap: 80 }}>
      {["axis", "allies"].map((side) => (
        <div key={side} style={{ flex: 1 }}>
          <div
            style={{
              color: side === "axis" ? AXIS : ALLIES,
              fontFamily: FONT,
              fontSize: 34,
              marginBottom: 22,
            }}
          >
            {side === "axis" ? "日方" : "美方"}
          </div>
          {(visual.lines || [])
            .filter((line) =>
              side === "axis"
                ? line.startsWith("日方")
                : line.startsWith("美方"),
            )
            .map((line, index) => (
              <div
                key={index}
                style={{
                  color: TEXT,
                  fontFamily: FONT,
                  fontSize: 27,
                  lineHeight: 1.6,
                  marginBottom: 16,
                }}
              >
                {line}
              </div>
            ))}
        </div>
      ))}
    </div>
  </AbsoluteFill>
);

const BoardFrame: React.FC<{ visual: Beat["visual"]; overlays?: Beat["overlays"] }> = ({
  visual,
  overlays,
}) => {
  const board = visual.board!;
  const viewpoint = visual.viewpoint || "god";
  return (
    <AbsoluteFill style={{ background: OCEAN }}>
      <KenBurns src={`frames/${frameName(board.turn, board.phase, viewpoint)}`} />
      <div
        style={{
          position: "absolute",
          top: 36,
          left: 64,
          color: TEXT,
          fontFamily: FONT,
          fontSize: 32,
          background: "rgba(6,14,22,0.7)",
          padding: "10px 22px",
          borderRadius: 6,
        }}
      >
        {visual.title}
      </div>
      {(overlays || []).length ? (
        <div
          style={{
            position: "absolute",
            top: 120,
            right: 60,
            width: 620,
            background: "rgba(8,18,28,0.82)",
            borderLeft: `4px solid ${ACCENT}`,
            padding: "18px 24px",
          }}
        >
          {(overlays || []).slice(0, 4).map((item, index) => (
            <div
              key={index}
              style={{
                color: TEXT,
                fontFamily: FONT,
                fontSize: 26,
                lineHeight: 1.5,
                marginBottom: 10,
              }}
            >
              {item.text}
            </div>
          ))}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

const Compare: React.FC<{ visual: Beat["visual"] }> = ({ visual }) => {
  const board = visual.board!;
  const views = ["god", "axis", "allies"];
  const labels = visual.labels || ["上帝视角", "日方所见", "美方所见"];
  return (
    <AbsoluteFill style={{ background: OCEAN, padding: "70px 40px 40px" }}>
      <div
        style={{
          color: ACCENT,
          fontFamily: FONT,
          fontSize: 32,
          marginLeft: 40,
          marginBottom: 18,
        }}
      >
        {visual.title}
      </div>
      <div style={{ display: "flex", gap: 18, flex: 1 }}>
        {views.map((view, index) => (
          <div key={view} style={{ flex: 1, display: "flex", flexDirection: "column" }}>
            <div
              style={{
                color: view === "axis" ? AXIS : view === "allies" ? ALLIES : ACCENT,
                fontFamily: FONT,
                fontSize: 26,
                textAlign: "center",
                marginBottom: 8,
              }}
            >
              {labels[index]}
            </div>
            <div
              style={{
                flex: 1,
                background: PANEL,
                border: `1px solid ${
                  view === "axis" ? AXIS : view === "allies" ? ALLIES : "#31506b"
                }`,
                overflow: "hidden",
              }}
            >
              <KenBurns
                src={`frames/${frameName(board.turn, board.phase, view)}`}
                zoom={0.05}
                pan={8}
              />
            </div>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

const SidePanel: React.FC<{ visual: Beat["visual"]; overlays?: Beat["overlays"] }> = ({
  visual,
  overlays,
}) => {
  const board = visual.board!;
  const side = visual.side || "axis";
  const color = side === "axis" ? AXIS : ALLIES;
  return (
    <AbsoluteFill style={{ background: OCEAN, display: "flex", flexDirection: "row" }}>
      <div style={{ width: 900, height: "100%", overflow: "hidden" }}>
        <KenBurns src={`frames/${frameName(board.turn, board.phase, side)}`} pan={12} />
      </div>
      <div style={{ flex: 1, padding: "70px 50px", borderLeft: `6px solid ${color}` }}>
        <div style={{ color, fontFamily: FONT, fontSize: 40, marginBottom: 26 }}>
          {visual.title}
        </div>
        {(overlays || []).map((item, index) => (
          <div
            key={index}
            style={{
              color: TEXT,
              fontFamily: FONT,
              fontSize: 25,
              lineHeight: 1.55,
              marginBottom: 16,
              borderLeft: `3px solid ${color}`,
              paddingLeft: 14,
            }}
          >
            {item.text}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

const Chart: React.FC<{ visual: Beat["visual"] }> = ({ visual }) => {
  const bars = visual.bars || [];
  const max = Math.max(1, ...bars.map((bar) => bar.value));
  return (
    <AbsoluteFill style={{ background: OCEAN, padding: "100px 160px" }}>
      <div style={{ color: ACCENT, fontFamily: FONT, fontSize: 34, marginBottom: 50 }}>
        {visual.title}
      </div>
      {bars.map((bar, index) => (
        <div key={index} style={{ marginBottom: 26 }}>
          <div style={{ color: TEXT, fontFamily: FONT, fontSize: 26, marginBottom: 8 }}>
            {bar.label}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
            <div
              style={{
                height: 26,
                width: `${(bar.value / max) * 1100}px`,
                background: `linear-gradient(90deg, ${ALLIES}, ${ACCENT})`,
              }}
            />
            <div style={{ color: DIM, fontFamily: MONO, fontSize: 24 }}>{bar.value}</div>
          </div>
        </div>
      ))}
    </AbsoluteFill>
  );
};

const ResultCard: React.FC<{ visual: Beat["visual"] }> = ({ visual }) => (
  <AbsoluteFill
    style={{
      background: `radial-gradient(circle at 70% 30%, #16324a 0%, ${OCEAN} 65%)`,
      justifyContent: "center",
      alignItems: "center",
      textAlign: "center",
    }}
  >
    <div style={{ color: ACCENT, fontFamily: FONT, fontSize: 44, marginBottom: 40 }}>
      {visual.title}
    </div>
    {(visual.lines || []).map((line, index) => (
      <div
        key={index}
        style={{
          color: TEXT,
          fontFamily: FONT,
          fontSize: index === 0 ? 52 : 36,
          lineHeight: 1.6,
        }}
      >
        {line}
      </div>
    ))}
  </AbsoluteFill>
);

const BeatBody: React.FC<{ beat: Beat }> = ({ beat }) => {
  switch (beat.visual.kind) {
    case "title":
      return <TitleCard visual={beat.visual} />;
    case "card":
      return <Card visual={beat.visual} />;
    case "oob":
      return <Oob visual={beat.visual} />;
    case "board":
      return <BoardFrame visual={beat.visual} overlays={beat.overlays} />;
    case "compare":
      return <Compare visual={beat.visual} />;
    case "side":
      return <SidePanel visual={beat.visual} overlays={beat.overlays} />;
    case "chart":
      return <Chart visual={beat.visual} />;
    case "result":
      return <ResultCard visual={beat.visual} />;
    default:
      return <Card visual={beat.visual} />;
  }
};

export const Documentary: React.FC<DocumentaryProps> = ({ beats }) => {
  const { fps } = useVideoConfig();
  let from = 0;
  return (
    <AbsoluteFill style={{ background: OCEAN }}>
      {beats.map((beat) => {
        const frames = Math.max(1, Math.round((beat.seconds || 4) * fps));
        const start = from;
        from += frames;
        return (
          <Sequence key={beat.id} from={start} durationInFrames={frames}>
            <AbsoluteFill>
              <BeatBody beat={beat} />
              {beat.audio ? <Audio src={staticFile(beat.audio)} /> : null}
              <Caption text={beat.narration} chapter={beat.chapter} />
            </AbsoluteFill>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
