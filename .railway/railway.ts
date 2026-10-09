import { defineRailway, project, service, volume } from "railway/iac";

// Own only the demo; other services in this project are outside this manifest.
export const partial = "calligraphy-demo";

export default defineRailway(() => {
  const data = volume("calligraphy-demo-volume", {
    region: "us-west2", sizeMB: 50000,
    alerts: { usage: { "100": {}, "80": {}, "95": {} } },
    allowOnlineResize: true,
  });
  const demo = service("calligraphy-demo", {
    build: { builder: "DOCKERFILE", dockerfilePath: "Dockerfile" },
    start: "sh deploy/start.sh",
    healthcheck: "/health", healthcheckTimeout: 120,
    replicas: { "us-west2": 1 },
    deploy: { restartPolicyMaxRetries: 5 },
    volumeMounts: { "/data": data },
    env: {
      PORT: "8080",
      DATABASE_URL: "sqlite:////data/calligraphy.db",
      CALLIGRAPHY_OUTPUT_DIR: "/data/outputs",
      CALLIGRAPHY_STYLE_DIR: "/data/styles",
      CALLIGRAPHY_KAI_CACHE: "/data/kai-geometry.db",
      CALLIGRAPHY_CONTACT_CACHE: "/data/contact-geometry.db",
      CALLIGRAPHY_ISOLATE_JOBS: "1",
      CALLIGRAPHY_SECURE_COOKIES: "1",
      CALLIGRAPHY_JOB_TIMEOUT_SECONDS: "600",
      CALLIGRAPHY_RETENTION_SECONDS: "86400",
      CALLIGRAPHY_MAX_ACTIVE_JOBS: "10",
      CALLIGRAPHY_PUBLIC_STYLES: "",
      CALLIGRAPHY_DEMO_ALL_FONTS: "1",
    },
  });
  return project("charming-magic", { resources: [demo, data] });
});
