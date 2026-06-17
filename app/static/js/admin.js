const messageEl = document.getElementById("admin-message");
const tabButtons = document.querySelectorAll(".admin-tabs__btn");
const panels = document.querySelectorAll(".admin-panel");

const state = {
  users: { page: 1, role: "", q: "" },
  posts: { page: 1, country: "", q: "" },
  comments: { page: 1, q: "" },
  scraps: { page: 1, q: "" },
  contacts: { page: 1, q: "" },
};

function showMessage(text, type = "success") {
  if (!messageEl) return;
  messageEl.hidden = false;
  messageEl.className = `admin-message ${type}`;
  messageEl.textContent = text;
  clearTimeout(showMessage.timer);
  showMessage.timer = setTimeout(() => {
    messageEl.hidden = true;
  }, 3200);
}

tabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const tab = button.dataset.tab;
    tabButtons.forEach((item) => item.classList.toggle("is-active", item === button));
    panels.forEach((panel) => panel.classList.toggle("is-active", panel.dataset.panel === tab));
    if (tab === "users") loadUsers();
    if (tab === "posts") loadPosts();
    if (tab === "comments") loadComments();
    if (tab === "scraps") loadScraps();
    if (tab === "contacts") loadContacts();
  });
});

function renderPagination(containerId, page, totalPages, onPage) {
  const container = document.getElementById(containerId);
  if (!container) return;
  if (totalPages <= 1) {
    container.innerHTML = "";
    return;
  }
  container.innerHTML = `
    <button type="button" class="admin-page-btn" ${page <= 1 ? "disabled" : ""} data-page="${page - 1}">←</button>
    <span>${page} / ${totalPages}</span>
    <button type="button" class="admin-page-btn" ${page >= totalPages ? "disabled" : ""} data-page="${page + 1}">→</button>
  `;
  container.querySelectorAll("[data-page]").forEach((btn) => {
    btn.addEventListener("click", () => onPage(Number(btn.dataset.page)));
  });
}

async function loadOverview() {
  const response = await fetch("/admin/api/overview");
  const data = await response.json();
  if (!data.success) return;

  const { totals, users_by_role, posts_by_country, model_metrics: metrics } = data.overview;
  const stats = document.getElementById("overview-stats");
  if (stats) {
    const labels = ["회원", "게시물", "댓글", "스크랩"];
    const values = [totals.users, totals.posts, totals.comments, totals.scraps];
    stats.innerHTML = labels
      .map(
        (label, idx) => `
      <div class="admin-stat">
        <span class="admin-stat__label">${label}</span>
        <strong>${values[idx].toLocaleString()}</strong>
      </div>`
      )
      .join("");
  }

  document.getElementById("role-breakdown").innerHTML = users_by_role
    .map((row) => `<li><span>${row.role === "admin" ? "관리자" : "일반"}</span><strong>${row.cnt}</strong></li>`)
    .join("");

  document.getElementById("country-breakdown").innerHTML = posts_by_country
    .map((row) => `<li><span>${row.country}</span><strong>${row.cnt}</strong></li>`)
    .join("");

  const metricsEl = document.getElementById("model-metrics");
  const trainBtn = document.getElementById("train-model-btn");
  if (metrics) {
    const trainedAt = metrics.trained_at
      ? new Date(metrics.trained_at).toLocaleString("ko-KR")
      : "—";
    const hybridLabel = metrics.stage3_enabled
      ? "3단계 (TF-IDF · 의미 임베딩 · 협업 · 조회 + LTR)"
      : metrics.hybrid_enabled
        ? "2단계 (TF-IDF + 협업 필터)"
        : "—";
    const countryHit = metrics.stage3_country_hit_at_3 ?? metrics.hybrid_country_hit_at_3;
    const postHit = metrics.stage3_post_hit_at_3 ?? metrics.hybrid_post_hit_at_3;
    const weights = metrics.ranking_weights;
    const weightText = weights
      ? `RF ${(weights.rf * 100).toFixed(0)}% · 콘텐츠 ${(weights.content * 100).toFixed(0)}% · 의미 ${(weights.semantic * 100).toFixed(0)}% · 협업 ${(weights.collab * 100).toFixed(0)}% · 조회 ${(weights.view * 100).toFixed(0)}%`
      : null;
    metricsEl.innerHTML = `
      <p>상태 <strong>${metrics.exists ? "저장됨" : "미생성"}</strong>${metrics.model_version ? ` <span class="admin-metrics__note">v${metrics.model_version}</span>` : ""}</p>
      <p>마지막 학습 <strong>${metrics.exists ? trainedAt : "—"}</strong></p>
      <p>학습 샘플 <strong>${metrics.sample_count != null ? metrics.sample_count.toLocaleString() + "건" : "—"}</strong></p>
      <p>Top-1 정확도 <strong>${metrics.top1_accuracy != null ? (metrics.top1_accuracy * 100).toFixed(1) + "%" : "—"}</strong></p>
      <p>Top-3 정확도 <strong>${metrics.top3_accuracy != null ? (metrics.top3_accuracy * 100).toFixed(1) + "%" : "—"}</strong></p>
      <p>피처 수 <strong>${metrics.feature_count != null ? metrics.feature_count + "개 (나이·성별·스크랩·작성·여행)" : "—"}</strong></p>
      <p>랭킹 엔진 <strong>${hybridLabel}</strong></p>
      ${weightText ? `<p>LTR 가중치 <strong>${weightText}</strong></p>` : ""}
      <p>추천 국가 Hit@3 <strong>${countryHit != null ? (countryHit * 100).toFixed(1) + "%" : "—"}</strong>${metrics.rf_rank_country_hit_at_3 != null ? ` <span class="admin-metrics__note">(RF만 ${(metrics.rf_rank_country_hit_at_3 * 100).toFixed(1)}%)</span>` : ""}</p>
      <p>추천 게시물 Hit@3 <strong>${postHit != null ? (postHit * 100).toFixed(1) + "%" : "—"}</strong></p>
      ${metrics.note ? `<p class="admin-metrics__note">${metrics.note}</p>` : ""}
      ${!metrics.exists ? `<p class="admin-metrics__note">모델 생성 버튼을 눌러 학습·저장하세요. 추천은 저장된 모델을 사용합니다.</p>` : ""}
    `;
  }
  if (trainBtn) {
    trainBtn.textContent = metrics?.exists ? "모델 재학습" : "모델 생성";
  }
}

