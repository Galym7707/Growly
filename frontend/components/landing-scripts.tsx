"use client";

import { useEffect } from "react";

export function LandingScripts() {
  useEffect(() => {
    let disposed = false;
    const scripts: HTMLScriptElement[] = [];

    const loadScript = (src: string) =>
      new Promise<void>((resolve, reject) => {
        const script = document.createElement("script");
        script.src = src;
        script.async = false;
        script.dataset.growlyLandingScript = "true";
        script.addEventListener("load", () => resolve(), { once: true });
        script.addEventListener(
          "error",
          () => reject(new Error(`Failed to load landing script: ${src}`)),
          { once: true },
        );
        scripts.push(script);
        document.body.appendChild(script);
      });

    void loadScript("/landing/i18n.js")
      .then(() => {
        if (!disposed) return loadScript("/landing/main.js");
      })
      .catch((error: unknown) => {
        if (!disposed) console.error(error);
      });

    return () => {
      disposed = true;
      scripts.forEach((script) => script.remove());
    };
  }, []);

  return null;
}
