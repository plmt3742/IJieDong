/// <reference types="miniprogram-api-typings" />

interface IAppOption {
  globalData: {
    apiBaseUrl: string;
    appName: string;
    version: string;
    demoMode: boolean;
    systemInfo: WechatMiniprogram.SystemInfo | null;
  };
  onLaunch?: () => void;
  onError?: (message: string) => void;
}

/**
 * Minimal structural types for the Canvas 2D node returned by
 * `createSelectorQuery().fields({ node: true, size: true })`.
 * The mini program typings do not ship a precise DOM context type, so the
 * renderer declares only the members it actually uses. No `any` is involved.
 */
interface ICanvas2DContext {
  fillStyle: string;
  strokeStyle: string;
  lineWidth: number;
  font: string;
  textAlign: 'left' | 'center' | 'right';
  textBaseline: 'top' | 'middle' | 'bottom' | 'alphabetic';
  globalAlpha: number;
  scale(x: number, y: number): void;
  clearRect(x: number, y: number, width: number, height: number): void;
  fillRect(x: number, y: number, width: number, height: number): void;
  strokeRect(x: number, y: number, width: number, height: number): void;
  measureText(text: string): { width: number };
  fillText(text: string, x: number, y: number): void;
  beginPath(): void;
  closePath(): void;
  moveTo(x: number, y: number): void;
  lineTo(x: number, y: number): void;
  arc(
    x: number,
    y: number,
    radius: number,
    startAngle: number,
    endAngle: number,
    counterclockwise?: boolean
  ): void;
  stroke(): void;
  fill(): void;
  save(): void;
  restore(): void;
  setTransform(a: number, b: number, c: number, d: number, e: number, f: number): void;
}

interface ICanvasNode {
  width: number;
  height: number;
  getContext(type: '2d'): ICanvas2DContext;
}
