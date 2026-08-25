import http from "k6/http";
import { check, sleep } from "k6";
import { Trend, Rate } from "k6/metrics";

const askLatency = new Trend("ask_latency_ms", true);
const askErrors = new Rate("ask_errors");
const BASE = __ENV.BASE_URL || "http://localhost:8000";

const QUESTIONS = [
  "How are JWTs validated?",
  "What caused the auth outage on Nov 3?",
  "How do I roll back a production deploy?",
  "What algorithm signs the access tokens?",
];

export const options = {
  stages: [
    { duration: "30s", target: 3 },
    { duration: "1m",  target: 5 },
    { duration: "30s", target: 10 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<15000"],
    ask_errors: ["rate<0.05"],
  },
};

export default function () {
  const q = QUESTIONS[Math.floor(Math.random() * QUESTIONS.length)];
  const res = http.post(
    BASE + "/ask",
    JSON.stringify({ question: q }),
    { headers: { "Content-Type": "application/json" }, timeout: "120s" }
  );

  askLatency.add(res.timings.duration);
  const ok = check(res, {
    "status is 200": function (r) { return r.status === 200; },
    "has an answer": function (r) {
      try { return (r.json("answer") || "").length > 0; } catch (e) { return false; }
    },
  });
  askErrors.add(!ok);
  sleep(1);
}