async function trainModel() {
  const trainBtn = document.getElementById("train-model-btn");
  if (!trainBtn) return;
  trainBtn.disabled = true;
  trainBtn.textContent = "학습 중…";

  try {
    const response = await fetch("/admin/api/model/train", { method: "POST" });
    const data = await response.json();
    showMessage(data.message, data.success ? "success" : "error");
    if (data.success) {
      loadOverview();
    }
  } catch {
    showMessage("서버에 연결할 수 없습니다.", "error");
  } finally {
    trainBtn.disabled = false;
  }
}

async function loadUsers(page = state.users.page) {
  state.users.page = page;
  const params = new URLSearchParams({ page, role: state.users.role, q: state.users.q });
  const response = await fetch(`/admin/api/users?${params}`);
  const data = await response.json();
  if (!data.success) return;

  const tbody = document.getElementById("users-table-body");
  tbody.innerHTML = data.items
    .map(
      (user) => `
    <tr data-user-row="${user.user_id}">
      <td>${user.user_id}</td>
      <td class="admin-table__email"><input type="email" class="admin-input" data-field="email" value="${escapeHtml(user.email)}" /></td>
      <td><input type="text" class="admin-input" data-field="nickname" value="${escapeHtml(user.nickname)}" /></td>
      <td>
        <select class="admin-select" data-field="gender">
          <option value="M" ${user.gender === "M" ? "selected" : ""}>남</option>
          <option value="F" ${user.gender === "F" ? "selected" : ""}>여</option>
          <option value="U" ${user.gender === "U" ? "selected" : ""}>미선택</option>
        </select>
      </td>
      <td><input type="number" class="admin-input admin-input--short" data-field="birth_year" value="${user.birth_year || ""}" /></td>
      <td>
        <select class="admin-select" data-field="role">
          <option value="user" ${user.role === "user" ? "selected" : ""}>일반</option>
          <option value="admin" ${user.role === "admin" ? "selected" : ""}>관리자</option>
        </select>
      </td>
      <td>${(user.created_at || "").slice(0, 10)}</td>
      <td class="admin-table__actions">
        <button type="button" class="admin-btn admin-btn--primary" data-save-user="${user.user_id}">저장</button>
        <button type="button" class="admin-btn admin-btn--danger" data-delete-user="${user.user_id}">삭제</button>
      </td>
    </tr>`
    )
    .join("");

  bindUserSaveButtons();
  bindUserDeleteButtons();
  renderPagination("users-pagination", data.page, data.total_pages, loadUsers);
}

