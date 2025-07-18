document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("token");

  if (!token) {
    alert("로그인이 필요합니다.");
    window.location.href = "index.html";
    return;
  }

  const chatBox = document.getElementById("chat-box");
  const userInput = document.getElementById("userInput");
  const sendBtn = document.getElementById("sendBtn");
  const imageInput = document.getElementById("imageInput");
  const previewWrapper = document.getElementById("imagePreviewWrapper");
  const previewImage = document.getElementById("previewImage");

  const profileBtn = document.getElementById("profileBtn");
  const logoutBtn = document.getElementById("logoutBtn");
  const modal = document.getElementById("profileModal");
  const profileDetails = document.getElementById("profileDetails");
  const closeModalBtn = document.querySelector(".close");

  logoutBtn.addEventListener("click", () => {
    localStorage.removeItem("token");
    window.location.href = "index.html";
  });

  function appendMessage(sender, text) {
    const msg = document.createElement("div");
    msg.className = `message ${sender}`;
    msg.innerText = text;
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  // ✅ 이미지 선택 시 미리보기 표시
  imageInput.addEventListener("change", () => {
    const file = imageInput.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        previewImage.src = reader.result;
        previewWrapper.classList.add("show");
      };
      reader.readAsDataURL(file);
    } else {
      previewImage.src = "";
      previewWrapper.classList.remove("show");
    }
  });

  // ✅ 메시지 전송 (텍스트 + 이미지)
  sendBtn.addEventListener("click", async () => {
    const message = userInput.value.trim();
    const file = imageInput.files[0];
    if (!message && !file) return;

    appendMessage("user", message || "[이미지 전송]");
    userInput.value = "";

    const formData = new FormData();
    formData.append("message", message);
    if (file) formData.append("image", file);

    try {
      const res = await fetch("http://localhost:8000/chat/image", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        appendMessage("bot", data.response);
      } else {
        appendMessage("bot", "❗ 오류가 발생했습니다.");
      }
    } catch (err) {
      appendMessage("bot", "❗ 네트워크 오류입니다.");
      console.error(err);
    }

    // ✅ 전송 후 초기화
    imageInput.value = "";
    previewImage.src = "";
    previewWrapper.classList.remove("show");
  });

  // 내 정보 보기 모달 로직 (생략 없이 유지)
  profileBtn.addEventListener("click", async () => {
    try {
      const res = await fetch("http://localhost:8000/protected/me", {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error("사용자 정보를 불러올 수 없습니다.");

      const data = await res.json();
      const user = data.user;

      profileDetails.innerHTML = `
        <div class="info-group"><div class="label">아이디</div><div class="value">${user.user_id}</div></div>
        <div class="info-group"><div class="label">성별</div><div class="value">${user.gender}</div></div>
        <div class="info-group"><div class="label">나이</div><div class="value">${user.age}세</div></div>
        <div class="info-group"><div class="label">키</div><div class="value">${user.height}cm</div></div>
        <div class="info-group"><div class="label">몸무게</div><div class="value">${user.weight}kg</div></div>
        <div class="divider"></div>
        <div class="info-group"><div class="label">운동 수준</div><div class="value">${user.level}</div></div>
        <div class="info-group"><div class="label">부상 부위</div><div class="value">${user.injury_part || "없음"}</div></div>
        <div class="info-group"><div class="label">부상 수준</div><div class="value">${user.injury_level || "없음"}</div></div>
      `;

      modal.classList.remove("hidden");
    } catch (err) {
      alert("내 정보를 불러오는 데 실패했습니다.");
      console.error(err);
    }
  });

  closeModalBtn.addEventListener("click", () => modal.classList.add("hidden"));
  window.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.add("hidden");
  });
});