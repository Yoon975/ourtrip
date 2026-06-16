const form = document.getElementById("signupForm");
const messageEl = document.getElementById("message");
const submitBtn = document.getElementById("submitBtn");
const photoInput = document.getElementById("profilePhoto");
const photoPreview = document.getElementById("photoPreview");
const photoPin = document.getElementById("photoPin");

const receiptFields = [
  { inputId: "u_id", statusId: "status-email" },
  { inputId: "pw", statusId: "status-pw" },
  { inputId: "nick", statusId: "status-nick" },
  { inputId: "birth_year", statusId: "status-birth", optional: true },
];

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
}

receiptFields.forEach(({ inputId }) => {
  document.getElementById(inputId).addEventListener("input", updateReceiptStatus);
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

    const payload = {
      u_id: document.getElementById("u_id").value.trim(),
      pw: document.getElementById("pw").value,
      nick: document.getElementById("nick").value.trim(),
      birth_year: document.getElementById("birth_year").value.trim(),
    };

    try {
      const response = await fetch(window.REGISTER_API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();

      if (data.success) {
        messageEl.className = "message success";
        messageEl.textContent = data.message || "회원가입이 완료되었습니다!";
        form.reset();
        if (photoInput) photoInput.value = "";
        if (photoPreview) photoPreview.src = "";
        if (photoPin) photoPin.classList.remove("has-photo");
        updateReceiptStatus();

        if (data.redirect) {
          setTimeout(() => {
            window.location.href = data.redirect;
          }, 1200);
        }
      } else {
        messageEl.className = "message error";
        messageEl.textContent = data.message || "회원가입에 실패했습니다.";
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
