<template>
  <div class="card">
    <h2>Homework Grading Setup</h2>

    <!-- Answer upload -->
    <div class="form-group">
      <label>Standard Answers</label>
      <div
        class="upload-area"
        :class="{
          'has-files': fileUpload.sessionId.value,
          'drag-over': isDragOverAnswer,
          'is-uploading': fileUpload.uploading.value,
        }"
        @dragenter.prevent="isDragOverAnswer = true"
        @dragover.prevent="isDragOverAnswer = true"
        @dragleave.prevent="isDragOverAnswer = false"
        @drop.prevent="handleAnswerDrop"
      >
        <input
          ref="fileInput"
          type="file"
          multiple
          accept="image/*,.pdf"
          style="display: none"
          @change="handleFileChange"
        />
        <div v-if="fileUpload.uploading.value" class="upload-status">
          Uploading... {{ fileUpload.uploadProgress.value }}%
        </div>
        <div v-else-if="fileUpload.sessionId.value" class="upload-status">
          Uploaded {{ fileUpload.files.value.length }} file(s)
        </div>
        <div v-else class="upload-status">
          Drag answer files here, or
          <button class="btn-browse" @click.stop="$refs.fileInput.click()">Browse Files</button>
          <div class="upload-hint">Supports images and PDF</div>
        </div>
        <div v-if="fileUpload.uploading.value" class="upload-progress-track">
          <div class="upload-progress-bar" :style="{ width: fileUpload.uploadProgress.value + '%' }"></div>
        </div>
      </div>
      <div class="file-list" v-if="fileUpload.files.value.length > 0 && !fileUpload.uploading.value">
        <span v-for="f in fileUpload.files.value" :key="f.name">{{ f.name }}</span>
        <button v-if="fileUpload.sessionId.value" class="btn-browse btn-browse-sm" @click="$refs.fileInput.click()">Replace</button>
      </div>
      <div v-if="fileUpload.uploadError.value" class="error-msg">
        {{ fileUpload.uploadError.value }}
      </div>
    </div>

    <!-- Student submissions: toggle between path and upload -->
    <div class="form-group">
      <label>Student Submissions</label>
      <div class="toggle-row">
        <button
          class="toggle-btn"
          :class="{ active: submissionMode === 'path' }"
          @click="submissionMode = 'path'"
        >Folder Path</button>
        <button
          class="toggle-btn"
          :class="{ active: submissionMode === 'upload' }"
          @click="submissionMode = 'upload'"
        >Upload ZIP</button>
      </div>

      <!-- Path mode -->
      <input
        v-if="submissionMode === 'path'"
        type="text"
        v-model="studentFolder"
        placeholder="/path/to/student/submissions"
      />

      <!-- Upload mode -->
      <div
        v-else
        class="upload-area"
        :class="{
          'has-files': submissionZipUploaded,
          'drag-over': isDragOverSubmission,
          'is-uploading': uploadingSubmission,
        }"
        @dragenter.prevent="isDragOverSubmission = true"
        @dragover.prevent="isDragOverSubmission = true"
        @dragleave.prevent="isDragOverSubmission = false"
        @drop.prevent="handleSubmissionDrop"
      >
        <input
          ref="submissionInput"
          type="file"
          accept=".zip"
          style="display: none"
          @change="handleSubmissionSelect"
        />
        <div v-if="uploadingSubmission" class="upload-status">
          Uploading... {{ submissionProgress }}%
        </div>
        <div v-else-if="submissionZipUploaded" class="upload-status">
          {{ submissionZipName }} ({{ submissionFileCount }} files)
          <button class="btn-browse btn-browse-sm" @click.stop="$refs.submissionInput.click()">Replace</button>
        </div>
        <div v-else class="upload-status">
          Drag a ZIP file here, or
          <button class="btn-browse" @click.stop="$refs.submissionInput.click()">Browse Files</button>
          <div class="upload-hint">Supports .zip containing student submissions</div>
        </div>
        <div v-if="uploadingSubmission" class="upload-progress-track">
          <div class="upload-progress-bar" :style="{ width: submissionProgress + '%' }"></div>
        </div>
      </div>
      <div v-if="submissionError" class="error-msg">
        {{ submissionError }}
      </div>
    </div>

    <!-- Grading prompt -->
    <div class="form-group">
      <label>Grading Rules / Rubric</label>
      <textarea
        v-model="gradingPrompt"
        placeholder="e.g. Full marks: 100 points. Deduct 10 points for each incorrect answer. Provide feedback in Chinese."
      ></textarea>
    </div>

    <!-- Submit -->
    <button
      class="btn btn-primary"
      :disabled="!canSubmit || isRunning"
      @click="handleSubmit"
    >
      {{
        fileUpload.uploading.value || uploadingSubmission
          ? "Uploading..."
          : isRunning
          ? "Grading in Progress..."
          : "Start Grading"
      }}
    </button>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

