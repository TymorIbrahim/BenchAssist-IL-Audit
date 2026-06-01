import { useEffect, type RefObject } from "react";

const DEFAULT_TOP_BAR_PX = 88;

/** Keep sticky sub-headers aligned below the tab bar (and optional filter bar). */
export function useDetentionStickyOffsets(
  topBarRef: RefObject<HTMLElement | null>,
  filterAnchorRef: RefObject<HTMLElement | null>,
  filterVisible: boolean,
) {
  useEffect(() => {
    const root = document.querySelector(".detention-dashboard") as HTMLElement | null;
    if (!root) return;

    const sync = () => {
      const topHeight = topBarRef.current?.getBoundingClientRect().height ?? DEFAULT_TOP_BAR_PX;
      root.style.setProperty("--detention-top-bar-height", `${Math.ceil(topHeight)}px`);

      const filterHeight =
        filterVisible && filterAnchorRef.current
          ? Math.ceil(filterAnchorRef.current.getBoundingClientRect().height)
          : 0;
      root.style.setProperty("--detention-filter-height", `${filterHeight}px`);
    };

    sync();
    const observer = new ResizeObserver(sync);
    if (topBarRef.current) observer.observe(topBarRef.current);
    if (filterVisible && filterAnchorRef.current) observer.observe(filterAnchorRef.current);
    window.addEventListener("resize", sync);
    if (filterVisible) requestAnimationFrame(sync);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", sync);
    };
  }, [topBarRef, filterAnchorRef, filterVisible]);
}