async function loadScraps(page = state.scraps.page) {
  state.scraps.page = page;
  const params = new URLSearchParams({ page, q: state.scraps.q });
  const response = await fetch(`/admin/api/scraps?${params}`);
  const data = await response.json();
  if (!data.success) return;
  document.getElementById("scraps-table-body").innerHTML = data.items
    .map(
      (scrap) => `
    <tr>
      <td>${scrap.scrap_id}</td>
      <td>${escapeHtml(scrap.nickname)}</td>
      <td><a href="/posts/${scrap.post_id}" class="admin-link">${escapeHtml(scrap.title)}</a></td>
      <td>${escapeHtml(scrap.location_country || "")}</td>
      <td>${(scrap.created_at || "").slice(0, 10)}</td>
      <td><button type="button" class="admin-btn admin-btn--danger" data-delete-scrap="${scrap.scrap_id}">삭제</button></td>
    </tr>`
    )
    .join("");
  document.querySelectorAll("[data-delete-scrap]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!confirm("스크랩을 삭제할까요?")) return;
      const response = await fetch(`/admin/api/scraps/${button.dataset.deleteScrap}`, { method: "DELETE" });
      const result = await response.json();
      showMessage(result.message, result.success ? "success" : "error");
      if (result.success) loadScraps(state.scraps.page);
    });
  });
  renderPagination("scraps-pagination", data.page, data.total_pages, loadScraps);
}

async function loadContacts(page = state.contacts.page) {
  state.contacts.page = page;
  const params = new URLSearchParams({ page, q: state.contacts.q });
  const response = await fetch(`/admin/api/contacts?${params}`);
  const data = await response.json();
  if (!data.success) return;
  document.getElementById("contacts-table-body").innerHTML = data.items
    .map(
      (contact) => `
    <tr>
      <td>${contact.contact_id}</td>
      <td>${escapeHtml(contact.name)}</td>
      <td>${escapeHtml(contact.email)}</td>
      <td class="admin-table__content">${escapeHtml(contact.message)}</td>
      <td>${(contact.created_at || "").slice(0, 10)}</td>
      <td><button type="button" class="admin-btn admin-btn--danger" data-delete-contact="${contact.contact_id}">삭제</button></td>
    </tr>`
    )
    .join("");
  document.querySelectorAll("[data-delete-contact]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!confirm("문의를 삭제할까요?")) return;
      const response = await fetch(`/admin/api/contacts/${button.dataset.deleteContact}`, { method: "DELETE" });
      const result = await response.json();
      showMessage(result.message, result.success ? "success" : "error");
      if (result.success) loadContacts(state.contacts.page);
    });
  });
  renderPagination("contacts-pagination", data.page, data.total_pages, loadContacts);
}

async function loadPosts(page = state.posts.page) {
  state.posts.page = page;
  const params = new URLSearchParams({ page, country: state.posts.country, q: state.posts.q });
  const response = await fetch(`/admin/api/posts?${params}`);
  const data = await response.json();
  if (!data.success) return;

  const countryFilter = document.getElementById("post-country-filter");
  if (countryFilter && countryFilter.options.length <= 1 && data.countries) {
    data.countries.forEach((country) => {
      const option = document.createElement("option");
      option.value = country;
      option.textContent = country;
      countryFilter.appendChild(option);
    });
  }

  document.getElementById("posts-table-body").innerHTML = data.items
    .map(
      (post) => `
    <tr data-post-row="${post.post_id}">
      <td>${post.post_id}</td>
      <td><a href="/posts/${post.post_id}" class="admin-link">${escapeHtml(post.title)}</a></td>
      <td><span class="admin-tag">${escapeHtml(post.location_country)}</span>${post.location_city ? ` · ${escapeHtml(post.location_city)}` : ""}</td>
      <td>${escapeHtml(post.nickname)}</td>
      <td>${post.view_count}</td>
      <td>${(post.created_at || "").slice(0, 10)}</td>
      <td><button type="button" class="admin-btn admin-btn--danger" data-delete-post="${post.post_id}">삭제</button></td>
    </tr>`
    )
    .join("");

  bindPostDeleteButtons();
  renderPagination("posts-pagination", data.page, data.total_pages, loadPosts);
}

