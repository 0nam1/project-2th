document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("token");

  if (!token) {
    alert("로그인이 필요합니다.");
    window.location.href = "index.html";
    return;
  }

  const chatBox = document.getElementById("chat-box");
  const userInput = document.getElementById("userInput");
  const imageInput = document.getElementById("imageInput");
  const previewWrapper = document.getElementById("imagePreviewWrapper");
  const previewImage = document.getElementById("previewImage");
  const chatForm = document.getElementById("chat-form");
  const chatFormChat = document.getElementById("chat-form-chat");
  const userInputChat = document.getElementById("userInputChat");
  const imageInputChat = document.getElementById("imageInputChat");

  const profileBtn = document.getElementById("profileBtn");
  const logoutBtn = document.getElementById("logoutBtn");
  const modal = document.getElementById("profileModal");
  const profileDetails = document.getElementById("profileDetails");
  const closeModalBtn = document.querySelector(".close");

  const modelSelector = document.getElementById("modelSelector");

  const welcomeMsg = document.getElementById("welcome-message");
  const chatWrapper = document.getElementById("chat-wrapper");

  // 메시지 추가 함수
  function appendMessage(who, text) {
    const div = document.createElement("div");
    div.className = `message ${who}`; // who: 'user' 또는 'bot'
    div.textContent = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  // 이미지 미리보기 (초기 입력창)
  if (imageInput) {
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
  }

  // 실제 챗봇 메시지 전송 함수 (공통)
  async function sendMessage(message, file) {
    if (!message && !file) return;

    appendMessage("user", message || "[이미지 전송]");

    const formData = new FormData();
    formData.append("message", message);
    if (file) formData.append("image", file);

    const model = modelSelector.value;
    formData.append("model", model);

    const botMessageDiv = document.createElement("div");
    botMessageDiv.className = "message bot";
    chatBox.appendChild(botMessageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;

    // YouTube 영상을 표시할 컨테이너 추가
    const youtubeVideosContainer = document.createElement("div");
    youtubeVideosContainer.className = "youtube-videos-container";
    chatBox.appendChild(youtubeVideosContainer);

    let fullStreamBuffer = "";

    try {
      const res = await fetch("http://localhost:8000/chat/image", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (res.ok) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          let chunk = decoder.decode(value, { stream: true });
          botMessageDiv.textContent += chunk;
          fullStreamBuffer += chunk;
          chatBox.scrollTop = chatBox.scrollHeight;
        }

        // 스트리밍 완료 후 YouTube 검색
        try {
          const youtubeSearchRes = await fetch(`http://localhost:8000/youtube_search?query=${encodeURIComponent(fullStreamBuffer)}`, {
            headers: { Authorization: `Bearer ${token}` },
          });

          if (youtubeSearchRes.ok) {
            const videoData = await youtubeSearchRes.json();
            if (videoData && videoData.length > 0) {
              videoData.forEach(video => {
                const videoItem = document.createElement("div");
                videoItem.className = "youtube-video-item";

                const iframe = document.createElement("iframe");
                iframe.width = "100%";
                iframe.height = "200";
                iframe.src = `https://www.youtube.com/embed/${video.id}`;
                iframe.frameBorder = "0";
                iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture";
                iframe.allowFullscreen = true;
                videoItem.appendChild(iframe);

                const videoTitle = document.createElement("p");
                videoTitle.innerText = video.title;
                videoTitle.style.fontSize = "0.9em";
                videoTitle.style.marginTop = "5px";
                videoTitle.style.marginBottom = "15px";
                videoItem.appendChild(videoTitle);

                youtubeVideosContainer.appendChild(videoItem);
              });
            }
          } else {
            console.error("Failed to fetch YouTube videos:", youtubeSearchRes.status, youtubeSearchRes.statusText);
          }
        } catch (youtubeErr) {
          console.error("Error fetching YouTube videos:", youtubeErr);
        }
      } else {
        botMessageDiv.innerText = "❗ 오류가 발생했습니다.";
      }
    } catch (err) {
      botMessageDiv.innerText = "❗ 네트워크 오류입니다.";
      console.error(err);
    }

    if (imageInput) imageInput.value = "";
    if (previewImage) previewImage.src = "";
    if (previewWrapper) previewWrapper.classList.remove("show");
    if (imageInputChat) imageInputChat.value = "";
  }

  // 초기화면 입력창
  if (chatForm) {
    chatForm.addEventListener("submit", function (e) {
      e.preventDefault();
      if (!userInput.value.trim() && !(imageInput && imageInput.files[0])) return;
      // 안내문구 숨기고 채팅창 보이기 (오직 여기서만!)
      if (welcomeMsg) welcomeMsg.style.display = "none";
      if (chatWrapper) chatWrapper.style.display = "flex";
      // 실제 챗봇 메시지 전송
      sendMessage(userInput.value.trim(), imageInput && imageInput.files[0]);
      userInput.value = "";
    });
  }

  // 챗봇화면 입력창 (여기서는 안내문구/화면전환 X)
  if (chatFormChat) {
    chatFormChat.addEventListener("submit", function (e) {
      e.preventDefault();
      if (!userInputChat.value.trim() && !(imageInputChat && imageInputChat.files[0])) return;
      sendMessage(userInputChat.value.trim(), imageInputChat && imageInputChat.files[0]);
      userInputChat.value = "";
    });
  }

  // 로그아웃
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      localStorage.removeItem("token");
      window.location.href = "index.html";
    });
  }

  // 프로필 모달
  if (profileBtn) {
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
  }

  if (closeModalBtn) {
    closeModalBtn.addEventListener("click", () => modal.classList.add("hidden"));
  }
  if (modal) {
    window.addEventListener("click", (e) => {
      if (e.target === modal) modal.classList.add("hidden");
    });
  }
});
