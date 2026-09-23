import { Composition } from "remotion";
import { Documentary, type DocumentaryProps } from "./Documentary";
import { beats as fallbackBeats } from "./fallbackTimeline";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Documentary"
        component={Documentary}
        durationInFrames={30 * 60 * 12}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          beats: fallbackBeats,
          title: "第二次马里亚纳海战 · 内南洋水雷强袭战",
        } as DocumentaryProps}
        calculateMetadata={({ props }) => {
          // The composition's length is the sum of its beats: each beat is as long as
          // its narration plus a breath, so picture and voice cannot drift apart.
          const fps = 30;
          const total = (props.beats || []).reduce(
            (sum, beat) => sum + Math.max(1, Math.round((beat.seconds || 4) * fps)),
            0,
          );
          return {
            durationInFrames: Math.max(fps * 5, total),
            fps,
            width: 1920,
            height: 1080,
          };
        }}
      />
    </>
  );
};