async function loadComments(page = state.comments.page) {
  state.comments.page = page;
  const params = new URLSearchParams({ page, q: state.comments.q });
  const response = await fetch(`/admin/api/comments?${params}`);
  const data = await response.json();
  if (!data.success) return;

  document.getElementById("comments-table-body").innerHTML = data.items
    .map(
      (comment) => `
    <tr data-comment-row="${comment.comment_id}">
      <td>${comment.comment_id}</td>
      <td class="admin-table__content" title="${escapeHtml(comment.content)}">${escapeHtml(comment.content)}</td>
      <td>${escapeHtml(comment.nickname)}</td>
      <td><a href="/posts/${comment.post_id}" class="admin-link">${escapeHtml(comment.post_title)}</a></td>
      <td>${(comment.created_at || "").slice(0, 10)}</td>
      <td><button type="button" class="admin-btn admin-btn--danger" data-delete-comment="${comment.comment_id}">삭제</button></td>
    </tr>`
    )
    .join("");

  bindCommentDeleteButtons();
  renderPagination("comments-pagination", data.page, data.total_pages, loadComments);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function getRowField(row, field) {
  const input = row.querySelector(`[data-field="${field}"]`);
  return input ? input.value.trim() : "";
}

function bindUserSaveButtons() {
  document.querySelectorAll("[data-save-user]").forEach((button) => {
    button.addEventListener("click", async () => {
      const userId = button.dataset.saveUser;
      const row = document.querySelector(`[data-user-row="${userId}"]`);
      if (!row) return;
      button.disabled = true;
      const formData = new FormData();
      formData.append("nickname", getRowField(row, "nickname"));
      formData.append("email", getRowField(row, "email"));
      formData.append("gender", getRowField(row, "gender"));
      formData.append("birth_year", getRowField(row, "birth_year"));
      formData.append("role", getRowField(row, "role"));
      try {
        const response = await fetch(`/admin/api/users/${userId}`, { method: "POST", body: formData });
        const data = await response.json();
        showMessage(data.message, data.success ? "success" : "error");
      } catch {
        showMessage("서버에 연결할 수 없습니다.", "error");
      } finally {
        button.disabled = false;
      }
    });
  });
}

function bindUserDeleteButtons() {
  document.querySelectorAll("[data-delete-user]").forEach((button) => {
    button.addEventListener("click", async () => {
      const userId = button.dataset.deleteUser;
      if (!confirm("회원을 삭제할까요?")) return;
      const response = await fetch(`/admin/api/users/${userId}`, { method: "DELETE" });
      const data = await response.json();
      showMessage(data.message, data.success ? "success" : "error");
      if (data.success) loadUsers(state.users.page);
    });
  });
}

function bindPostDeleteButtons() {
  document.querySelectorAll("[data-delete-post]").forEach((button) => {
    button.addEventListener("click", async () => {
      const postId = button.dataset.deletePost;
      if (!confirm("이 게시글을 삭제할까요?")) return;
      button.disabled = true;
      try {
        const response = await fetch(`/admin/api/posts/${postId}`, { method: "DELETE" });
        const data = await response.json();
        if (data.success) {
          showMessage(data.message, "success");
          loadPosts(state.posts.page);
          loadOverview();
        } else {
          showMessage(data.message, "error");
          button.disabled = false;
        }
      } catch {
        showMessage("서버에 연결할 수 없습니다.", "error");
        button.disabled = false;
      }
    });
  });
}

function bindCommentDeleteButtons() {
  document.querySelectorAll("[data-delete-comment]").forEach((button) => {
    button.addEventListener("click", async () => {
      const commentId = button.dataset.deleteComment;
      if (!confirm("이 댓글을 삭제할까요?")) return;
      button.disabled = true;
      try {
        const response = await fetch(`/admin/api/comments/${commentId}`, { method: "DELETE" });
        const data = await response.json();
        if (data.success) {
          showMessage(data.message, "success");
          loadComments(state.comments.page);
          loadOverview();
        } else {
          showMessage(data.message, "error");
          button.disabled = false;
        }
      } catch {
        showMessage("서버에 연결할 수 없습니다.", "error");
        button.disabled = false;
      }
    });
  });
}

document.getElementById("user-search-btn")?.addEventListener("click", () => {
  state.users.q = document.getElementById("user-search").value.trim();
  loadUsers(1);
});
document.getElementById("user-search")?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    state.users.q = e.target.value.trim();
    loadUsers(1);
  }
});
document.getElementById("post-search-btn")?.addEventListener("click", () => {
  state.posts.q = document.getElementById("post-search").value.trim();
  loadPosts(1);
});
document.getElementById("post-search")?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    state.posts.q = e.target.value.trim();
    loadPosts(1);
  }
});
document.getElementById("comment-search-btn")?.addEventListener("click", () => {
  state.comments.q = document.getElementById("comment-search").value.trim();
  loadComments(1);
});
document.getElementById("comment-search")?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    state.comments.q = e.target.value.trim();
    loadComments(1);
  }
});
document.getElementById("scrap-search-btn")?.addEventListener("click", () => {
  state.scraps.q = document.getElementById("scrap-search").value.trim();
  loadScraps(1);
});
document.getElementById("contact-search-btn")?.addEventListener("click", () => {
  state.contacts.q = document.getElementById("contact-search").value.trim();
  loadContacts(1);
});
document.getElementById("user-role-filter")?.addEventListener("change", (e) => {
  state.users.role = e.target.value;
  loadUsers(1);
});
document.getElementById("post-country-filter")?.addEventListener("change", (e) => {
  state.posts.country = e.target.value;
  loadPosts(1);
});

document.getElementById("train-model-btn")?.addEventListener("click", trainModel);

loadOverview();