const props = defineProps({
  fileUpload: { type: Object, required: true },
  isRunning: { type: Boolean, default: false },
});

const emit = defineEmits(["start"]);

const isDragOverAnswer = ref(false);
const isDragOverSubmission = ref(false);

const submissionMode = ref("path"); // "path" or "upload"
const studentFolder = ref("");

// Upload mode state
const submissionZipFile = ref(null);
const submissionZipName = ref("");
const submissionZipUploaded = ref(false);
const submissionFileCount = ref(0);
const uploadingSubmission = ref(false);
const submissionProgress = ref(0);
const submissionError = ref("");
const uploadedFolderPath = ref("");

const gradingPrompt = ref(
  "总分100分。错第一个题扣10分，每多错两个题多扣10分。如果所有题都不对或者题号都不对则为0分。"
);

const canSubmit = computed(() => {
  const answersReady = props.fileUpload.sessionId.value && !props.fileUpload.uploading.value;
  const submissionsReady =
    submissionMode.value === "path"
      ? studentFolder.value.trim() !== ""
      : submissionZipUploaded.value && !uploadingSubmission.value;
  return answersReady && submissionsReady;
});

function handleFileChange(e) {
  props.fileUpload.onFilesSelected(e);
  props.fileUpload.uploadAnswers();
}

function handleAnswerDrop(e) {
  isDragOverAnswer.value = false;
  const dropped = e.dataTransfer.files;
  if (dropped.length > 0) {
    props.fileUpload.onFilesDrop(dropped);
    props.fileUpload.uploadAnswers();
  }
}

function handleSubmissionSelect(e) {
  const file = e.target.files[0];
  if (file) {
    setSubmissionZip(file);
    uploadSubmissionZip();
  }
}

function handleSubmissionDrop(e) {
  isDragOverSubmission.value = false;
  const file = e.dataTransfer.files[0];
  if (file) {
    setSubmissionZip(file);
    uploadSubmissionZip();
  }
}

function setSubmissionZip(file) {
  submissionZipFile.value = file;
  submissionZipUploaded.value = false;
  uploadedFolderPath.value = "";
  submissionError.value = "";
  submissionProgress.value = 0;
}

async function uploadSubmissionZip() {
  if (!submissionZipFile.value) return false;
  if (submissionZipUploaded.value) return true;

  uploadingSubmission.value = true;
  submissionProgress.value = 0;
  submissionError.value = "";

  try {
    const formData = new FormData();
    formData.append("file", submissionZipFile.value);

    const data = await props.fileUpload.xhrUpload(
      "/api/upload-submissions",
      formData,
      (pct) => { submissionProgress.value = pct; }
    );

    uploadedFolderPath.value = data.folder_path;
    submissionFileCount.value = data.file_count;
    submissionZipName.value = submissionZipFile.value.name;
    submissionZipUploaded.value = true;
    return true;
  } catch (e) {
    submissionError.value = e.message;
    return false;
  } finally {
    uploadingSubmission.value = false;
  }
}

async function handleSubmit() {
  // Wait for answer upload if still in progress
  if (props.fileUpload.uploading.value) return;
  if (!props.fileUpload.sessionId.value) {
    // Retry upload if it failed earlier
    await props.fileUpload.uploadAnswers();
    if (!props.fileUpload.sessionId.value) return;
  }

  let folder = "";
  if (submissionMode.value === "path") {
    folder = studentFolder.value.trim();
  } else {
    if (uploadingSubmission.value) return;
    if (!submissionZipUploaded.value) {
      // Retry upload if it failed earlier
      const ok = await uploadSubmissionZip();
      if (!ok) return;
    }
    folder = uploadedFolderPath.value;
  }

  emit("start", {
    sessionId: props.fileUpload.sessionId.value,
    studentFolder: folder,
    gradingPrompt: gradingPrompt.value,
  });
}
</script>
