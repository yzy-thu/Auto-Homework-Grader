<template>
  <div class="card" v-if="logs.length > 0 || status === 'running'">
    <div class="progress-header">
      <h2>Grading Progress</h2>
      <button
        v-if="status === 'running'"
        class="btn btn-stop"
        @click="$emit('stop')"
      >
        Stop
      </button>
      <span v-else-if="status === 'stopping'" class="status-badge status-stopping">Stopping...</span>
      <span v-else-if="status === 'stopped'" class="status-badge status-stopped">Stopped</span>
      <span v-else-if="status === 'complete'" class="status-badge status-complete">Complete</span>
    </div>

    <!-- Progress bar -->
    <div class="progress-bar-container">
      <div class="progress-bar" :class="{ 'progress-bar-stopped': status === 'stopped' }" :style="{ width: progressPercent + '%' }"></div>
    </div>
    <div class="progress-text">
      {{ progress.current }} / {{ progress.total || "?" }} submissions
      ({{ progressPercent }}%)
    </div>

    <!-- Log output -->
    <div class="log-area" ref="logContainer">
      <div
        v-for="(log, i) in logs"
        :key="i"
        class="log-line"
        :class="{ 'log-error': log.type === 'error' }"
      >
        {{ log.message }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from "vue";

const props = defineProps({
  status: { type: String, default: "idle" },
  logs: { type: Array, default: () => [] },
  progress: { type: Object, default: () => ({ current: 0, total: 0 }) },
  progressPercent: { type: Number, default: 0 },
});

defineEmits(["stop"]);

const logContainer = ref(null);

watch(
  () => props.logs.length,
  async () => {
    await nextTick();
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight;
    }
  }
);
</script>
