<template>
  <div class="card" v-if="results.length > 0">
    <div class="download-row">
      <h2>Grading Results</h2>
      <div style="display: flex; align-items: center; gap: 12px">
        <span class="summary">
          {{ gradedCount }} graded, {{ errorCount }} errors
        </span>
        <button
          v-if="status === 'complete' || status === 'stopped'"
          class="btn btn-success"
          @click="$emit('download')"
        >
          Download CSV
        </button>
      </div>
    </div>

    <div class="table-wrapper">
      <table class="results-table">
        <thead>
          <tr>
            <th v-for="col in columns" :key="col">{{ col }}</th>
            <th style="width: 70px">Score</th>
            <th>Feedback</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in results" :key="i">
            <td v-for="col in columns" :key="col">{{ r[col] || "" }}</td>
            <td class="score-cell" v-if="!r.error">{{ r.score }}</td>
            <td class="error-cell" v-else>--</td>
            <td v-if="!r.error">{{ r.feedback }}</td>
            <td class="error-cell" v-else>{{ r.error }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  results: { type: Array, default: () => [] },
  columns: { type: Array, default: () => [] },
  status: { type: String, default: "idle" },
});

defineEmits(["download"]);

const gradedCount = computed(
  () => props.results.filter((r) => !r.error && r.score !== "").length
);
const errorCount = computed(
  () => props.results.filter((r) => r.error).length
);
</script>
