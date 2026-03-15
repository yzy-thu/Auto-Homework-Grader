<template>
  <div class="app-container">
    <header class="app-header">
      <h1>Auto Homework Grader</h1>
      <p>Upload standard answers and student submissions, let AI grade them automatically</p>
    </header>

    <GradingForm
      :file-upload="fileUpload"
      :is-running="grading.status.value === 'running'"
      @start="handleStart"
    />

    <ProgressTracker
      :status="grading.status.value"
      :logs="grading.logs.value"
      :progress="grading.progress.value"
      :progress-percent="grading.progressPercent.value"
      @stop="grading.stopGrading"
    />

    <ResultsTable
      :results="grading.results.value"
      :columns="grading.columns.value"
      :status="grading.status.value"
      @download="grading.downloadCSV"
    />
  </div>
</template>

<script setup>
import GradingForm from "./components/GradingForm.vue";
import ProgressTracker from "./components/ProgressTracker.vue";
import ResultsTable from "./components/ResultsTable.vue";
import { useFileUpload } from "./composables/useFileUpload.js";
import { useGrading } from "./composables/useGrading.js";

const fileUpload = useFileUpload();
const grading = useGrading();

function handleStart({ sessionId, studentFolder, gradingPrompt }) {
  grading.startGrading(sessionId, studentFolder, gradingPrompt);
}
</script>
