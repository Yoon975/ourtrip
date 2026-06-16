document.addEventListener("DOMContentLoaded", () => {
  const postDetail = document.getElementById("postDetail");
  if (!postDetail) return;

  const postId = Number(postDetail.dataset.postId);
  const scrapBtn = document.getElementById("scrapBtn");
  const scrapCountEl = document.getElementById("scrapCount");
  const commentForm = document.getElementById("commentForm");
  const commentContent = document.getElementById("commentContent");
  const parentCommentId = document.getElementById("parentCommentId");
  const replyTarget = document.getElementById("replyTarget");
  const cancelReplyBtn = document.getElementById("cancelReplyBtn");

  if (scrapBtn) {
    scrapBtn.addEventListener("click", async () => {
      scrapBtn.disabled = true;
      try {
        const response = await fetch("/api/scraps/toggle", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ post_id: postId }),
        });
        const data = await response.json();
        if (!response.ok || !data.success) {
          alert(data.message || "스크랩 처리에 실패했습니다.");
          return;
        }

        scrapBtn.dataset.scraped = data.scraped ? "true" : "false";
        scrapBtn.classList.toggle("is-scraped", data.scraped);
        scrapBtn.textContent = data.scraped ? "★ 스크랩됨" : "☆ 스크랩";
        if (scrapCountEl) {
          scrapCountEl.textContent = `스크랩 ${data.scrap_count}`;
        }
      } catch {
        alert("서버에 연결할 수 없습니다.");
      } finally {
        scrapBtn.disabled = false;
      }
    });
  }

  document.querySelectorAll(".comment-reply-btn").forEach((button) => {
    button.addEventListener("click", () => {
      parentCommentId.value = button.dataset.commentId;
      replyTarget.hidden = false;
      replyTarget.textContent = `${button.dataset.nickname}님에게 답글 작성 중`;
      cancelReplyBtn.hidden = false;
      commentContent.focus();
    });
  });

  if (cancelReplyBtn) {
    cancelReplyBtn.addEventListener("click", () => {
      parentCommentId.value = "";
      replyTarget.hidden = true;
      cancelReplyBtn.hidden = true;
    });
  }

  if (commentForm) {
    commentForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = {
        post_id: postId,
        content: commentContent.value.trim(),
        parent_id: parentCommentId.value || null,
      };

      try {
        const response = await fetch("/api/comments", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok || !data.success) {
          alert(data.message || "댓글 등록에 실패했습니다.");
          return;
        }
        window.location.reload();
      } catch {
        alert("서버에 연결할 수 없습니다.");
      }
    });
  }
});
