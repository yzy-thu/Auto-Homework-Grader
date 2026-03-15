import { ref } from "vue";

function xhrUpload(url, formData, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      let data;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        reject(new Error("Server returned invalid response"));
        return;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data);
      } else {
        reject(new Error(data.error || `Upload failed (${xhr.status})`));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Network error")));
    xhr.addEventListener("abort", () => reject(new Error("Upload cancelled")));

    xhr.send(formData);
  });
}

export function useFileUpload() {
  const files = ref([]);
  const sessionId = ref(null);
  const uploading = ref(false);
  const uploadProgress = ref(0);
  const uploadError = ref("");

  function onFilesSelected(event) {
    const selected = Array.from(event.target.files || []);
    files.value = selected;
    uploadError.value = "";
    sessionId.value = null;
    uploadProgress.value = 0;
  }

  function onFilesDrop(fileList) {
    files.value = Array.from(fileList);
    uploadError.value = "";
    sessionId.value = null;
    uploadProgress.value = 0;
  }

  async function uploadAnswers() {
    if (files.value.length === 0) {
      uploadError.value = "Please select answer files";
      return;
    }

    uploading.value = true;
    uploadProgress.value = 0;
    uploadError.value = "";

    try {
      const formData = new FormData();
      for (const f of files.value) {
        formData.append("files", f);
      }

      const data = await xhrUpload("/api/upload-answers", formData, (pct) => {
        uploadProgress.value = pct;
      });

      sessionId.value = data.session_id;
    } catch (e) {
      uploadError.value = e.message;
    } finally {
      uploading.value = false;
    }
  }

  return {
    files,
    sessionId,
    uploading,
    uploadProgress,
    uploadError,
    onFilesSelected,
    onFilesDrop,
    uploadAnswers,
    xhrUpload,
  };
}
