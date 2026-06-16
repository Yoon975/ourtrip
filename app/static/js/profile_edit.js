const form = document.getElementById("profileEditForm");
const messageEl = document.getElementById("message");
const submitBtn = document.getElementById("submitBtn");
const photoInput = document.getElementById("profilePhoto");
const photoPreview = document.getElementById("photoPreview");
const photoPin = document.getElementById("photoPin");

const receiptFields = [
  { inputId: "nick", statusId: "status-nick" },
  { inputId: "birth_year", statusId: "status-birth", optional: true },
];

function updateGenderStatus() {
  const status = document.getElementById("status-gender");
  if (!status) return;
  const selected = document.querySelector('input[name="gender"]:checked');
  if (selected) {
    status.textContent = "Complete";
    status.classList.add("complete");
  } else {
    status.textContent = "required";
    status.classList.remove("complete");
  }
}

function updateReceiptStatus() {
  receiptFields.forEach(({ inputId, statusId, optional }) => {
    const input = document.getElementById(inputId);
    const status = document.getElementById(statusId);
    const filled = input.value.trim().length > 0;

    if (filled) {
      status.textContent = "Complete";
      status.classList.add("complete");
    } else {
      status.textContent = optional ? "optional" : "required";
      status.classList.remove("complete");
    }
  });
  updateGenderStatus();
}

receiptFields.forEach(({ inputId }) => {
  document.getElementById(inputId).addEventListener("input", updateReceiptStatus);
});

document.querySelectorAll('input[name="gender"]').forEach((radio) => {
  radio.addEventListener("change", updateGenderStatus);
});

if (photoInput && photoPin && photoPreview) {
  photoInput.addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      alert("이미지 파일만 첨부할 수 있습니다.");
      photoInput.value = "";
      return;
    }

    const reader = new FileReader();
    reader.onload = (loadEvent) => {
      photoPreview.src = loadEvent.target.result;
      photoPin.classList.add("has-photo");
    };
    reader.readAsDataURL(file);
  });
}

if (form) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    messageEl.className = "message";
    messageEl.textContent = "";
    submitBtn.disabled = true;

    const formData = new FormData();
    formData.append("nick", document.getElementById("nick").value.trim());
    formData.append("birth_year", document.getElementById("birth_year").value.trim());
    formData.append("profile_role", document.getElementById("profile_role").value.trim());
    formData.append("bio", document.getElementById("bio").value.trim());

    const genderInput = document.querySelector('input[name="gender"]:checked');
    if (genderInput) {
      formData.append("gender", genderInput.value);
    }

    if (photoInput && photoInput.files[0]) {
      formData.append("profilePhoto", photoInput.files[0]);
    }

    try {
      const response = await fetch(window.PROFILE_UPDATE_API_URL, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();

      if (data.success) {
        messageEl.className = "message success";
        messageEl.textContent = data.message || "프로필이 수정되었습니다.";
        if (data.redirect) {
          setTimeout(() => {
            window.location.href = data.redirect;
          }, 900);
        }
      } else {
        messageEl.className = "message error";
        messageEl.textContent = data.message || "프로필 수정에 실패했습니다.";
      }
    } catch {
      messageEl.className = "message error";
      messageEl.textContent = "서버에 연결할 수 없습니다.";
    } finally {
      submitBtn.disabled = false;
    }
  });
}

updateReceiptStatus();
