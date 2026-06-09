import { clsx } from "clsx";
import { twMerge } from "tailwind-merge"

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

const SAFE_HTTP_PROTOCOLS = new Set(["http:", "https:"]);
const YOUTUBE_EMBED_HOSTS = new Set([
  "www.youtube.com",
  "youtube.com",
  "www.youtube-nocookie.com",
  "youtube-nocookie.com",
]);

export function isSafeHttpUrl(url) {
  if (!url || typeof url !== "string") return false;
  try {
    return SAFE_HTTP_PROTOCOLS.has(new URL(url).protocol);
  } catch {
    return false;
  }
}

export function isSafeYouTubeEmbedUrl(url) {
  if (!isSafeHttpUrl(url)) return false;
  try {
    return YOUTUBE_EMBED_HOSTS.has(new URL(url).hostname.toLowerCase());
  } catch {
    return false;
  }
}

export function isSafeImageSrc(url) {
  if (!url || typeof url !== "string") return false;
  if (url.startsWith("data:image/")) return true;
  return isSafeHttpUrl(url);
}
