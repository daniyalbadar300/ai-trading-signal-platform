/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend base URL, e.g. https://ai-trading-api.onrender.com.
   *  Empty/undefined = same origin (dev proxy / nginx / k8s ingress). */
  readonly VITE_API_BASE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
