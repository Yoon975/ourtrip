function showAccountMessage(text, type = "success") {
  const el = document.getElementById("accountMessage");
  if (!el) return;
  el.hidden = false;
  el.className = `account-message account-message--${type}`;
  el.textContent = text;
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok || !data.success) {
    throw new Error(data.message || "요청에 실패했습니다.");
  }
  return data;
}

document.getElementById("passwordForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await postJson("/api/account/password", {
      current_password: document.getElementById("current_password").value,
      new_password: document.getElementById("new_password").value,
      confirm_password: document.getElementById("confirm_password").value,
    });
    event.target.reset();
    showAccountMessage("비밀번호가 변경되었습니다.");
  } catch (error) {
    showAccountMessage(error.message, "error");
  }
});

document.getElementById("emailForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const data = await postJson("/api/account/email", {
      new_email: document.getElementById("new_email").value.trim(),
      password: document.getElementById("email_password").value,
    });
    document.getElementById("currentEmail").textContent = data.email;
    event.target.reset();
    showAccountMessage("이메일이 변경되었습니다.");
  } catch (error) {
    showAccountMessage(error.message, "error");
  }
});

document.getElementById("withdrawForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!confirm("정말 탈퇴하시겠습니까? 모든 데이터가 삭제됩니다.")) return;
  try {
    const data = await postJson("/api/account/withdraw", {
      password: document.getElementById("withdraw_password").value,
      confirm_text: document.getElementById("confirm_text").value.trim(),
    });
    alert(data.message);
    window.location.href = data.redirect || "/";
  } catch (error) {
    showAccountMessage(error.message, "error");
  }
});
