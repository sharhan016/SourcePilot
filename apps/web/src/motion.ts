import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import type { RefObject } from "react";

gsap.registerPlugin(useGSAP);

export function usePageMotion(scope: RefObject<HTMLElement | null>) {
  useGSAP(
    () => {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      gsap.from("[data-reveal]", {
        opacity: 0,
        y: 18,
        duration: 0.7,
        stagger: 0.08,
        ease: "power3.out",
      });
      gsap.from("[data-stack]", {
        opacity: 0,
        y: 12,
        duration: 0.45,
        stagger: 0.05,
        delay: 0.18,
        ease: "power2.out",
      });
    },
    { scope },
  );
}
