import { ref, computed } from "vue";

export function useGrading() {
  const jobId = ref(null);
  const status = ref("idle"); // idle | running | stopping | complete | stopped | error
  const logs = ref([]);
  const results = ref([]);
  const columns = ref([]);   // dynamic metadata columns from backend
  const progress = ref({ current: 0, total: 0 });
  const errorMessage = ref("");

  const progressPercent = computed(() => {
    if (progress.value.total === 0) return 0;
    return Math.round((progress.value.current / progress.value.total) * 100);
  });

  async function startGrading(sessionId, studentFolder, gradingPrompt) {
    status.value = "running";
    logs.value = [];
    results.value = [];
    columns.value = [];
    progress.value = { current: 0, total: 0 };
    errorMessage.value = "";

    try {
      const resp = await fetch("/api/grade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          student_folder: studentFolder,
          grading_prompt: gradingPrompt,
        }),
      });

      const text = await resp.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch {
        throw new Error("Server returned invalid response");
      }

      if (!resp.ok) {
        throw new Error(data.error || "Failed to start grading");
      }

      jobId.value = data.job_id;
      connectSSE(data.job_id);
    } catch (e) {
      status.value = "error";
      errorMessage.value = e.message;
    }
  }

  function connectSSE(id) {
    const source = new EventSource(`/api/grade/stream?job_id=${id}`);
    let done = false;

    source.addEventListener("columns", (e) => {
      const data = JSON.parse(e.data);
      columns.value = data.columns || [];
    });

    source.addEventListener("progress", (e) => {
      const data = JSON.parse(e.data);
      logs.value.push({ type: "info", message: data.message });
      if (data.total) {
        progress.value.total = data.total;
      }
      if (typeof data.current === "number") {
        progress.value.current = data.current;
      }
    });

    source.addEventListener("result", (e) => {
      const data = JSON.parse(e.data);
      results.value.push(data);
      progress.value.current = results.value.length;
      // Build display label from the first two metadata columns
      const cols = columns.value;
      const label = cols.length >= 2
        ? `[${data[cols[0]] || ""}] ${data[cols[1]] || ""}`
        : cols.length === 1
        ? `[${data[cols[0]] || ""}]`
        : `[${data.filename || "?"}]`;
      const scoreText = data.error
        ? `ERROR: ${data.error}`
        : `${data.score} points`;
      logs.value.push({
        type: data.error ? "error" : "info",
        message: `${label}: ${scoreText}`,
      });
    });

    // Backend-sent "error" event (named event, has e.data)
    source.addEventListener("error", (e) => {
      if (e.data) {
        const data = JSON.parse(e.data);
        logs.value.push({ type: "error", message: data.message });
      }
    });

    source.addEventListener("complete", (e) => {
      done = true;
      const data = JSON.parse(e.data);
      status.value = "complete";
      logs.value.push({
        type: "info",
        message: `Done! Graded ${data.graded}/${data.total} submissions.`,
      });
      source.close();
    });

    source.addEventListener("stopped", (e) => {
      done = true;
      const data = JSON.parse(e.data);
      status.value = "stopped";
      logs.value.push({
        type: "info",
        message: `Stopped. Graded ${data.graded}/${data.total} submissions. Partial CSV ready for download.`,
      });
      source.close();
    });

    source.onerror = () => {
      if (done || status.value !== "running") {
        source.close();
      }
    };
  }

  async function stopGrading() {
    if (!jobId.value || status.value !== "running") return;
    status.value = "stopping";
    logs.value.push({ type: "info", message: "Stopping... waiting for in-progress tasks to finish." });
    try {
      await fetch("/api/grade/stop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId.value }),
      });
    } catch {
      // ignore — SSE will handle the stopped event
    }
  }

  function downloadCSV() {
    if (jobId.value) {
      window.open(`/api/download?job_id=${jobId.value}`, "_blank");
    }
  }

  return {
    jobId,
    status,
    logs,
    results,
    columns,
    progress,
    progressPercent,
    errorMessage,
    startGrading,
    stopGrading,
    downloadCSV,
  };
}
